from urlparse import urljoin, urlparse, urlunparse
from datetime import datetime
import re
import cgi
import urllib

from remoteobjects import fields, PromiseObject, Link, remote
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseError
import typepad
from batchhttp.client import BatchError
import logging

class TypePadObject(PromiseObject):
    # TODO configurable?
    BASE_URL = 'http://127.0.0.1:8000/'

    @classmethod
    def get(cls, url, *args, **kwargs):
        if not urlparse(url)[1]:  # network location
            url = urljoin(cls.BASE_URL, url)

        ret = super(TypePadObject, cls).get(url, *args, **kwargs)
        try:
            typepad.client.add(ret)
        except BatchError:
            pass
        return ret

class Link(TypePadObject):
    rel      = fields.Something()
    href     = fields.Something()
    type     = fields.Something()
    width    = fields.Something()
    height   = fields.Something()
    duration = fields.Something()
    total    = fields.Something()

class SequenceProxyMetaclass(PromiseObject.__metaclass__):
    @staticmethod
    def makeSequenceMethod(methodname):
        def seqmethod(self, *args, **kwargs):
            # Proxy these methods to self.entries.
            return getattr(self.entries, methodname)(*args, **kwargs)
        seqmethod.__name__ = methodname
        return seqmethod

    def __new__(cls, name, bases, attrs):
        for methodname in ('__len__', '__getitem__', '__setitem__', '__delitem__', '__iter__', '__reversed__', '__contains__'):
            if methodname not in attrs:
                attrs[methodname] = cls.makeSequenceMethod(methodname)
        return super(SequenceProxyMetaclass, cls).__new__(cls, name, bases, attrs)

class ListObject(TypePadObject, remoteobjects.ListObject):
    __metaclass__ = SequenceProxyMetaclass

    total_results = fields.Something(api_name='totalResults')
    start_index   = fields.Something(api_name='startIndex')
    links         = fields.List(fields.Object(Link))
    entries       = fields.List(fields.Something())

    def __init__(self, cls=None, api_name=None, **kwargs):
        self.cls = cls
        self.api_name = api_name
        # FIXME: this shouldn't be necessary
        self._delivered = False
        self._http = None

    def _get_cls(self):
        cls = self.__dict__['cls']
        if not callable(cls):
            clsname = '.'.join((self.of_cls.__module__, cls))
            cls = find_by_name(clsname)
        return cls

    def _set_cls(self, cls):
        self.__dict__['cls'] = cls

    cls = property(_get_cls, _set_cls)

    def __get__(self, instance, owner):
        if instance._id is None:
            raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (type(self).__name__, owner.__name__))

        assert instance._id.endswith('.json')
        newurl = instance._id[:-5]
        newurl += '/' + self.api_name
        newurl += '.json'
        ret = type(self).get(newurl)
        ret.cls = self.cls
        return ret

    filterorder = ['following', 'follower', 'friend', 'nonreciprocal',
        'published', 'unpublished', 'spam', 'admin', 'member',
        'by-group', 'by-user', 'photo', 'post', 'video', 'audio', 'comment', 'link']

    def filter(self, **kwargs):
        # Split the list's URL into URL parts, filters, and queryargs.
        parts = list(urlparse(self._id))
        queryargs = cgi.parse_qs(parts[4], keep_blank_values=True)
        queryargs = dict([(k, v[0]) for k, v in queryargs.iteritems()])

        oldpath = parts[2]
        assert oldpath.endswith('.json')
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

        ret = type(self).get(newurl)
        ret.cls = self.cls
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
        super(List, self).update_from_dict(data)
        # Post-convert all the "entries" list items to our entry class.
        self.entries = [self.cls.from_dict(d) for d in self.entries]

class User(TypePadObject):
    # documented fields
    atom_id       = fields.Something(api_name='id')
    display_name  = fields.Something(api_name='displayName')
    profile_alias = fields.Something(api_name='profileAlias')
    about_me      = fields.Something(api_name='aboutMe')
    interests     = fields.List(fields.Something())
    urls          = fields.List(fields.Something())
    accounts      = fields.List(fields.Something())
    links         = fields.List(fields.Something())
    object_type   = fields.Something(api_name='objectType')

    # astropad extras
    email         = fields.Something()
    userpic       = fields.Something()

    relationships = Link(ListObject('UserRelationship'))
    events        = Link(ListObject('Event'))
    comments      = Link(ListObject('Asset'), api_name='comments-sent')
    notifications = Link(ListObject('Event'))

    @property
    def id(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:user-50
        return int(self.atom_id.split('-', 1)[1])

    @classmethod
    def get_self(cls, **kwargs):
        return cls.get('/users/@self.json', **kwargs)

class UserRelationship(TypePadObject):
    #status = fields.Something()
    source = fields.Object(User)
    target = fields.Object(User)

class PublicationStatus(TypePadObject):
    published = fields.Something()
    spam      = fields.Something()

class AssetRef(TypePadObject):
    ref  = fields.Something()
    href = fields.Something()
    type = fields.Something()

class Asset(TypePadObject):
    # documented fields
    atom_id      = fields.Something(api_name='id')
    title        = fields.Something()
    author       = fields.Object(User)
    published    = fields.Datetime()
    updated      = fields.Datetime()
    summary      = fields.Something()
    content      = fields.Something()
    # TODO  categories should be Tags?
    categories   = fields.List(fields.Something())
    object_types = fields.List(fields.Something(), api_name='objectTypes')
    status       = fields.Object(PublicationStatus)
    links        = fields.List(fields.Object(Link))
    in_reply_to  = fields.Object(AssetRef, api_name='inReplyTo')

    @property
    def actor(self):
        """
        An alias for author to satisify more generic 'actor' name used
        in templates where event/asset are used interchangeably.
        """
        return self.author

    def comment_count(self):
        for l in self.links:
            if l.rel == 'replies':
                return l.total
        return 0

    comments = Link(ListObject('Asset'))

    @property
    def id(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:asset-1794
        return self.atom_id.split('-', 1)[1]

    @property
    def asset_ref(self):
        # This is also stupid. Why not have in_reply_to just be another asset??
        ref = AssetRef()
        ref.type = 'application/json'
        ref.href = '/assets/%s.json' % self.id
        ref.ref = self.atom_id
        return ref

    def __unicode__(self):
        if self.title:
            return self.title
        if self.summary:
            return self.summary
        return self.content

    '''
    @property
    def author(self):
        try:
            return self.authors[0]
        except IndexError:
            return None
    '''

class Event(TypePadObject):
    atom_id = fields.Something(api_name='id')
    verbs   = fields.List(fields.Something())
    # TODO: vary these based on verb content? oh boy
    actor   = fields.Object(User)
    object  = fields.Object(Asset)

    @property
    def id(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:event-1680
        return self.atom_id.split('-', 1)[1]

    def __unicode__(self):
        return unicode(self.object)

class Comment(Asset):
    object_types = fields.Constant(("tag:api.typepad.com,2009:Comment",), api_name='objectTypes')

class Post(Asset):
    object_types = fields.Constant(("tag:api.typepad.com,2009:Post",), api_name='objectTypes')

class LinkAsset(Asset):
    object_types = fields.Constant(("tag:api.typepad.com,2009:Link",), api_name='objectTypes')

class Group(TypePadObject):
    atom_id      = fields.Something(api_name='id')
    display_name = fields.Something(api_name='displayName')
    tagline      = fields.Something()
    avatar       = fields.Something()
    urls         = fields.List(fields.Something())
    links        = fields.List(fields.Something())
    object_types = fields.List(fields.Something(), api_name='objectTypes')

    memberships  = Link(ListObject(UserRelationship))
    assets       = Link(ListObject(Asset))
    events       = Link(ListObject(Event))
    comments     = Link(ListObject(Asset))
    posts        = Link(ListObject(Post))
    #linkassets   = Link(ListObject(LinkAsset), api_name='assets/@link')

    @property
    def id(self):
        return self.atom_id.split('-', 1)[1]

class GroupStatus(TypePadObject):
    #status = fields.Something()
    source = fields.Object(User)
    target = fields.Object(Group)
