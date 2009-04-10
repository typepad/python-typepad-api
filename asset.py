from urlparse import urljoin, urlparse, urlunparse
from datetime import datetime
import re
import cgi
import urllib

import remoteobjects
from remoteobjects import fields
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseError
import typepad
from batchhttp.client import BatchError
import logging

class TypePadObject(remoteobjects.RemoteObject):
    base_url = None
    batch_requests = True

    @classmethod
    def get_response(cls, url, http=None, **kwargs):
        http = typepad.client.http
        return super(TypePadObject, cls).get_response(url, http=http, **kwargs)

    @classmethod
    def get(cls, url, *args, **kwargs):
        if cls.base_url is not None and not urlparse(url)[1]:  # network location
            url = urljoin(cls.base_url, url)

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
        if self.batch_requests:
            raise PromiseError("Cannot deliver %s %s except by batch request"
                % (type(self).__name__, self._location))
        return super(TypePadObject, self).deliver()

class Link(TypePadObject):
    rel      = fields.Field()
    href     = fields.Field()
    type     = fields.Field()
    width    = fields.Field()
    height   = fields.Field()
    duration = fields.Field()
    total    = fields.Field()

class LinkSet(set, TypePadObject):
    def update_from_dict(self, data):
        self.update([Link.from_dict(x) for x in data])

    def to_dict(self):
        return [x.to_dict() for x in self]

    def __getitem__(self, key):
        if isinstance(key, slice):
            raise KeyError('LinkSets cannot be sliced')

        if key.endswith('_set'):
            # Gimme all matching links.
            key = key[:-4]
            return [x for x in self if x.rel == key]

        # Gimme the first matching link.
        for x in self:
            if x.rel == key:
                return x

        raise KeyError('No such link %r in this set' % key)

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

class ApiLink(fields.Link):
    def __get__(self, instance, owner):
        try:
            if instance._location is None:
                raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (type(self).__name__, owner.__name__))

            assert instance._location.endswith('.json')
            newurl = instance._location[:-5]
            newurl += '/' + self.api_name
            newurl += '.json'

            ret = self.cls.get(newurl)
            ret.of_cls = self.of_cls
            return ret
        except Exception, e:
            logging.error(str(e))
            raise

class User(TypePadObject):
    # documented fields
    id                 = fields.Field(api_name='urlId')
    atom_id            = fields.Field(api_name='id')
    display_name       = fields.Field(api_name='displayName')
    preferred_username = fields.Field(api_name='preferredUsername')
    about_me           = fields.Field(api_name='aboutMe')
    interests          = fields.List(fields.Field())
    urls               = fields.List(fields.Field())
    accounts           = fields.List(fields.Field())
    links              = fields.Object(LinkSet)
    object_types       = fields.Field(api_name='objectTypes')

    # astropad extras
    email              = fields.Field()

    relationships      = ApiLink(ListOf('UserRelationship'))
    events             = ApiLink(ListOf('Event'))
    comments           = ApiLink(ListOf('Asset'), api_name='comments-sent')
    notifications      = ApiLink(ListOf('Event'))
    memberships        = ApiLink(ListOf('UserRelationship'))
    elsewhere_accounts = ApiLink(ListOf('ElsewhereAccount'))

    @classmethod
    def get_self(cls, **kwargs):
        return cls.get('/users/@self.json', **kwargs)

class UserRelationship(TypePadObject):
    #status = fields.Field()
    source = fields.Object('User')
    target = fields.Object('User')

class PublicationStatus(TypePadObject):
    published = fields.Field()
    spam      = fields.Field()

class AssetRef(TypePadObject):
    ref  = fields.Field()
    href = fields.Field()
    type = fields.Field()
    id   = fields.Field(api_name='urlId')

class Asset(TypePadObject):
    # documented fields
    id           = fields.Field(api_name='urlId')
    atom_id      = fields.Field(api_name='id')
    title        = fields.Field()
    author       = fields.Object(User)
    published    = fields.Datetime()
    updated      = fields.Datetime()
    summary      = fields.Field()
    content      = fields.Field()
    # TODO  categories should be Tags?
    categories   = fields.List(fields.Field())
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    status       = fields.Object(PublicationStatus)
    links        = fields.Object(LinkSet)
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

    comments = ApiLink(ListOf('Asset'))
    
    def favorite_count(self):
        for l in self.links:
            if l.rel == 'favorites':
                return l.total
        return 0

    favorites = ApiLink(ListOf('Asset'))

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
    id      = fields.Field(api_name='urlId')
    atom_id = fields.Field(api_name='id')
    verbs   = fields.List(fields.Field())
    # TODO: vary these based on verb content? oh boy
    actor   = fields.Object(User)
    object  = fields.Object(Asset)

    def __unicode__(self):
        return unicode(self.object)

class Comment(Asset):
    object_types = fields.Constant(("tag:api.typepad.com,2009:Comment",), api_name='objectTypes')

class Post(Asset):
    object_types = fields.Constant(("tag:api.typepad.com,2009:Post",), api_name='objectTypes')

class LinkAsset(Asset):
    object_types = fields.Constant(("tag:api.typepad.com,2009:Link",), api_name='objectTypes')


class ElsewhereAccount(TypePadObject):
    domain            = fields.Field()
    username          = fields.Field()
    user_id           = fields.Field(api_name='userId')
    url               = fields.Field()
    provider_name     = fields.Field(api_name='providerName')
    provider_url      = fields.Field(api_name='providerURL')
    provider_icon_url = fields.Field(api_name='providerIconURL')


class Group(TypePadObject):
    id           = fields.Field(api_name='urlId')
    atom_id      = fields.Field(api_name='id')
    display_name = fields.Field(api_name='displayName')
    tagline      = fields.Field()
    urls         = fields.List(fields.Field())
    links        = fields.List(fields.Field())
    object_types = fields.List(fields.Field(), api_name='objectTypes')

    memberships  = ApiLink(ListOf(UserRelationship))
    assets       = ApiLink(ListOf(Asset))
    events       = ApiLink(ListOf(Event))
    comments     = ApiLink(ListOf(Asset))

    # comments     = ApiLink(ListOf(Asset), api_name='comment-assets')
    # post_assets  = ApiLink(ListOf(Post), api_name='post-assets')
    # photo_assets = ApiLink(ListOf(Post), api_name='photo-assets')
    # link_assets  = ApiLink(ListOf(Post), api_name='link-assets')
    # video_assets = ApiLink(ListOf(Post), api_name='video-assets')
    # audio_assets = ApiLink(ListOf(Post), api_name='audio-assets')
    # link_assets  = ApiLink(ListOf(LinkAsset), api_name='assets/@link')


class Application(TypePadObject):
    owner   = fields.Object(Group)
    api_key = fields.Field()
    links   = fields.Object(LinkSet)

    @property
    def oauth_request_token(self):
        return self.links['oauth-request-token-endpoint'].href

    @property
    def oauth_authorization_page(self):
        return self.links['oauth-authorization-page'].href

    @property
    def oauth_access_token_endpoint(self):
        return self.links['oauth-access-token-endpoint'].href

class GroupStatus(TypePadObject):
    #status = fields.Field()
    source = fields.Object(User)
    target = fields.Object(Group)
