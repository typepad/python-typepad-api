# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import cgi
import httplib
import logging
import threading
import urlparse

import batchhttp.client
import httplib2
from oauth import oauth

import typepad


__all__ = ('OAuthAuthentication', 'OAuthClient', 'OAuthHttp', 'log')

log = logging.getLogger(__name__)


class OAuthAuthentication(httplib2.Authentication):

    """An `httplib2.Authentication` module that provides OAuth authentication.

    The OAuth authentication will be tried automatically, but to use OAuth
    authentication with a particular user agent (`Http` instance), it must
    have the OAuth consumer and access token set as one of its sets of
    credentials. For instance:

    >>> csr = oauth.OAuthConsumer(key='blah', secret='moo')
    >>> token = get_access_token_for(user)
    >>> http.add_credentials(csr, token)

    """

    def request(self, method, request_uri, headers, content):
        """Add the HTTP Authorization header to the headers for this request.

        In this implementation, the Authorization header contains the OAuth
        signing information and signature.

        """
        # httplib2 only gives us the URI in parts, so rebuild it from the
        # partial uri and host.
        partial_uri = urlparse.urlsplit(request_uri)

        # Check the query to see if the URI is already signed.
        query = partial_uri[3]
        querydict = cgi.parse_qs(query)
        if 'oauth_signature' in querydict:
            # The URI is already signed. Don't do anything.
            return

        uri = urlparse.urlunsplit((self.http.default_scheme, self.host) + partial_uri[2:])

        req = self.signed_request(uri, method)
        headers.update(req.to_header())

    def signed_request(self, uri, method):
        """Returns an `OAuthRequest` for the given URL and HTTP method, signed
        with this `OAuthAuthentication` instance's credentials."""
        csr, token = self.credentials
        assert token.secret is not None

        req = oauth.OAuthRequest.from_consumer_and_token(csr, token,
            http_method=method, http_url=uri)

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r for web request %s'
            % (sign_method.build_signature_base_string(req, csr, token),
               uri))
        req.sign_request(sign_method, csr, token)

        return req


httplib2.AUTH_SCHEME_CLASSES['oauth'] = OAuthAuthentication
httplib2.AUTH_SCHEME_ORDER[0:0] = ('oauth',)  # unshift onto front


class OAuthHttp(httplib2.Http):

    """An HTTP user agent for an OAuth web service."""

    default_scheme = 'https'

    def add_credentials(self, name, password, domain=""):
        """Adds a name (or `OAuthConsumer` instance) and password (or
        `OAuthToken` instance) to this user agent's available credentials.

        If ``name`` is an `OAuthConsumer` instance and the ``domain`` parameter
        is provided, the `OAuthHttp` instance will be configured to provide the
        given OAuth credentials, even upon the first request to that domain.
        (Normally the user agent will make the request unauthenticated first,
        receive a challenge from the server, then make the request again with
        the credentials.)

        """
        super(OAuthHttp, self).add_credentials(name, password, domain)
        log.debug("Setting credentials for name %s password %s"
            % (name, password))
        if isinstance(name, oauth.OAuthConsumer) and domain:
            if self.default_scheme is None:
                self.default_scheme = urlparse.urlsplit(typepad.client.endpoint)[0]
            # Preauthorize these credentials for any request at that domain.
            cred = (name, password)
            domain = domain.lower()
            auth = OAuthAuthentication(cred, domain, "%s://%s/" % ( self.default_scheme, domain ), {}, None, None, self)
            self.authorizations.append(auth)

    def url_for_signed_request(self, uri, method=None, headers=None, body=None):
        """Prepares to perform a request on the given URL with the given
        parameters by signing the URL with any OAuth credentials available for
        that URL.

        If no such credentials are available, a `ValueError` is raised.

        """
        if method is None:
            method = 'GET'

        uriparts = list(urlparse.urlparse(uri))
        host = uriparts[1]
        request_uri = urlparse.urlunparse([None, None] + uriparts[2:])

        # find OAuthAuthentication for this uri
        auths = [(auth.depth(request_uri), auth) for auth in self.authorizations if auth.inscope(host, request_uri)]
        if not auths:
            raise ValueError('No authorizations with which to sign a request to %r are available' % uri)
        auth = sorted(auths)[0][1]

        # use it to make a signed uri instead
        req = auth.signed_request(uri, method)
        return req.to_url()

    def signed_request(self, uri, method=None, headers=None, body=None):
        """Performs a request on the given URL with the given parameters, after
        signing the URL with any OAuth credentials available for that URL.

        If no such credentials are available, a `ValueError` is raised.

        """
        uri = self.url_for_signed_request(uri, method=method, headers=headers, body=body)
        return self.request(uri=uri, method=method, headers=headers, body=body)

    def interactive_authorize(self, consumer, app, **kwargs):
        from textwrap import fill

        # Suppress batchhttp.client's no-log-handler warning.
        class NullHandler(logging.Handler):
            def emit(self, record):
                pass
        logging.getLogger().addHandler(NullHandler())

        if not isinstance(consumer, oauth.OAuthConsumer):
            consumer = oauth.OAuthConsumer(*consumer)
        if not isinstance(app, typepad.Application):
            app = typepad.Application.get_by_id(app)

        # Set up an oauth client for our signed requestses.
        oauth_client = OAuthClient(consumer, None)
        oauth_client.request_token_url = app.oauth_request_token_url
        oauth_client.access_token_url = app.oauth_access_token_url
        oauth_client.authorization_url = app.oauth_authorization_url

        # Get a request token for the viewer to interactively authorize.
        request_token = oauth_client.fetch_request_token(None)
        log.debug("Got request token %r", request_token)

        # Ask the viewer to authorize it.
        approve_url = oauth_client.authorize_token(params=kwargs)
        log.debug("Asking viewer to authorize token with URL %r", approve_url)
        print fill("""To join your application %r, follow this link and click "Allow":"""
            % app.name, width=78)
        print
        print "<%s>" % approve_url
        print

        try:
            verifier = raw_input('Enter the verifier code TypePad gave you: ')
        except KeyboardInterrupt:
            print
            return

        # Exchange the authorized request token for an access token.
        access_token = oauth_client.fetch_access_token(verifier=verifier)

        # Re-authorize ourselves using that access token, so we can make authenticated requests with it.
        domain = urlparse.urlsplit(self.endpoint)[1]
        self.add_credentials(consumer, access_token, domain=domain)

        # Make sure the key works.
        typepad.client.batch_request()
        user = typepad.User.get_self()
        typepad.client.complete_batch()

        # Yay! Give the access token to the viewer for their reference.
        print
        print fill("""Yay! This new access token authorizes this typepad.client to act as %s (%s). Here's the token:"""
            % (user.display_name, user.url_id), width=78)
        print """
    Key:    %s
    Secret: %s
""" % (access_token.key, access_token.secret)
        print fill("""Pass this access token to typepad.client.add_credentials() to re-authorize as %s later."""
            % user.display_name, width=78)
        print

        return access_token


class OAuthClient(oauth.OAuthClient):

    """An `OAuthClient` for interacting with the TypePad API."""

    consumer = None
    request_token_url = None
    access_token_url = None
    authorization_url = None
    callback_url = None

    def set_consumer(self, key, secret):
        self.consumer = oauth.OAuthConsumer(
            key = key,
            secret = secret,
        )

    def set_token_from_string(self, token_str):
        self.token = oauth.OAuthToken.from_string(token_str)

    def fetch_request_token(self, callback):
        if not callback:
            callback = 'oob'

        h = typepad.client
        h.clear_credentials()
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            http_method='GET',
            http_url=self.request_token_url,
            callback=callback,
        )

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r in fetch_request_token()'
            % (sign_method.build_signature_base_string(req, self.consumer,
                                                       self.token),))
        req.sign_request(sign_method, self.consumer, self.token)

        log.debug('Asking for request token from %r', req.to_url())
        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        if resp.status != 200:
            log.debug(content)
            raise httplib.HTTPException('WHAT %d %s?!' % (resp.status, resp.reason))
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def fetch_access_token(self, request_token_str=None, verifier=None):
        # -> OAuthToken
        h = typepad.client
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token = self.token,
            http_url = self.access_token_url,
            verifier = verifier,
        )

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r in fetch_access_token()'
            % (sign_method.build_signature_base_string(req, self.consumer,
                                                       self.token),))
        req.sign_request(sign_method, self.consumer, self.token)

        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def authorize_token(self, params=None):
        """Returns the URL at which an interactive user can authorize this
        instance's request token."""
        if params is None:
            params = {}
        req = oauth.OAuthRequest.from_token_and_callback(
            self.token,
            http_url=self.authorization_url,
            parameters=params,
        )
        return req.to_url()

    def get_file_upload_url(self, upload_url):
        """Returns the given upload URL, signed for performing an HTTP ``POST``
        against it, with this instance's OAuth credentials.

        Such a signed URL can be used for uploading asset files to TypePad.

        """
        # oauth GET params for file upload url
        # since the form is multipart/form-data
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token = self.token,
            http_method = 'POST',
            http_url = upload_url,
        )

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r in get_file_upload_url()'
            % (sign_method.build_signature_base_string(req, self.consumer,
                                                       self.token),))
        req.sign_request(sign_method, self.consumer, self.token)
        return req.to_url()


class TypePadClient(batchhttp.client.BatchClient, OAuthHttp):

    """An HTTP user agent for performing TypePad API requests.

    A `TypePadClient` instance supports the same interface as `httplib2.Http`
    instances, plus some special methods for performing OAuth authenticated
    requests, and using TypePad's batch HTTP endpoint.

    Each `TypePadClient` instance also has a `cookies` member, a dictionary
    containing any additional HTTP cookies to send when making API requests.

    """

    endpoint = 'http://api.typepad.com'
    """The URL against which to perform TypePad API requests."""

    subrequest_limit = 20
    """The number of subrequests permitted for a given batch."""

    def __init__(self, *args, **kwargs):
        self.cookies = dict()
        self._consumer = None
        self._token = None
        kwargs['endpoint'] = self.endpoint
        super(TypePadClient, self).__init__(*args, **kwargs)
        self.follow_redirects = False

    def request(self, uri, method="GET", body=None, headers=None, redirections=httplib2.DEFAULT_MAX_REDIRECTS, connection_type=None):
        """Makes the given HTTP request, as specified.

        If the instance's ``cookies`` dictionary contains any cookies, they
        will be sent along with the request.

        See `httplib2.Http.request()` for more information.

        """
        if self.cookies:
            if headers is None:
                headers = {}
            else:
                headers = dict(headers)
            cookies = ['='.join((key, value)) for key, value in self.cookies.items()]
            headers['cookie'] = '; '.join(cookies)
        return super(TypePadClient, self).request(uri, method, body, headers, redirections, connection_type)

    def add_credentials(self, name, password, domain=""):
        endparts = urlparse.urlsplit(self.endpoint)
        if domain == '':
            domain = endparts[1]
        if isinstance(name, oauth.OAuthConsumer) and domain == endparts[1]:
            # We're adding TypePad credentials, so upgrade to HTTPS.
            self.endpoint = urlparse.urlunsplit(('https',) + endparts[1:])
        super(TypePadClient, self).add_credentials(name, password, domain)

    def clear_credentials(self):
        super(TypePadClient, self).clear_credentials()
        # We cleared our TypePad credentials too, so downgrade to HTTP.
        endparts = urlparse.urlsplit(self.endpoint)
        self.endpoint = urlparse.urlunsplit(('http',) + endparts[1:])

    def signed_request(self, uri, method=None, body=None, headers=None):
        """Performs the given request, after signing the URL with the user
        agent's configured OAuth credentials.

        If the given URL is not an absolute URL, it is taken as relative to
        this instance's endpoint first.

        """
        host = urlparse.urlparse(uri)[1]
        if not host:
            uri = urlparse.urljoin(self.endpoint, uri)
        return super(TypePadClient, self).signed_request(uri=uri,
            method=method, body=body, headers=headers)

    def _get_consumer(self):
        return self._consumer

    def _set_consumer(self, consumer):
        if isinstance(consumer, tuple):
            consumer = oauth.OAuthConsumer(consumer[0], consumer[1])
        assert(consumer is None or isinstance(consumer, oauth.OAuthConsumer))
        if self._consumer != consumer:
            self._consumer = consumer
            if consumer is None:
                self.clear_credentials()
            else:
                self._reauthorize()

    consumer = property(_get_consumer, _set_consumer)

    def _get_token(self):
        return self._token

    def _set_token(self, token):
        if isinstance(token, tuple):
            token = oauth.OAuthToken(token[0], token[1])
        assert(token is None or isinstance(token, oauth.OAuthToken))
        if self._token != token:
            self._token = token
            # if token is None, forcibly clear credentials
            if token is None:
                self.clear_credentials()
            else:
                self._reauthorize()

    token = property(_get_token, _set_token)

    def _reauthorize(self):
        if self._consumer is not None and self._token is not None:
            self.clear_credentials()
            self.add_credentials(self._consumer, self._token)


class ThreadAwareTypePadClientProxy(object):

    def __init__(self):
        self._local = threading.local()

    def _get_client(self):
        if not hasattr(self._local, 'client'):
            self.client = typepad.client_factory()
        return self._local.client

    def _set_client(self, new_client):
        self._local.client = new_client

    client = property(_get_client, _set_client)
    """Property for accessing the real client instance.

    Constructs a TypePadClient if the active thread doesn't have one."""

    def __getattr__(self, name):
        if name in ('_local', 'client'):
            return super(ThreadAwareTypePadClientProxy,
                self).__getattr__(name)
        else:
            return getattr(self.client, name)

    def __setattr__(self, name, value):
        if name in ('_local', 'client'):
            super(ThreadAwareTypePadClientProxy, self).__setattr__(name,
                value)
        else:
            setattr(self.client, name, value)
