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

"""

The `typepad.tpobject` module houses the `TypePadObject` class and related
classes, providing a `RemoteObject` based implementation of the generic
TypePad API.

The module contains:

* the `TypePadObject` class, a `RemoteObject` subclass that enforces batch
  requesting and ``objectTypes`` behavior

* the `Link` class, implementing the TypePad API's common link object

* the `ListObject` class and `ListOf` metaclass, providing an interface for
  working with the TypePad API's list endpoints

"""

import cgi
from copy import copy
from cStringIO import StringIO
try:
    from email.message import Message
    from email.generator import Generator, _make_boundary
except ImportError:
    from email.Message import Message
    from email.Generator import Generator, _make_boundary
import httplib
import inspect
from itertools import chain
import logging
import re
import sys
import urllib
from urlparse import urljoin, urlparse, urlunparse

from batchhttp.client import BatchError
import httplib2
import remoteobjects
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseError
import remoteobjects.listobject
import simplejson as json

import typepad
from typepad import fields


log = logging.getLogger(__name__)

classes_by_object_type = {}


class TypePadObjectMetaclass(remoteobjects.RemoteObject.__metaclass__):

    """A metaclass for creating new `TypePadObject` classes.

    In addition to the normal behavior of `RemoteObject` class creation,
    classes created by `TypePadObjectMetaclass` are classified by their
    ``object_type`` members, so their instances can be reclassified based on
    ``object_types`` data in API responses.

    """

    def __new__(cls, name, bases, attrs):
        newcls = super(TypePadObjectMetaclass, cls).__new__(cls, name, bases, attrs)
        try:
            api_type = attrs['_class_object_type']
        except KeyError:
            pass
        else:
            classes_by_object_type[api_type] = newcls.__name__
        return newcls


class TypePadObject(remoteobjects.RemoteObject):

    """A `RemoteObject` representing an object in the TypePad API.

    All HTTP requests made for a `TypePadObject` are made through the
    `typepad.client` user agent instance. Unlike other `PromiseObject`
    instances, `TypePadObject` instances cannot be independently delivered;
    they must be delivered by an outside object (namely `typepad.client`).

    """

    __metaclass__ = TypePadObjectMetaclass

    _class_object_type = None
    batch_requests = True

    @classmethod
    def get(cls, url, *args, **kwargs):
        """Promises a new `TypePadObject` instance for the named resource.

        If parameter `url` is not an absolute URL, the resulting instance will
        reference the given URL relative to the TypePad API's base address.

        If batch requests are enabled, the request that delivers the resulting
        `TypePadObject` instance will be added to the `typepad.client`
        `BatchClient` instance's batch request. If `typepad.client` has no
        active batch request, a `PromiseError` will be raised. The `batch`
        parameter can be used to force a non-batch request if batch
        requests are enabled.

        """
        if not urlparse(url)[1]:  # network location
            url = urljoin(typepad.client.endpoint, url)

        kwargs['http'] = typepad.client

        ret = super(TypePadObject, cls).get(url, *args, **kwargs)
        ret.batch_requests = kwargs.get('batch', cls.batch_requests)
        if ret.batch_requests:
            # Schedule for batching, if there's a batch request open.
            cb = kwargs.get('callback', ret.update_from_response)
            try:
                typepad.client.batch(ret.get_request(), cb)
            except BatchError, ex:
                # Remember our caller in case we need to debug delivery later.
                ret._origin = inspect.stack()[1][1:4]

        return ret

    def post(self, obj, http=None):
        """Adds another `TypePadObject` to this remote resource through an HTTP
        ``POST`` request, as in `HttpObject.post()`.

        Regardless of the `http` parameter, the request is performed with the
        `typepad.client` user agent.

        """
        http = typepad.client
        return super(TypePadObject, self).post(obj, http=http)

    def put(self, http=None):
        """Saves a previously requested `TypePadObject` back to its remote
        resource through an HTTP ``PUT`` request, as in `HttpObject.put()`.

        Regardless of the `http` parameter, the request is performed with the
        `typepad.client` user agent.

        """
        http = typepad.client
        return super(TypePadObject, self).put(http=http)

    def delete(self, http=None):
        """Deletes the remote resource represented by this `TypePadObject`
        instance through an HTTP ``DELETE`` request.

        Regardless of the `http` parameter, the request is performed with the
        `typepad.client` user agent.

        """
        http = typepad.client
        return super(TypePadObject, self).delete(http=http)

    def head(self, http=None):
        http = typepad.client

        ret = super(TypePadObject, self).head(http=http)
        try:
            typepad.client.batch(ret.get_request(), ret.update_from_response)
        except BatchError, ex:
            # Remember our caller in case we need to complain about
            # delivery later.
            ret._origin = inspect.stack()[1][1:4]
        return ret

    def options(self, http=None):
        http = typepad.client

        ret = super(TypePadObject, self).options(http=http)
        try:
            typepad.client.batch(ret.get_request(), ret.update_from_response)
        except BatchError, ex:
            # Remember our caller in case we need to complain about
            # delivery later.
            ret._origin = inspect.stack()[1][1:4]
        return ret

    def reclass_for_data(self, data):
        """Modifies this `TypePadObject` instance to be an instance of the
        specific `TypePadObject` subclass specified in `data`.

        If the data specify a different `TypePadObject` subclass than the one
        of which `self` is an instance, `self` will be modified to be an
        instance of the described class. That is, if:

        * the `data` parameter is a dictionary containing an ``objectTypes``
          item,
        * that ``objectTypes`` item is a list of object type identifiers, and
        * the object type identifiers describe a different `TypePadObject`
          subclass besides the one `self` belongs to,

        `self` will be turned into an instance of the class specified in the
        `data` parameter's ``objectTypes`` list.

        This method returns ``True`` if the instance was changed to be a
        different class, or ``False`` if it was not modified.

        """
        # What should I be?
        try:
            objtype = data['objectType']
        except (TypeError, KeyError):
            pass
        else:
            try:
                objclsname = classes_by_object_type[objtype]
                objcls = find_by_name(objclsname)  # KeyError
            except KeyError:
                pass
            else:
                # Is that a change?
                if objcls is not self.__class__:
                    self.__class__ = objcls

                    # Have update_from_dict() start over.
                    return True

        # We're already that class, so go ahead.
        return False

    def make_self_link(self):
        """Builds the API URL for this `TypePadObject` instance from its data.

        This method returns either the fully absolute URL at which this
        `TypePadObject` instance can be found in the API, or ``None`` if the
        `TypePadObject` instance has no API URL. (A `TypePadObject` instance
        may have no URL if it has not been saved to the API, or if it is an
        instance of a `TypePadObject` subclass that is only ever used as a
        field in another class and so cannot be requested by itself.)

        This implementation returns ``None``. As different API objects use
        different URL schemes, all `TypePadObject` subclasses that can have
        self links must implement this method themselves.

        """
        return

    def update_from_dict(self, data):
        """Updates this object with the given data, transforming it into an
        instance of a different `TypePadObject` subclass if necessary.

        This implementation fills this `TypePadObject` instance with the data
        in parameter `data`, as in `RemoteObject.update_from_dict()`.

        If the data specify a different `TypePadObject` subclass than the one
        of which `self` is an instance, `self` will be modified to be an
        instance of the described class. That is, if:

        * this is the first time `update_from_dict()` is called on the instance,
        * the `data` parameter is a dictionary containing an ``objectTypes``
          item,
        * that ``objectTypes`` item is a list of object type identifiers, and
        * the object type identifiers describe a different `TypePadObject`
          subclass besides the one `self` belongs to,

        `self` will be turned into an instance of the class specified in the
        `data` parameter's ``objectTypes`` list.

        Override the `reclass_for_data()` method to change when an instance is
        modified to be of a different subclass.

        """
        if self.reclass_for_data(data):
            # Redispatch from the beginning.
            return self.update_from_dict(data)

        super(TypePadObject, self).update_from_dict(data)

        if self._location is None:
            try:
                # attempt to assign the _location of this object
                # to the 'self' link relation's href
                self._location = self.make_self_link()
            except (TypeError, KeyError, AttributeError), exc:
                if log.isEnabledFor(logging.DEBUG):
                    log.exception(exc)

    def to_dict(self):
        """Encodes the `TypePadObject` instance to a dictionary."""
        ret = super(TypePadObject, self).to_dict()
        if 'objectType' not in ret and hasattr(self, 'object_type'):
            ret['objectType'] = self._class_object_type
        return ret


class _PageFilterer(object):

    filterorder = ['following', 'follower', 'blocked', 'friend',
        'nonreciprocal', 'published', 'unpublished', 'spam', 'admin',
        'member', 'by-group', 'by-user', 'photo', 'post', 'video', 'audio',
        'comment', 'link', 'recent']

    def filter(self, **kwargs):
        """Returns a new `ListObject` instance representing the same endpoint
        as this `ListObject` instance with the additional filtering applied.

        This method filters the `ListObject` as does `RemoteObject.filter()`,
        but specially treats filters defined in the TypePad API. These special
        filters are not added in as query parameters but as path components.

        """
        # Split the list's URL into URL parts, filters, and queryargs.
        parts = list(urlparse(self._location))
        queryargs = cgi.parse_qs(parts[4], keep_blank_values=True)
        queryargs = dict([(k, v[0]) for k, v in queryargs.iteritems()])

        oldpath = parts[2]
        if not oldpath.endswith('.json'):
            raise AssertionError('oldpath %r does not end in %r' % (oldpath, '.json'))
        path = oldpath[:-5].split('/')

        filters = dict()
        newpath = list()
        pathparts = iter(path)
        for x in pathparts:
            if x.startswith('@'):
                x = x[1:]
                if x in ('by-group', 'by-user'):
                    filters[x] = pathparts.next()
                else:
                    filters[x] = True
            else:
                newpath.append(x)

        # Add kwargs into the filters and queryargs as appropriate.
        for k, v in kwargs.iteritems():
            # ignore this kwarg
            if k in ('callback', 'batch'):
                continue

            # handle case where value is a TypePadObject. If it is, check for
            # 'url_id' and if present, use that. If not, raise an exception
            if isinstance(v, typepad.api.TypePadObject):
                if hasattr(v, 'url_id'):
                    v = v.url_id
                else:
                    raise ValueError("""invalid object filter value for parameter %s; """
                        """object must have a url_id property to filter by object""" % k)
            # Convert by_group to by-group.
            k = k.replace('_', '-')
            # Convert by_group=7 to by_group='7'.
            v = str(v)

            if k in self.filterorder:
                filters[k] = v
            else:
                queryargs[k] = v

        # Put the filters back on the URL path in API order.
        keys = filters.keys()
        keys.sort(key=self.filterorder.index)
        for k in keys:
            if filters[k]:
                newpath.append('@' + k)
                if k in ('by-group', 'by-user'):
                    newpath.append(filters[k])

        # Coalesce the URL back into a string and make a new List from it.
        parts[2] = '/'.join(newpath) + '.json'
        parts[4] = urllib.urlencode(queryargs)
        newurl = urlunparse(parts)

        getargs = {}
        if 'callback' in kwargs:
            getargs['callback'] = kwargs['callback']
        if 'batch' in kwargs:
            getargs['batch'] = kwargs['batch']
        return self.get(newurl, **getargs)


class StreamOf(remoteobjects.listobject.PageOf, TypePadObjectMetaclass):

    _modulename = 'typepad.tpobject._streams'


class StreamObject(_PageFilterer, TypePadObject, remoteobjects.PageObject):

    __metaclass__ = StreamOf

    more_results_token = fields.Field(api_name='moreResultsToken')
    estimated_total_results = fields.Field(api_name='estimatedTotalResults')
    total_results = fields.Field(api_name='totalResults')

    def count(self):
        """Returns the number of items in the overall list resource, of which
        this `StreamObject` instance may be only a segment."""
        return int(self.total_results)

    def next(self):
        if self.more_results_token is None:
            return
        return self.filter(start_token=self.more_results_token)


class ListOf(remoteobjects.listobject.PageOf, TypePadObjectMetaclass):

    _modulename = 'typepad.tpobject._lists'


class ListObject(_PageFilterer, TypePadObject, remoteobjects.PageObject):

    """A `TypePadObject` representing a list of other `TypePadObject`
    instances.

    Endpoints in the TypePad API can be either objects themselves or sets of
    objects, which are represented in the client library as `ListObject`
    instances. As the API lists are homogeneous, all `ListObject` instances
    you'll use in practice are configured for particular `TypePadObject`
    classes (their "entry classes"). A `ListObject` instance will hold only
    instances of its configured class.

    The primary way to reference a `ListObject` class is to call its
    metaclass, `ListOf`, with a reference to or name of that class.

    >>> ListOfEntry = ListOf(Entry)

    For an `Entry` list you then fetch with the `ListOfEntry` class's `get()`
    method, all the entities in the list resource's `entries` member will be
    decoded into `Entry` instances.

    """

    __metaclass__ = ListOf

    total_results = fields.Field(api_name='totalResults')
    """The total number of items in the overall list resource (of which this
    `ListObject` instance may be only a segment)."""
    entries       = fields.List(fields.Field())
    """A list of items in this list resource."""

    def count(self):
        """Returns the number of items in the overall list resource, of which
        this `ListObject` instance may be only a segment."""
        return int(self.total_results)

    def __getitem__(self, key):
        """Returns the specified members of the `ListObject` instance's
        `entries` list or, if the `ListObject` has not yet been delivered,
        filters the `ListObject` according to the given slice."""
        if self._delivered or not isinstance(key, slice):
            return self.entries[key]
        args = dict()
        if key.start is not None:
            args['start_index'] = key.start
            if key.stop is not None:
                args['max_results'] = key.stop - key.start
        elif key.stop is not None:
            args['max_results'] = key.stop
        return self.filter(**args)

    def __repr__(self):
        return '<%s.%s %r>' % (type(self).__module__, type(self).__name__,
            getattr(self, '_location', None))


class BrowserUploadEndpoint(object):

    class NetworkGenerator(Generator):

        def __init__(self, outfp, mangle_from_=True, maxheaderlen=78, write_headers=True):
            self.write_headers = write_headers
            Generator.__init__(self, outfp, mangle_from_, maxheaderlen)

        def _write_headers(self, msg):
            """Writes this `NetworkMessage` instance's headers to
            the given generator's output file with network style CR
            LF character pair line endings.

            If called during a `NetworkMessage.as_string()` to which
            the `write_headers` option was ``False``, this method
            does nothing.

            """
            if not self.write_headers:
                return

            headerfile = self._fp
            unixheaderfile = StringIO()
            try:
                self._fp = unixheaderfile
                Generator._write_headers(self, msg)
            finally:
                self._fp = headerfile

            headers = unixheaderfile.getvalue()
            headerfile.write(headers.replace('\n', '\r\n'))

        def _flatten_submessage(self, part):
            s = StringIO()
            g = self.clone(s)
            g.flatten(part, unixfrom=False)
            return s.getvalue()

        def _handle_multipart(self, msg):
            subparts = msg.get_payload()
            if subparts is None:
                subparts = []
            elif isinstance(subparts, basestring):
                self._fp.write(subparts)
                return
            elif not isinstance(subparts, list):
                subparts = [subparts]

            msgtexts = [self._flatten_submessage(part) for part in subparts]

            alltext = '\r\n'.join(msgtexts)

            no_boundary = object()
            boundary = msg.get_boundary(failobj=no_boundary)
            if boundary is no_boundary:
                boundary = _make_boundary(alltext)
                msg.set_boundary(boundary)

            if msg.preamble is not None:
                self._fp.write(msg.preamble)
                self._fp.write('\r\n')
            self._fp.write('--' + boundary)

            for body_part in msgtexts:
                self._fp.write('\r\n')
                self._fp.write(body_part)
                self._fp.write('\r\n--' + boundary)
            self._fp.write('--\r\n')

            if msg.epilogue is not None:
                self._fp.write('\r\n')
                self._fp.write(msg.epilogue)

    class NetworkMessage(Message):

        """A MIME `Message` that has its headers separated by the
        network style CR LF character pairs, not only UNIX style LF
        characters.

        As noted in Python issue 1349106, the default behavior of
        the `email.message.Message` implementation is to use plain
        system line endings when writing its headers, and having the
        protocol module such as `smtplib` convert the headers to
        network style when sending them on the wire. In order to
        work with protocol libraries that are not aware of MIME
        messages, flattening a `NetworkMessage` with `as_string()`
        produces network style CR LF line endings.

        """

        def as_string(self, unixfrom=False, write_headers=True):
            """Flattens this `NetworkMessage` instance to a string.

            If `write_headers` is ``True``, the headers of this
            `NetworkMessage` instance are included in the result.
            Headers of sub-messages contained in this message's
            payload are always included.

            """
            fp = StringIO()
            g = BrowserUploadEndpoint.NetworkGenerator(fp, write_headers=write_headers)
            g.flatten(self, unixfrom=unixfrom)
            return fp.getvalue()

    def raise_error_for_response(self, resp, obj):
        if resp.status != 302 or 'location' not in resp:
            raise ValueError('Response is not a browser upload response: not a 302 or has no Location header')

        urlparts = urlparse(resp['location'])
        query = cgi.parse_qs(urlparts[4])

        try:
            status = query['status'][0]
        except (KeyError, IndexError):
            raise ValueError("Response is not a browser upload response: no 'status' query parameter")
        try:
            status = int(status)
        except KeyError:
            raise ValueError("Response is not a browser upload response: non-numeric 'status' query parameter %r" % status)

        if status == 201:
            # Yay, no error! Return the query params in case we want to pull asset_url out of it.
            return query

        # Not a 201 means it was an error. But which?
        err_classes = {
            httplib.NOT_FOUND: obj.NotFound,
            httplib.UNAUTHORIZED: obj.Unauthorized,
            httplib.FORBIDDEN: obj.Forbidden,
            httplib.PRECONDITION_FAILED: obj.PreconditionFailed,
            httplib.INTERNAL_SERVER_ERROR: obj.ServerError,
            httplib.BAD_REQUEST: obj.RequestError,
        }
        try:
            err_cls = err_classes[status]
        except KeyError:
            raise ValueError("Response is not a browser upload response: unexpected 'status' query parameter %r" % status)

        try:
            message = query['error'][0]
        except (KeyError, IndexError):
            # Not all these error responses have an error message, so that's okay.
            raise err_cls()
        raise err_cls(message)

    def upload(self, obj, fileobj, content_type='application/octet-stream', **kwargs):
        http = typepad.client

        data = dict(kwargs)
        data['asset'] = json.dumps(obj.to_dict())

        bodyobj = self.NetworkMessage()
        bodyobj.set_type('multipart/form-data')
        bodyobj.preamble = "multipart snowform for you"
        for key, value in data.iteritems():
            msg = self.NetworkMessage()
            msg.add_header('Content-Disposition', 'form-data', name=key)
            msg.set_payload(value)
            bodyobj.attach(msg)

        filemsg = self.NetworkMessage()
        filemsg.set_type(content_type)
        filemsg.add_header('Content-Disposition', 'form-data', name="file",
            filename="file")
        filemsg.add_header('Content-Transfer-Encoding', 'identity')
        filecontent = fileobj.read()
        filemsg.set_payload(filecontent)
        filemsg.add_header('Content-Length', str(len(filecontent)))
        bodyobj.attach(filemsg)

        # Serialize the message first, so we have the generated MIME
        # boundary when we pull the headers out.
        body = bodyobj.as_string(write_headers=False)
        headers = dict(bodyobj.items())

        request = obj.get_request(url='/browser-upload.json', method='POST',
            headers=headers, body=body)
        response, content = http.signed_request(**request)

        if 'location' in response:
            urlparts = urlparse(response['location'])
            query = cgi.parse_qs(urlparts[4])
            if 'asset_url' in query:
                parts = urlparse(query['asset_url'][0])
                url = urljoin(typepad.client.endpoint, parts[2])
                request2 = obj.get_request(url=url, method='GET')
                response2, content2 = http.request(**request2)
                obj.update_from_response(url, response2, content2)

        return response, content


class _ImageResizer(object):

    """Logic for resizing TypePad images.

    The `_ImageResizer` is an abstract mixin providing helper methods for TypePad images. A concrete implementation must
    provide implementations for several properties:

    * `url`, the default URL for the image. Required if `url_template` is not present.
    * `url_template`, the URL template to a TypePad image containing an image sizing specifier.
    * `width`, the width of the full unresized version of the image.
    * `height`, the height of the full unresized version of the image.

    """

    _PI = (        50, 75,      115, 120,      200,                320, 350,           500,                640,                800,                1024)
    _WI = (        50, 75, 100, 115, 120, 150, 200,      250, 300, 320, 350, 400, 450, 500, 550, 580, 600, 640, 650, 700, 750, 800, 850, 900, 950, 1024)
    _HI = (            75,                               250)
    _SI = (16, 20, 50, 75,      115, 120, 150,      220, 250)

    valid_specs = set(chain(
        ('%dpi' % x for x in _PI),
        ('%dwi' % x for x in _WI),
        ('%dhi' % x for x in _HI),
        ('%dsi' % x for x in _SI),
        ('pi',),
    ))
    """A set of all known valid image sizing specs."""

    # selection algorithm to scale to fit both dimensions
    def inscribe(self, size):
        """Given a size, return an `ImageLink` of an image that is no taller
        or wider than the requested size.

        This mode takes the largest dimension (either width or height) and
        scales the image so that dimension is the size specified in the spec.
        The other dimension is scaled to maintain the image's aspect ratio.

        """
        if self.url_template is None: return self
        if size == 0 or size is None: size = max(self.width, self.height)

        if self.width > self.height:
            if size > self.width:
                size = self.width
        else:
            if size > self.height:
                size = self.height

        pi = size
        if pi not in self._PI:
            pi = self._PI[-1]
            if size > pi:
                size = pi
            else:
                for x in self._PI:
                    if x > size:
                        pi = x
                        break

        if self.height > self.width:
            # scale by height
            new_height = size
            new_width = int(self.width * (new_height / float(self.height)))
        else:
            # scale by width
            new_width = size
            new_height = int(self.height * (new_width / float(self.width)))

        url = copy(self)
        url.width = new_width
        url.height = new_height
        url.url = self.at_size('%dpi' % pi)
        return url

    # selection algorithm to scale to fit width
    def by_width(self, size):
        """Given a size, return an `ImageLink` of an image that is no wider
        than the requested size.

        This mode scales the image such that the width is the size specified
        in the spec, and the height is scaled to maintain the image's aspect
        ratio.

        """
        if self.url_template is None: return self
        if size == 0 or size is None or size > self.width: size = self.width

        wi = size
        if size not in self._WI:
            wi = self._WI[-1]
            if size > wi:
                size = wi
            else:
                for x in self._WI:
                    if x > size:
                        wi = x
                        break

        url = copy(self)
        url.width = size
        url.height = int(self.height * (size / float(self.width)))
        url.url = self.at_size('%dwi' % wi)
        return url

    # selection algorithm to scale to fit height
    def by_height(self, size):
        """Given a size, return an `ImageLink` of an image that is no
        taller than the requested size.

        This mode scales the image such that the height is the size specified
        in the spec, and the width is scaled to maintain the image's aspect
        ratio.

        """
        if self.url_template is None: return self
        if size == 0 or size is None or size > self.height: size = self.height

        hi = size
        if size not in self._HI:
            hi = self._HI[-1]
            if size > hi:
                size = hi
            else:
                for x in self._HI:
                    if x > size:
                        hi = x
                        break

        url = copy(self)
        url.height = size
        url.width = int(self.width * (size / float(self.height)))
        url.url = self.at_size('%dhi' % hi)
        return url

    # selection algorithm to scale and crop to square
    def square(self, size):
        """Given a size, return an `ImageLink` of an image that fits within a
        square of the requested size.

        This results in a square image whose width and height are both the
        size specified. If the original image isn't square, the image is
        cropped across its longest dimension, showing only the central portion
        which fits inside the square.

        """
        if self.url_template is None: return self
        if size == 0 or size is None: size = max(self.width, self.height)
        if self.width > self.height:
            if size > self.width:
                size = self.width
        else:
            if size > self.height:
                size = self.height

        si = size
        if si not in self._SI:
            si = self._SI[-1]
            if size > si:
                size = si
            else:
                for x in self._SI:
                    if x > size:
                        si = x
                        break

        url = copy(self)
        url.width = size
        url.height = size
        url.url = self.at_size('%dsi' % si)
        return url

    def at_size(self, spec):
        """Returns the URL for the image at size given by `spec`.

        You can request images from TypePad in several sizes, using an
        *image sizing spec*. For example, the image spec ``pi`` means the
        original size of the image, whereas ``75si`` means a 75 pixel
        square.

        If `spec` is not a valid image sizing spec, this method raises a
        `ValueError`.

        """
        if self.url_template is None: return self.url
        if spec not in self.valid_specs:
            raise ValueError('String %r is not a valid image sizing spec' % spec)
        return self.url_template.replace('{spec}', spec)


class _VideoResizer(object):

    _width = None
    _height = None

    def get_width(self):
        if self._width is None:
            match = re.search('\swidth="(\d+)"', self.embed_code)
            if match:
                self._width = int(match.group(1))
        return self._width

    def get_height(self):
        if self._height is None:
            match = re.search('\sheight="(\d+)"', self.embed_code)
            if match:
                self._height = int(match.group(1))
        return self._height

    def set_width(self, width):
        self._width = width
        self._update_embed()

    def set_height(self, height):
        self._height = height
        self._update_embed()

    width = property(get_width, set_width)
    height = property(get_height, set_height)

    def _update_embed(self):
        self.embed_code = re.sub('(\swidth=)"\d+"', '\\1"%d"' % self.width, self.embed_code)
        self.embed_code = re.sub('(\sheight=)"\d+"', '\\1"%d"' % self.height, self.embed_code)

    # selection algorithm to scale to fit width
    def by_width(self, size):
        """Given a size, return a `VideoLink` of a video that is as wide
        as the requested size.

        This mode scales the video such that the width is the size specified
        and the height is scaled to maintain the video's aspect ratio.

        """
        vid = copy(self)
        vid.width = size
        vid.height = int(self.height * (size / float(self.width)))
        return vid


def renamed_property(old, new):
    @property
    def prop(self):
        classname = type(self).__name__
        logging.getLogger('typepad.api').warn('Property %s.%s is deprecated; use %s.%s instead',
            classname, old, classname, new)
        return getattr(self, new)
    return prop
