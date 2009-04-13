from urlparse import urljoin, urlparse, urlunparse
from datetime import datetime
import re
import cgi
import urllib

import remoteobjects
from remoteobjects.dataobject import find_by_name
from remoteobjects.promise import PromiseError
import typepad
from batchhttp.client import BatchError
import logging

from typepad.tpobject import *
from typepad import fields

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

    relationships      = fields.Link(ListOf('UserRelationship'))
    events             = fields.Link(ListOf('Event'))
    comments           = fields.Link(ListOf('Asset'), api_name='comments-sent')
    notifications      = fields.Link(ListOf('Event'))
    memberships        = fields.Link(ListOf('UserRelationship'))
    elsewhere_accounts = fields.Link(ListOf('ElsewhereAccount'))

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
    author       = fields.Object('User')
    published    = fields.Datetime()
    updated      = fields.Datetime()
    summary      = fields.Field()
    content      = fields.Field()
    # TODO  categories should be Tags?
    categories   = fields.List(fields.Field())
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    status       = fields.Object('PublicationStatus')
    links        = fields.Object('LinkSet')
    in_reply_to  = fields.Object('AssetRef', api_name='inReplyTo')

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

    comments = fields.Link(ListOf('Asset'))

    def favorite_count(self):
        for l in self.links:
            if l.rel == 'favorites':
                return l.total
        return 0

    favorites = fields.Link(ListOf('Asset'))

    @property
    def asset_ref(self):
        # This is also stupid. Why not have in_reply_to just be another asset??
        ref = AssetRef()
        ref.type = 'application/json'
        ref.href = '/assets/%s.json' % self.id
        ref.ref = self.atom_id
        return ref

    def __unicode__(self):
        return self.title or self.summary or self.content

class Event(TypePadObject):
    id      = fields.Field(api_name='urlId')
    atom_id = fields.Field(api_name='id')
    verbs   = fields.List(fields.Field())
    # TODO: vary these based on verb content? oh boy
    actor   = fields.Object('User')
    object  = fields.Object('Asset')

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

    # TODO: these aren't really UserRelationships because the target is really a group
    memberships  = fields.Link(ListOf('UserRelationship'))
    assets       = fields.Link(ListOf('Asset'))
    events       = fields.Link(ListOf('Event'))
    comments     = fields.Link(ListOf('Asset'))

    # comments     = fields.Link(ListOf(Asset), api_name='comment-assets')
    post_assets  = fields.Link(ListOf(Post), api_name='post-assets')
    # photo_assets = fields.Link(ListOf(Post), api_name='photo-assets')
    # link_assets  = fields.Link(ListOf(Post), api_name='link-assets')
    # video_assets = fields.Link(ListOf(Post), api_name='video-assets')
    # audio_assets = fields.Link(ListOf(Post), api_name='audio-assets')
    # link_assets  = fields.Link(ListOf(LinkAsset), api_name='assets/@link')


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
    source = fields.Object('User')
    target = fields.Object('Group')
