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

The `typepad.api` module contains `TypePadObject` implementations of all the
content objects provided in the TypePad API.

"""

from urlparse import urljoin
from datetime import datetime
import re

from remoteobjects.dataobject import find_by_name

from typepad.tpobject import *
from typepad import fields
import typepad


def xid_from_atom_id(atom_id):
    try:
        # tag:api.typepad.com,2009:6e01148739c04077bd0119f49c602c9c4b
        # tag:api.typepad.com,2003:user-6p00000001
        return re.match('^tag:(?:[\w-]+[.]?)+,\d{4}:(?:\w+-)?(\w+)$', atom_id).groups()[0]
    except:
        return None


class User(TypePadObject):

    """A TypePad user.

    This includes those who own TypePad blogs, those who use TypePad Connect
    and registered commenters who have either created a TypePad account or
    signed in with OpenID.

    """

    object_type = "tag:api.typepad.com,2009:User"

    id                 = fields.Field()
    url_id             = fields.Field(api_name='urlId')
    display_name       = fields.Field(api_name='displayName')
    preferred_username = fields.Field(api_name='preferredUsername')
    email              = fields.Field()
    location           = fields.Field()
    gender             = fields.Field()
    homepage           = fields.Field()
    about_me           = fields.Field(api_name='aboutMe')
    interests          = fields.List(fields.Field())
    urls               = fields.List(fields.Field())
    accounts           = fields.List(fields.Field())
    links              = fields.Object('LinkSet')
    relationships      = fields.Link(ListOf('Relationship'))
    events             = fields.Link(ListOf('Event'))
    comments           = fields.Link(ListOf('Comment'), api_name='comments-sent')
    favorites          = fields.Link(ListOf('Favorite'))
    notifications      = fields.Link(ListOf('Event'))
    memberships        = fields.Link(ListOf('Relationship'))
    elsewhere_accounts = fields.Link(ListOf('ElsewhereAccount'), api_name='elsewhere-accounts')

    @property
    def xid(self):
        return xid_from_atom_id(self.id)

    @classmethod
    def get_self(cls, **kwargs):
        """Returns a `User` instance representing the account as whom the
        client library is authenticating."""
        return cls.get('/users/@self.json', **kwargs)

    @classmethod
    def get_by_id(cls, id, **kwargs):
        """Returns a `User` instance by their unique identifier.

        Asserts that the id parameter is valid."""
        id = xid_from_atom_id(id)
        assert id, "valid id parameter required"
        return cls.get_by_url_id(id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        """Returns a `User` instance by their url identifier.

        Profile URL identifiers must contain only letters, numbers, and
        underscores.

        """
        if len(url_id) == 0:
            raise ValueError('URL identifiers must contain some characters')
        mo = re.search('\W', url_id)
        if mo:
            raise ValueError('URL identifiers cannot contain "%s" characters'
                             % mo.group(0))
        return cls.get('/users/%s.json' % url_id, **kwargs)


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

    """The unidirectional relationship between a pair of entities.

    A Relationship can be between a user and a user (a contact relationship),
    or a user and a group (a membership). In either case, the relationship's
    status shows *all* the unidirectional relationships between the source and
    target entities.

    """

    source = fields.Object('TypePadObject')
    target = fields.Object('TypePadObject')
    status = fields.Object('RelationshipStatus')
    links  = fields.Object('LinkSet')

    def _rel_type_updater(uri):
        def update(self):
            rel_status = RelationshipStatus.get(self.status_url(), batch=False)
            if uri:
                rel = RelationshipType(uri=uri, create=datetime.now())
                rel_status.types = [rel]
            else:
                rel_status.types = []
            rel_status.put()
        return update

    block   = _rel_type_updater("tag:api.typepad.com,2009:Blocked")
    unblock = _rel_type_updater(None)
    leave   = _rel_type_updater(None)

    def _rel_type_checker(uri):
        def has_edge_with_uri(self):
            for edge in self.status.types:
                if edge.uri == uri:
                    return True
            return False
        return has_edge_with_uri

    is_member  = _rel_type_checker("tag:api.typepad.com,2009:Member")
    is_admin   = _rel_type_checker("tag:api.typepad.com,2009:Admin")
    is_blocked = _rel_type_checker("tag:api.typepad.com,2009:Blocked")

    def status_url(self):
        return self.links['status'].href


class RelationshipType(TypePadObject):

    """The specific relationship "edge" between two entities."""

    uri     = fields.Field()
    created = fields.Datetime()


class RelationshipStatus(TypePadObject):

    """A representation of just the relationship types of a relationship,
    without the associated endpoints."""

    types = fields.List(fields.Object('RelationshipType'))

    def update_from_dict(self, data):
        """Decodes the remote API data structure into the RelationshipStatus
        instance.

        The remote data structure may include timestamps for when the
        relationship was established (the contact was added, the group was
        joined, etc). This is decoded into the appropriate RelationshipType
        instance too.

        """
        types = [{'uri': uri, 'created': (data.get('created', {}) or {}).get(uri)} for uri in data['types']]
        data = {'types': types}
        super(RelationshipStatus, self).update_from_dict(data)

    def to_dict(self):
        """Encodes this RelationshipStatus instance into an API data structure.

        This implementation encodes the creation timestamps of the
        RelationshipType instances into a sidecar data structure.

        """
        data = super(RelationshipStatus, self).to_dict()

        created = {}
        types = []
        for t in data['types']:
            uri = t['uri']
            types.append(uri)
            if 'created' in t and t['created'] is not None:
                created[uri] = t['created']

        if created:
            return {'types': types, 'created': created}
        return {'types': types}


class Group(TypePadObject):

    """A group that users can join, and to which users can post assets.

    TypePad API social applications are represented as groups.

    """

    object_type = "tag:api.typepad.com,2009:Group"

    id           = fields.Field()
    url_id       = fields.Field(api_name='urlId')
    display_name = fields.Field(api_name='displayName')
    tagline      = fields.Field()
    urls         = fields.List(fields.Field())
    links        = fields.Object('LinkSet')

    memberships  = fields.Link(ListOf('Relationship'))
    assets       = fields.Link(ListOf('Asset'))
    events       = fields.Link(ListOf('Event'))
    comments     = fields.Link(ListOf('Asset'))

    # comments     = fields.Link(ListOf(Asset), api_name='comment-assets')
    post_assets  = fields.Link(ListOf('Post'), api_name='post-assets')
    photo_assets = fields.Link(ListOf('Photo'), api_name='photo-assets')
    link_assets  = fields.Link(ListOf('LinkAsset'), api_name='link-assets')
    video_assets = fields.Link(ListOf('Video'), api_name='video-assets')
    audio_assets = fields.Link(ListOf('Audio'), api_name='audio-assets')

    @property
    def xid(self):
        return xid_from_atom_id(self.id)

    @classmethod
    def get_by_id(cls, id, **kwargs):
        """Returns a `Group` instance by their unique identifier.

        Asserts that the id parameter is valid."""
        id = xid_from_atom_id(id)
        assert id, "valid id parameter required"
        return cls.get_by_url_id(id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id):
        """Returns a `Group` instance by the group's url identifier.

        Asserts that the url_id parameter matches ^\w+$."""
        assert re.match('^\w+$', url_id), "invalid url_id parameter given"
        return cls.get('/groups/%s.json' % url_id)


class ApiKey(TypePadObject):

    api_key = fields.Field(api_name='apiKey')
    """The consumer key portion for this `ApiKey`."""
    owner   = fields.Object('Application')

    @classmethod
    def get_by_api_key(cls, api_key):
        """Returns an `ApiKey` instance with the given consumer key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        return cls.get('/api-keys/%s.json' % api_key)


class AuthToken(TypePadObject):

    auth_token = fields.Field(api_name='authToken')
    target     = fields.Object('TypePadObject', api_name='targetObject')

    @classmethod
    def get_by_key_and_token(cls, api_key, auth_token):
        return cls.get('/auth-tokens/%s:%s.json' % (api_key, auth_token))


class Application(TypePadObject):

    """An application that can authenticate to the TypePad API using OAuth.

    An application is identified by its OAuth consumer key, which in the case
    of a hosted group is the same as the identifier for the group itself.

    """

    object_type = "tag:api.typepad.com,2009:Application"

    name  = fields.Field()
    """The name of this `Application` as configured by the developer."""
    links = fields.Object('LinkSet')

    @property
    def oauth_request_token(self):
        """The service URL from which to request the OAuth request token."""
        return self.links['oauth-request-token-endpoint'].href

    @property
    def oauth_authorization_page(self):
        """The URL at which end users can authorize the application to access
        their accounts."""
        return self.links['oauth-authorization-page'].href

    @property
    def oauth_access_token_endpoint(self):
        """The service URL from which to request the OAuth access token."""
        return self.links['oauth-access-token-endpoint'].href

    @property
    def session_sync_script(self):
        """The URL from which to request session sync javascript."""
        return self.links['session-sync-script'].href

    @property
    def oauth_identification_page(self):
        """The URL at which end users can identify themselves to sign into
        typepad, thereby signing into this site."""
        return self.links['oauth-identification-page'].href

    @property
    def signout_page(self):
        """The URL at which end users can sign out of TypePad."""
        return self.links['signout-page'].href

    @property
    def membership_management_page(self):
        """The URL at which end users can manage their group memberships."""
        return self.links['membership-management-page'].href

    @property
    def user_flyouts_script(self):
        """The URL from which to request typepad user flyout javascript."""
        return self.links['user-flyouts-script'].href

    @property
    def browser_upload_endpoint(self):
        """The endpoint to use for uploading file assets directly to
        TypePad."""
        return urljoin(typepad.client.endpoint, '/browser-upload.json')

    @classmethod
    def get_by_api_key(cls, api_key):
        """Returns an `Application` instance by the API key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        return cls.get('/applications/%s.json' % api_key)


class Event(TypePadObject):

    """An action that a user or group did.

    An event has an `actor`, which is the user or group that did the action; a
    set of `verbs` that describe what kind of action occured; and an `object`
    that is the object that the action was done to. In the current TypePad API
    implementation, only assets, users and groups can be the object of an
    event.

    """

    id        = fields.Field()
    url_id    = fields.Field(api_name='urlId')
    actor     = fields.Object('TypePadObject')
    object    = fields.Object('TypePadObject')
    published = fields.Datetime()
    verbs     = fields.List(fields.Field())

    def __unicode__(self):
        return unicode(self.object)

    @property
    def xid(self):
        return xid_from_atom_id(self.id)


class Source(TypePadObject):

    id       = fields.Field()
    links    = fields.Object('LinkSet')
    provider = fields.Field()
    source   = fields.Field()
    by_user  = fields.Field(api_name='byUser')

    def original_link(self):
        return list(self.links['rel__alternate'])[0]


class Asset(TypePadObject):

    """An item of content generated by a user."""

    object_type = "tag:api.typepad.com,2009:Asset"

    # documented fields
    id           = fields.Field()
    url_id       = fields.Field(api_name='urlId')
    title        = fields.Field()
    author       = fields.Object('User')
    published    = fields.Datetime()
    updated      = fields.Datetime()
    summary      = fields.Field()
    content      = fields.Field()
    categories   = fields.List(fields.Object('Tag'))
    status       = fields.Object('PublicationStatus')
    links        = fields.Object('LinkSet')
    in_reply_to  = fields.Object('AssetRef', api_name='inReplyTo')
    source       = fields.Object('Source')
    text_format  = fields.Field(api_name='textFormat')
    groups       = fields.List(fields.Field())

    @property
    def can_delete(self):
        try:
            return 'DELETE' in self.links['self'].allowed_methods
        except:
            return False

    @property
    def xid(self):
        return xid_from_atom_id(self.id)

    @classmethod
    def get_by_id(cls, id, **kwargs):
        """Returns an `Asset` instance by the identifier for the asset.

        Asserts that the url_id parameter matches ^\w+$."""
        id = xid_from_atom_id(id)
        assert id, "valid id parameter required"
        return cls.get_by_url_id(id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id):
        """Returns an `Asset` instance by the url id for the asset.

        Asserts that the url_id parameter matches ^\w+$."""
        assert re.match('^\w+$', url_id), "invalid url_id parameter given"
        a = cls.get('/assets/%s.json' % url_id)
        a.id = '%s-%s' % (cls.object_type, url_id)
        return a

    @property
    def actor(self):
        """This asset's author.

        This alias lets us use `Asset` instances interchangeably with `Event`
        instances in templates.
        """
        return self.author

    def comment_count(self):
        try:
            return self.links['replies'].total
        except (TypeError, KeyError):
            return 0

    comments = fields.Link(ListOf('Asset'))

    def favorite_count(self):
        try:
            return self.links['favorites'].total
        except (TypeError, KeyError):
            return 0

    favorites = fields.Link(ListOf('Asset'))

    @property
    def asset_ref(self):
        """An `AssetRef` instance representing this asset."""
        return AssetRef(url_id=self.url_id,
                        ref=self.id,
                        href='/assets/%s.json' % self.url_id,
                        type='application/json',
                        object_types=self.object_types)

    def __unicode__(self):
        return self.title or self.summary or self.content


class Comment(Asset):

    """A text comment posted in reply to some other asset."""

    object_type = "tag:api.typepad.com,2009:Comment"


class Favorite(Asset):

    """A favorite of some other asset.

    Asserts that the user_id and asset_id parameter match ^\w+$."""

    object_type = "tag:api.typepad.com,2009:Favorite"

    @classmethod
    def get_by_user_asset(cls, user_id, asset_id):
        assert re.match('^\w+$', user_id), "invalid user_id parameter given"
        assert re.match('^\w+$', asset_id), "invalid asset_id parameter given"
        return cls.get('/favorites/%s:%s.json' % (asset_id, user_id))


class Post(Asset):

    """An entry in a blog."""

    object_type = "tag:api.typepad.com,2009:Post"


class Photo(Asset):

    """An entry in a blog."""

    object_type = "tag:api.typepad.com,2009:Photo"


class Audio(Asset):

    """An entry in a blog."""

    object_type = "tag:api.typepad.com,2009:Audio"


class Video(Asset):

    """An entry in a blog."""

    object_type = "tag:api.typepad.com,2009:Video"


class LinkAsset(Asset):

    """A shared link to some URL."""

    object_type = "tag:api.typepad.com,2009:Link"


class Document(Asset):

    """A shared link to some URL."""

    object_type = "tag:api.typepad.com,2009:Document"


class AssetRef(TypePadObject):

    """A structure that refers to an asset without including its full
    content."""

    ref    = fields.Field()
    url_id = fields.Field(api_name='urlId')
    href   = fields.Field()
    type   = fields.Field()
    author = fields.Object('User')


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


class Tag(TypePadObject):

    """A textual tag applied to an asset by its author."""

    term  = fields.Field()
    count = fields.Field()

    object_types = None
