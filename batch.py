import email
import email.feedparser
import email.header
from httplib import HTTPException
import httplib2
import mimetools
from StringIO import StringIO
from urlparse import urljoin, urlparse, urlunparse
import logging
import weakref

from http_multipart import MultipartHTTPMessage, HTTPRequestMessage
import typepad

__all__ = ('BatchClient', 'client', 'BATCH_REQUESTS')

BATCH_REQUESTS = False

# FIXME: shouldn't be necessary... endpoint URL should
# be able to handle batch requests.
BATCH_ENDPOINT = 'http://127.0.0.1:5001/batch-processor'

class BatchError(Exception):
    pass

class NoRequestObject(Exception):
    pass

class Request(object):
    def __init__(self, obj):
        self.objectref = weakref.ref(obj)

    @property
    def object(self):
        obj = self.objectref()
        if obj is None:
            raise NoRequestObject()
        return obj

    def _update_headers_from_cache(self, http):
        objreq = self.object.get_request()

        if http.cache is not None:
            class StopCharade(Exception):
                pass

            class VolatileHttp(httplib2.Http):
                def _request(self, conn, host, absolute_uri, request_uri, method, body, headers, redirections, cachekey):
                    self.url     = request_uri
                    self.body    = body
                    self.headers = headers
                    raise StopCharade()

            vh = VolatileHttp()
            vh.cache = http.cache

            try:
                vh.request(**objreq)
            except StopCharade:
                return vh.headers, vh.body

        # We didn't finish our _request, or there was no cache, so return what
        # we were given.
        return objreq.get('headers', {}), objreq.get('body')

    def _update_response_from_cache(self, http, response, body):
        if http.cache is not None:
            class FauxHttp(httplib2.Http):
                def _request(self, conn, host, absolute_uri, request_uri, method, body, headers, redirections, cachekey):
                    return response, body

            fh = FauxHttp()
            fh.cache = http.cache

            objreq = self.object.get_request()
            # Let Http.request fill in the response from its cache.
            response, body = fh.request(**objreq)

            # TODO: Fix up the status code, since httplib2 writes it through
            # to the cache, who knows why.
            if response.status == 304:
                response.status = 200

        return response, body

    def as_message(self, http, id):
        headers, body = self._update_headers_from_cache(http)

        objreq = self.object.get_request()
        parts = urlparse(objreq['uri'])
        host, path = parts[1], urlunparse(('', '') + parts[2:])

        requesttext = "GET %s HTTP/1.1\r\n" % path
        headers['host'] = host
        for header, value in headers.iteritems():
            requesttext += "%s: %s\r\n" % (header, value)
        requesttext += '\r\n'
        requesttext += body or ''

        requesttext = requesttext.encode('ascii')
        submsg = HTTPRequestMessage(requesttext, id)
        return submsg

    def decode_response(self, http, part):
        # Grab the object now so we can skip all that parsing if the request
        # is really empty.
        obj = self.object

        # Parse the part body into a status line and a Message.
        messagetext = part.get_payload(decode=True)
        messagefile = StringIO(messagetext)
        status_line = messagefile.readline()
        message = email.message_from_file(messagefile)

        if status_line.startswith('HTTP/'):
            status_code = status_line.split(' ')[1]
        else:
            status_code = status_line.split(' ')[0]
        message['status'] = int(status_code)

        httpresponse = httplib2.Response(message)
        # TODO: httplib2.Response doesn't lower case header keys itself,
        # so a Response from an email Message is inconsistent with one from
        # an httplib.HTTPResponse. Enforce lower case ourselves for now.
        for k, v in httpresponse.items():
            del httpresponse[k]
            httpresponse[k.lower()] = v

        body = message.get_payload()
        httpresponse, body = self._update_response_from_cache(http, httpresponse, body)

        obj._raise_response(httpresponse, obj.get_request()['uri'])
        obj.update_from_response(httpresponse, body)

class BatchRequest(object):
    def __init__(self):
        self.requests = list()

    def add(self, obj):
        r = Request(obj)
        self.requests.append(r)

    def process(self, http):
        if BATCH_REQUESTS:
            headers, body = self.construct(http)
            logging.debug('MADE HEADERS: %r' % (headers,))
            logging.debug('MADE BODY: %s' % (body,))
            response, content = http.request(BATCH_ENDPOINT, body=body, method="POST", headers=headers)
            logging.debug('GOT RESPONSE: %s' % (response,))
            logging.debug('GOT CONTENT: %s' % (content,))
            self.handle_response(http, response, content)
        else:
            # They're all PromiseObjects, so let them figure it out.
            for request in self.requests:
                try:
                    obj = request.object
                except NoRequestObject:
                    pass
                else:
                    obj.deliver()

    def construct(self, http):
        msg = MultipartHTTPMessage()
        request_id = 1
        for request in self.requests:
            try:
                submsg = request.as_message(http, request_id)
            except NoRequestObject:
                pass
            else:
                msg.attach(submsg)
            request_id += 1

        # Do this ahead of getting headers, since the boundary is not
        # assigned until we bake the multipart message:
        content = msg.as_string(write_headers=False)
        hdrs = msg.items()
        headers = {}
        for hdr in hdrs:
            headers[hdr[0]] = hdr[1]
        return headers, content

    def handle_response(self, http, response, content):
        # parse content into pieces

        # Prevent the message/http-response sub-parts from turning into
        # Messages, as the HTTP status line will confuse the parser and
        # we'll just get a text/plain Message with our response for the
        # payload anyway.
        class HttpAverseParser(email.feedparser.FeedParser):
            def _parse_headers(self, lines):
                email.feedparser.FeedParser._parse_headers(self, lines)
                if self._cur.get_content_type() == 'message/http-response':
                    self._set_headersonly()

        p = HttpAverseParser()
        headers = ""
        for hdr in response:
            headers += "%s: %s\n" % (hdr, email.header.Header(response[hdr]).encode(), )

        p.feed(headers)
        p.feed("\n")
        p.feed(content)
        message = p.close()

        if not message.is_multipart():
            raise HTTPException('Response was not a MIME multipart response set')

        response = {}
        messages = message.get_payload()

        for part in messages:
            if part.get_content_type() != 'message/http-response':
                raise HTTPException('Batch response included a part that was not an HTTP response message')
            try:
                request_id = int(part['Multipart-Request-ID'])
            except KeyError:
                raise HTTPException('Batch response included a part with no Multipart-Request-ID header')
            except ValueError:
                raise HTTPException('Batch response included a part with an invalid Multipart-Request-ID header')

            request = self.requests[request_id-1]
            try:
                request.decode_response(http, part)
            except NoRequestObject:
                # We shouldn't have lost any references to request objects
                # since the request, but just in case.
                pass

class BatchClient(object):

    def __init__(self):
        # TODO: set up caching?
        self.http = httplib2.Http()

    def batch_request(self):
        """Opens a new BatchRequest.

        If a request is already instantiated, this will raise an exception.

        >>> r = typepad.client.batch_request()
        >>> g = Group.get("/groups/1.json")
        >>> m = g.members()
        >>> a = g.assets()
        >>> typepad.client.complete_request()

        """
        if hasattr(self, 'request'):
            # hey, we already have a request. this is invalid...
            raise BatchError("There's already an open batch request")
        self.request = BatchRequest()
        return self.request

    def complete_request(self):
        if not hasattr(self, 'request'):
            raise BatchError("There's no open batch request to complete")
        try:
            self.request.process(self.http)
        finally:
            del self.request

    def clear_request(self):
        try:
            del self.request
        except AttributeError:
            # well it's already cleared then isn't it
            pass

    def add(self, obj):
        if not hasattr(self, 'request'):
            raise BatchError("There's no open batch request to add an object to")
        self.request.add(obj)

client = BatchClient()
