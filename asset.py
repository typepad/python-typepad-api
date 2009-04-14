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

    """A TypePad user.

    This includes those who own TypePad blogs, those who use TypePad Connect
    and registered commenters who have either created a TypePad account or
    signed in with OpenID.

    """

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

    relationships      = fields.Link(ListOf('Relationship'))
    events             = fields.Link(ListOf('Event'))
    comments           = fields.Link(ListOf('Asset'), api_name='comments-sent')
    notifications      = fields.Link(ListOf('Event'))
    memberships        = fields.Link(ListOf('Relationship'))
    elsewhere_accounts = fields.Link(ListOf('ElsewhereAccount'))

    @classmethod
    def get_self(cls, **kwargs):
        """Returns a `User` instance representing the account as whom the
        client library is authenticating."""
        return cls.get('/users/@self.json', **kwargs)


class ElsewhereAccount(TypePadObject):

    """A user account on an external website."""

    domain            = fields.Field()
    username          = fields.Field()
    user_id           = fields.Field(api_name='userId')
    url               = fields.Field()
    provider_name     = fields.Field(api_name='providerName')
    provider_url      = fields.Field(api_name='providerURL')
    provider_icon_url = fields.Field(api_name='providerIconURL')


class Relationship(TypePadObject):

    """The unidirectional relationship between pairs of users and groups."""

    source = fields.Object('User')
    target = fields.Object('User')
    status = fields.Object('RelationshipStatus')


class RelationshipStatus(TypePadObject):

    """A representation of just the relationship type of a relationship,
    without the associated endpoints."""

    types = fields.List(fields.Field())


class Group(TypePadObject):

    """A group that users can join, and to which users can post assets.

    TypePad API social applications are represented as groups.

    """

    id           = fields.Field(api_name='urlId')
    atom_id      = fields.Field(api_name='id')
    display_name = fields.Field(api_name='displayName')
    tagline      = fields.Field()
    urls         = fields.List(fields.Field())
    links        = fields.List(fields.Field())
    object_types = fields.List(fields.Field(), api_name='objectTypes')

    # TODO: these aren't really Relationships because the target is really a group
    memberships  = fields.Link(ListOf('Relationship'))
    assets       = fields.Link(ListOf('Asset'))
    events       = fields.Link(ListOf('Event'))
    comments     = fields.Link(ListOf('Asset'))

    # comments     = fields.Link(ListOf(Asset), api_name='comment-assets')
    post_assets  = fields.Link(ListOf('Post'), api_name='post-assets')
    # photo_assets = fields.Link(ListOf(Post), api_name='photo-assets')
    # link_assets  = fields.Link(ListOf(Post), api_name='link-assets')
    # video_assets = fields.Link(ListOf(Post), api_name='video-assets')
    # audio_assets = fields.Link(ListOf(Post), api_name='audio-assets')
    # link_assets  = fields.Link(ListOf(LinkAsset), api_name='assets/@link')


class Application(TypePadObject):

    """An application that can authenticate to the TypePad API using OAuth.

    An application is identified by its OAuth consumer key, which in the case
    of a hosted group is the same as the identifier for the group itself.

    """

    owner   = fields.Object(Group)
    api_key = fields.Field()
    links   = fields.Object(LinkSet)

    @property
    def oauth_request_token(self):
        """The URL from which to request the OAuth request token."""
        return self.links['oauth-request-token-endpoint'].href

    @property
    def oauth_authorization_page(self):
        """The URL at which end users can authorize the application to access
        their accounts."""
        return self.links['oauth-authorization-page'].href

    @property
    def oauth_access_token_endpoint(self):
        """The URL from which to request the OAuth access token."""
        return self.links['oauth-access-token-endpoint'].href


class Event(TypePadObject):

    """An action that a user or group did.

    An event has an `actor`, which is the user or group that did the action; a
    set of `verbs` that describe what kind of action occured; and an `object`
    that is the object that the action was done to. In the current TypePad API
    implementation, only assets, users and groups can be the object of an
    event.

    """

    id      = fields.Field(api_name='urlId')
    atom_id = fields.Field(api_name='id')
    verbs   = fields.List(fields.Field())
    # TODO: vary these based on verb content? oh boy
    actor   = fields.Object('User')
    object  = fields.Object('Asset')

    def __unicode__(self):
        return unicode(self.object)


class Asset(TypePadObject):

    """An item of content generated by a user."""

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
        """This asset's author.

        This alias lets us use `Asset` instances interchangeably with `Event`
        instances in templates.

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
        """An `AssetRef` instance representing this asset."""
        # TODO: "This is also stupid. Why not have in_reply_to just be another asset??"
        ref = AssetRef()
        ref.type = 'application/json'
        ref.href = '/assets/%s.json' % self.id
        ref.ref = self.atom_id
        return ref

    def __unicode__(self):
        return self.title or self.summary or self.content


class Comment(Asset):

    """A text comment posted in reply to some other asset."""

    object_types = fields.Constant(("tag:api.typepad.com,2009:Comment",), api_name='objectTypes')


class Post(Asset):

    """An entry in a blog."""

    object_types = fields.Constant(("tag:api.typepad.com,2009:Post",), api_name='objectTypes')


class LinkAsset(Asset):

    """A shared link to some URL."""

    object_types = fields.Constant(("tag:api.typepad.com,2009:Link",), api_name='objectTypes')


class AssetRef(TypePadObject):

    """A structure that refers to an asset without including its full
    content."""

    ref  = fields.Field()
    href = fields.Field()
    type = fields.Field()
    id   = fields.Field(api_name='urlId')


class PublicationStatus(TypePadObject):

    """A container for the flags that represent an asset's publication status.

    Publication status is currently represented by two flags: published and
    spam. The published flag is false when an asset is held for moderation,
    and can be set to true to publish the asset. The spam flag is true when
    TypePad's spam filter has determined that an asset is spam, or when the
    asset has been marked as spam by a moderator.

    """

    published = fields.Field()
    spam      = fields.Field()
