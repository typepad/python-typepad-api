# Copyright (c) 2009 Six Apart Ltd.
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

* the `Link` and `LinkSet` classes, implementing the TypePad API's common link
  mechanism using objects' ``links`` attributes

* the `ListObject` class and `ListOf` metaclass, providing an interface for
  working with the TypePad API's list endpoints

"""

from urlparse import urljoin, urlparse, urlunparse
import cgi
import inspect
import urllib

from batchhttp.client import BatchError
import remoteobjects
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseError

import typepad
from typepad import fields


classes_by_object_type = {}


class TypePadObjectMetaclass(remoteobjects.RemoteObject.__metaclass__):

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
    `typepad.client` instance of `batchhttp.client.BatchClient`. Unlike other
    `PromiseObject` instances, `TypePadObject` instances cannot be
    independently delivered; they must be delivered by an outside object
    (namely `typepad.client`).

    """

    __metaclass__ = TypePadObjectMetaclass

    object_type = None
    batch_requests = True

    object_types = fields.List(fields.Field(), api_name='objectTypes')

    @classmethod
    def get_response(cls, url, http=None, **kwargs):
        """Performs the given HTTP request through `typepad.client`
        `BatchClient` instance."""
        if not urlparse(url)[1]:  # network location
            url = urljoin(typepad.client.endpoint, url)
        return super(TypePadObject, cls).get_response(url, http=typepad.client, **kwargs)

    @classmethod
    def get(cls, url, *args, **kwargs):
        """Promises a new `TypePadObject` instance for the named resource.

        If parameter `url` is not an absolute URL but the `TypePadObject`
        class has been configured with a base URL, the resulting instance will
        reference the given URL relative to the base address.

        If batch requests are enabled, the request that delivers the resulting
        `TypePadObject` instance will be added to the `typepad.client`
        `BatchClient` instance's batch request. If `typepad.client` has no
        active batch request, a `PromiseError` will be raised. The `batch`
        parameter can be used to force a non-batch request if batch
        requests are enabled.

        """
        if not urlparse(url)[1]:  # network location
            url = urljoin(typepad.client.endpoint, url)

        ret = super(TypePadObject, cls).get(url, *args, **kwargs)
        ret.batch_requests = kwargs.get('batch', cls.batch_requests)
        if ret.batch_requests:
            try:
                typepad.client.batch(ret.get_request(), ret.update_from_response)
            except BatchError, ex:
                # Remember our caller in case we need to complain about
                # delivery later.
                ret._origin = inspect.stack()[1][1:4]
        return ret

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

        """
        # What should I be?
        objtypes = ()
        if not hasattr(self, '_originaldata'):
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

                # Redispatch from the beginning.
                return self.update_from_dict(data)

        super(TypePadObject, self).update_from_dict(data)

        if self._location is None:
            try:
                # attempt to assign the _location of this object
                # to the 'self' link relation's href
                self._location = self.links['self'].href
            except (TypeError, KeyError, AttributeError):
                pass

    def to_dict(self):
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


class Link(TypePadObject):

    """A `TypePadObject` representing a link from to another resource.

    The target of a `Link` object may be something other than an API resource,
    such as a `User` instance's avatar image.

    """

    rel             = fields.Field()
    href            = fields.Field()
    html            = fields.Field()
    type            = fields.Field()
    width           = fields.Field()
    height          = fields.Field()
    duration        = fields.Field()
    total           = fields.Field()
    by_user         = fields.Field(api_name="byUser")
    allowed_methods = fields.List(fields.Field(), api_name='allowedMethods')

    def __repr__(self):
        """Returns a developer-readable representation of this object."""
        return "<Link %s>" % self.__dict__.get('href', hex(id(self)))


class LinkSet(set, TypePadObject):

    """A `TypePadObject` representing a set of `Link` objects.

    `LinkSet` provides convenience methods for slicing the set of `Link`
    objects by their content. For example, the `Link` with `rel="avatar"` can
    be selected with `linkset['rel__avatar']`.

    """

    def update_from_dict(self, data):
        """Fills this `LinkSet` with `Link` instances representing the given
        data."""
        self.update([Link.from_dict(x) for x in data])

    def to_dict(self):
        """Returns a list of dictionary-ized representations of the `Link`
        instances contained in this `LinkSet`."""
        return sorted([x.to_dict() for x in self])

    def __getitem__(self, key):
        """Returns the `Link` or `LinkSet` described by the given key.

        Parameter `key` should be a string containing the axis and value by
        which to slice the `LinkSet` instance, separated by two underscores.
        For example, to select the contained `Link` with a `rel` value of
        `avatar`, the key should be `rel__avatar`.

        If the axis is `rel`, a new `LinkSet` instance containing all the
        `Link` instances with the requested value for `rel` are returned.

        If the axis is `width`, the `Link` instance best matching that width
        as discovered by the `link_by_width()` method is returned.

        No other axes are supported.

        If in either case no `Link` instances match the requested criterion, a
        `KeyError` is raised.

        """
        if isinstance(key, slice):
            raise KeyError('LinkSets cannot be sliced')

        if key.startswith('rel__'):
            # Gimme all matching links.
            key = key[5:]
            return self.__class__([x for x in self if x.rel == key])
        elif key.startswith('width__'):
            width = int(key[7:])
            return self.link_by_width(width)
        elif key.startswith('maxwidth__'):
            width = int(key[10:])
            links_by_width = dict([(x.width, x) for x in self if x.width <= width])
            if links_by_width:
                return links_by_width.get(max(links_by_width.keys()))
            return None

        # Gimme the first matching link.
        for x in self:
            if x.rel == key:
                return x

        raise KeyError('No such link %r in this set' % key)

    def link_by_width(self, width=0):
        """Returns the `Link` instance from this `LinkSet` that best matches
        the requested display width.

        If optional parameter `width` is specified, the `Link` instance
        representing the smallest image wider or matching the `width`
        specified is returned. If there is no such image, or if `width` is
        not specified, the `Link` for the widest image is returned.

        If there are no images in this `LinkSet`, returns `None`.

        """
        if width == 0:
            # Select the widest link
            better = lambda x: best is None or best.width < x.width
        else:
            # Select the image with the specified width or just greater
            better = lambda x: width <= x.width and (best is None or x.width < best.width)

        best = None
        for x in self:
            if better(x):
                best = x

        if best is None and width != 0:
            # Try again, this time just return the widest image available
            return self.link_by_width()

        return best


class SequenceProxy(object):

    """An abstract class implementing the sequence protocol by proxying it to
    an instance attribute.

    `SequenceProxy` instances act like sequences by forwarding all sequence
    method calls to their `entries` attributes. The `entries` attribute should
    be a list or some other that implements the sequence protocol.

    """

    def make_sequence_method(methodname):
        """Makes a new function that proxies calls to `methodname` to the
        `entries` attribute of the instance on which the function is called as
        an instance method."""
        def seqmethod(self, *args, **kwargs):
            # Proxy these methods to self.entries.
            return getattr(self.entries, methodname)(*args, **kwargs)
        seqmethod.__name__ = methodname
        return seqmethod

    __len__      = make_sequence_method('__len__')
    __getitem__  = make_sequence_method('__getitem__')
    __setitem__  = make_sequence_method('__setitem__')
    __delitem__  = make_sequence_method('__delitem__')
    __iter__     = make_sequence_method('__iter__')
    __reversed__ = make_sequence_method('__reversed__')
    __contains__ = make_sequence_method('__contains__')


class ListOf(TypePadObjectMetaclass, remoteobjects.ListObject.__metaclass__):

    """Metaclass defining a `ListObject` containing a list of some other
    class's instances.

    Unlike most metaclasses, this metaclass can be called directly to define
    new `ListObject` classes that contain objects of a specified other class,
    like so:

    >>> ListOfEntry = ListOf(Entry)

    This is equivalent to defining ``ListOfEntry`` yourself:

    >>> class ListOfEntry(typepad.ListObject):
    ...     entryclass = Entry

    which is a `ListObject` of ``Entry`` instances.

    """

    _subclasses = {}

    def __new__(cls, name, bases=None, attr=None):
        """Creates a new `ListObject` subclass.

        If `bases` and `attr` are specified, as in a regular subclass
        declaration, a new `ListObject` subclass bound to no particular
        `TypePadObject` class is created. `name` is the declared name of the
        new class, as usual.

        If only `name` is specified, that value is used as a reference to a
        `TypePadObject` class to which the new `ListObject` class is bound.
        The `name` parameter can be either a name or a `TypePadObject` class,
        as when declaring a `fields.Object` on a class.

        """
        direct = attr is None
        if direct:
            # Don't bother making a new subclass if we already made one for
            # this target.
            if name in cls._subclasses:
                return cls._subclasses[name]

            entryclass = name
            if callable(entryclass):
                name = cls.__name__ + entryclass.__name__
            else:
                name = cls.__name__ + entryclass
            bases = (ListObject,)
            attr = {'entryclass': entryclass}
        else:
            # Make sure classes we create conventionally are SequenceProxies.
            # As that includes ListObject, classes that are created directly
            # inherit SequenceProxy behavior through ListObject.
            bases = bases + (SequenceProxy,)

        newcls = super(ListOf, cls).__new__(cls, name, bases, attr)
        # Save the result for later direct invocations.
        if direct:
            orig_name = attr['entryclass']
            cls._subclasses[orig_name] = newcls
        return newcls


class ListObject(TypePadObject, remoteobjects.ListObject):

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
    start_index   = fields.Field(api_name='startIndex')
    links         = fields.Object('LinkSet')
    entries       = fields.List(fields.Field())

    filterorder = ['following', 'follower', 'friend', 'nonreciprocal',
        'published', 'unpublished', 'spam', 'admin', 'member',
        'by-group', 'by-user', 'photo', 'post', 'video', 'audio', 'comment',
        'link']

    def to_dict(self):
        d = super(ListObject, self).to_dict()
        d['entries'] = [x.to_dict() for x in self.entries]
        return d

    def count(self):
        return int(self.total_results)

    def filter(self, **kwargs):
        """Returns a new `ListObject` instance representing the same endpoint
        as this `ListObject` instance with the additional filtering applied.

        This method filters the `ListObject` as does
        `remoteobjects.ListObject.filter()`, but specially treats filters
        defined in the TypePad API. These special filters are not added in as
        query parameters but as path components.

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
            # handle case where value is a TypePadObject. If it is, check for
            # 'url_id' and if present, use that. If not, raise an exception
            if isinstance(v, typepad.api.TypePadObject):
                if hasattr(v, 'url_id'):
                    v = v.url_id
                else:
                    raise Exception("invalid object filter value for parameter %k; object must have a url_id property to filter by object" % k)
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

        ret = self.get(newurl)
        ret.of_cls = self.of_cls
        return ret

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

    def update_from_dict(self, data):
        """Fills this `ListObject` instance with the data from the given
        dictionary.

        The contents of the dictionary's `entries` member will be decoded into
        instances of this `ListObject` instance's entry class.

        """
        super(ListObject, self).update_from_dict(data)
        # Post-convert all the "entries" list items to our entry class.
        entryclass = self.entryclass
        if not callable(entryclass):
            entryclass = find_by_name(entryclass)
        self.entries = [entryclass.from_dict(d) for d in self.entries if d is not None]
