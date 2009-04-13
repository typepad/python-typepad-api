from urlparse import urljoin, urlparse, urlunparse
import cgi
import urllib

from batchhttp.client import BatchError
import remoteobjects
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseError

import typepad
from typepad import fields


class TypePadObject(remoteobjects.RemoteObject):

    """A `RemoteObject` representing an object in the TypePad API.

    All HTTP requests made for a `TypePadObject` are made through the
    `typepad.client` instance of `batchhttp.client.BatchClient`. Unlike other
    `PromiseObject` instances, `TypePadObject` instances cannot be
    independently delivered; they must be delivered by an outside object
    (namely `typepad.client`).

    """

    batch_requests = True

    @classmethod
    def get_response(cls, url, http=None, **kwargs):
        """Performs the given HTTP request through `typepad.client`
        `BatchClient` instance."""
        if not urlparse(url)[1]:  # network location
            url = urljoin(typepad.client.endpoint, url)
        return super(TypePadObject, cls).get_response(url, http=typepad.client.http, **kwargs)

    @classmethod
    def get(cls, url, *args, **kwargs):
        """Promises a new `TypePadObject` instance for the named resource.

        If parameter `url` is not an absolute URL but the `TypePadObject`
        class has been configured with a base URL, the resulting instance will
        reference the given URL relative to the base address.

        If batch requests are enabled, the request that delivers the resulting
        `TypePadObject` instance will be added to the `typepad.client`
        `BatchClient` instance's batch request. If `typepad.client` has no
        active batch request, a `PromiseError` will be raised.

        """
        if not urlparse(url)[1]:  # network location
            url = urljoin(typepad.client.endpoint, url)

        ret = super(TypePadObject, cls).get(url, *args, **kwargs)
        if cls.batch_requests:
            try:
                typepad.client.add(ret.get_request(), ret.update_from_response)
            except BatchError, ex:
                # We're suppressing an exception here for ListObjects
                # since in some cases we merely want the object to
                # 'post' against.
                if not issubclass(cls, ListObject):
                    raise PromiseError("Cannot get %s %s outside a batch request"
                        % (cls.__name__, url))
        return ret

    def deliver(self):
        """Prevents self-delivery of this instance if batch requests are
        enabled for `TypePadObject` instances.

        If batch requests are not enabled, delivers the object as by
        `PromiseObject.deliver()`.

        """
        if self.batch_requests:
            raise PromiseError("Cannot deliver %s %s except by batch request"
                % (type(self).__name__, self._location))
        return super(TypePadObject, self).deliver()


class Link(TypePadObject):

    """A `TypePadObject` representing a link from to another resource.

    The target of a `Link` object may be something other than an API resource,
    such as a `User` instance's avatar image.

    """

    rel      = fields.Field()
    href     = fields.Field()
    type     = fields.Field()
    width    = fields.Field()
    height   = fields.Field()
    duration = fields.Field()
    total    = fields.Field()

    def __repr__(self):
        """Returns a developer-readable representation of this object."""
        return "<Link %s>" % self.href


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
        return [x.to_dict() for x in self]

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
            return LinkSet([x for x in self if x.rel == key])
        elif key.startswith('width__'):
            width = int(key[7:])
            return self.link_by_width(width)

        # Gimme the first matching link.
        for x in self:
            if x.rel == key:
                return x

        raise KeyError('No such link %r in this set' % key)

    def link_by_width(self, width=None):
        """Returns the `Link` instance from this `LinkSet` that best matches
        the requested display width.

        If optional parameter `width` is specified, the `Link` instance
        representing the smallest image wider than `width` is returned. If
        there is no such image, or if `width` is not specified, the `Link` for
        the widest image is returned.

        If there are no images in this `LinkSet`, returns `None`.

        """
        # TODO: is there a brisk way to do this?
        widest = None
        best = None
        for link in self:
            # Keep track of the widest variant; this will be our failsafe.
            if (not widest) or link.width > widest.width:
                widest = link
            # Width was specified; enclosure is equal or larger than this
            if width and link.width >= width:
                # Assign if nothing was already chosen or if this new
                # enclosure is smaller than the last best one.
                if (not best) or link.width < best.width:
                    best = link

        # use best available image if none was selected as the 'best' fit
        if best is None:
            return widest
        else:
            return best


class SequenceProxy(object):
    def make_sequence_method(methodname):
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


class ListOf(remoteobjects.ListObject.__metaclass__):
    def __new__(cls, name, bases=None, attr=None):
        if attr is None:
            # TODO: memoize me
            entryclass = name
            if callable(entryclass):
                name = cls.__name__ + entryclass.__name__
            else:
                name = cls.__name__ + entryclass
            bases = (ListObject,)
            attr = {'entryclass': entryclass}

        bases = bases + (SequenceProxy,)
        return super(ListOf, cls).__new__(cls, name, bases, attr)

class ListObject(TypePadObject, remoteobjects.ListObject):
    __metaclass__ = ListOf

    total_results = fields.Field(api_name='totalResults')
    start_index   = fields.Field(api_name='startIndex')
    links         = fields.Object(LinkSet)
    entries       = fields.List(fields.Field())

    filterorder = ['following', 'follower', 'friend', 'nonreciprocal',
        'published', 'unpublished', 'spam', 'admin', 'member',
        'by-group', 'by-user', 'photo', 'post', 'video', 'audio', 'comment', 'link']

    def filter(self, **kwargs):
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
        super(ListObject, self).update_from_dict(data)
        # Post-convert all the "entries" list items to our entry class.
        entryclass = self.entryclass
        if not callable(entryclass):
            entryclass = find_by_name(entryclass)
        self.entries = [entryclass.from_dict(d) for d in self.entries]
