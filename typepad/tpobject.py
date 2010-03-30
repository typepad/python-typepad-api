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

from urlparse import urljoin, urlparse, urlunparse
from copy import copy
import cgi
import inspect
from itertools import chain
import logging
import sys
import urllib

from batchhttp.client import BatchError
import remoteobjects
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseError
import remoteobjects.listobject
import httplib2

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
            api_type = attrs['object_type']
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

    object_type = None
    batch_requests = True

    object_types = fields.List(fields.Field(), api_name='objectTypes')
    """A list of URIs that identify the type of TypePad content object this
    is."""

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
            cb = kwargs.get('callback', ret.update_from_response)
            try:
                typepad.client.batch(ret.get_request(), cb)
            except BatchError, ex:
                # Remember our caller in case we need to complain about
                # delivery later.
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
        objtypes = ()
        try:
            objtypes = data['objectTypes']
        except (TypeError, KeyError):
            pass

        for objtype in objtypes:
            try:
                objclsname = classes_by_object_type[objtype]
                objcls = find_by_name(objclsname)  # KeyError
            except KeyError:
                continue

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
        if 'objectTypes' not in ret and self.object_type is not None:
            ret['objectTypes'] = (self.object_type,)
        return ret

    def deliver(self):
        """Prevents self-delivery of this instance if batch requests are
        enabled for `TypePadObject` instances.

        If batch requests are not enabled, delivers the object as by
        `PromiseObject.deliver()`.

        """
        if self.batch_requests:
            if hasattr(self, '_origin'):
                origin = self._origin
                raise PromiseError("Cannot deliver %s %s created by %s at "
                    "%s line %d except by batch request"
                    % (type(self).__name__, self._location, origin[2],
                       origin[0], origin[1]))
            else:
                raise PromiseError("Cannot deliver %s %s except by batch request"
                    % (type(self).__name__, self._location))
        return super(TypePadObject, self).deliver()


class ListOf(remoteobjects.listobject.PageOf, TypePadObjectMetaclass):

    _modulename = 'typepad.tpobject._lists'


class ListObject(TypePadObject, remoteobjects.PageObject):

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
    start_index   = fields.Field(api_name='startIndex')
    """The index in the overall list resource of the first item in this
    `ListObject` instance.

    The first item in the list has index 1.

    """
    entries       = fields.List(fields.Field())
    """A list of items in this list resource."""

    filterorder = ['following', 'follower', 'friend', 'nonreciprocal',
        'published', 'unpublished', 'spam', 'admin', 'member',
        'by-group', 'by-user', 'photo', 'post', 'video', 'audio', 'comment',
        'link']

    def count(self):
        """Returns the number of items in the overall list resource, of which
        this `ListObject` instance may be only a segment."""
        return int(self.total_results)

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
