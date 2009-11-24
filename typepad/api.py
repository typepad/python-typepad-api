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

import base64
from cStringIO import StringIO
from datetime import datetime
try:
    from email.message import Message
    from email.generator import Generator, _make_boundary
except ImportError:
    from email.Message import Message
    from email.Generator import Generator, _make_boundary
import re
import simplejson as json
from urlparse import urljoin

from remoteobjects.dataobject import find_by_name

from typepad.tpobject import *
from typepad import fields
import typepad


def xid_from_atom_id(atom_id):
    """Returns the XID portion of the given Atom ID for a TypePad content
    object.

    If the given Atom ID is not the same format as a TypePad content object's
    Atom ID, returns ``None``.

    """
    try:
        # tag:api.typepad.com,2009:6e01148739c04077bd0119f49c602c9c4b
        # tag:api.typepad.com,2003:user-6p00000001
        # tag:api.typepad.com,2009:6a01229910fa0c12ef011cd6ccab0303b5:6p01229910fa0c12ef
        #    (Favorites look like this)
        return re.match('^tag:(?:[\w-]+[.]?)+,\d{4}:(?:\w+-)?(\w+(:\w+)?)$', atom_id).groups()[0]
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
    """A URI that uniquely identifies this `User`.

    A user's `id` URI is unique across groups, TypePad environments, and
    time. When associating local content to a user, use this identifier
    as the "foreign key" to an API user.

    """
    url_id             = fields.Field(api_name='urlId')
    """An identifier for this `User` that can be used in URLs.

    A user's `url_id` is unique only across groups in one TypePad
    environment, so you should use `id`, not `url_id`, to associate data
    with a `User`. When constructing URLs to API resources in a given
    TypePad environment, however, use `url_id`.

    """
    display_name       = fields.Field(api_name='displayName')
    """The name chosen by the `User` for display purposes.

    Use this name when displaying the `User`'s name in link text or other
    text for human viewing.

    """
    preferred_username = fields.Field(api_name='preferredUsername')
    """The identifying part of the `User`'s chosen TypePad Profile URL.

    This identifier is unique across groups, but not across TypePad
    environments. TypePad users can change their Profile URLs, so this
    identifier can also change over time for a given user. Use this name
    when constructing a link to the user's profile on your local site.
    (Use the appropriate `Link` from the `User` instance's `links` for
    the full TypePad Profile URL.)

    """
    email              = fields.Field()
    location           = fields.Field()
    gender             = fields.Field()
    homepage           = fields.Field()
    about_me           = fields.Field(api_name='aboutMe')
    """The biographical text provided by the `User`.

    This text is displayed on the user's TypePad Profile page. The string
    may contain multiple lines of text separated by newline characters.

    """
    interests          = fields.List(fields.Field())
    """A list of strings identifying interests, provided by the `User`."""
    urls               = fields.List(fields.Field())
    accounts           = fields.List(fields.Field())
    links              = fields.Object('LinkSet')
    """A `LinkSet` containing various URLs and API endpoints related to this
    `User`."""
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
        url_id = xid_from_atom_id(id)
        assert url_id, "valid id parameter required"
        u = cls.get_by_url_id(url_id, **kwargs)
        u.__dict__['id'] = id
        return u

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
        u = cls.get('/users/%s.json' % url_id, **kwargs)
        u.__dict__['url_id'] = url_id
        return u


class ElsewhereAccount(TypePadObject):

    """A user account on an external website."""

    domain            = fields.Field()
    """The DNS domain of the site to which the account belongs."""
    username          = fields.Field()
    """The username of the account, if known and appropriate.

    Some services don't have `username` attributes, only `user_id`
    attributes.

    """
    user_id           = fields.Field(api_name='userId')
    """The primary identifier of the account, if known."""
    url               = fields.Field()
    """The URL of the corresponding profile page on the service's web site,
    if known."""
    provider_name     = fields.Field(api_name='providerName')
    """The name of the service providing this account, suitable for
    presentation to human viewers."""
    provider_url      = fields.Field(api_name='providerURL')
    """The URL of the home page of the service providing this account."""
    provider_icon_url = fields.Field(api_name='providerIconURL')
    """The URL of a 16 by 16 pixel icon representing the service providing
    this account."""
    crosspostable     = fields.Field()
    """Boolean for whether or not this account supports cross-posting."""
    id                = fields.Field()
    """A unique identifier for this elsewhere account.
    
    Used when issuing a cross-post to the elsewhere account.
    
    """

    @property
    def xid(self):
        return xid_from_atom_id(self.id)


class Relationship(TypePadObject):

    """The unidirectional relationship between a pair of entities.

    A Relationship can be between a user and a user (a contact relationship),
    or a user and a group (a membership). In either case, the relationship's
    status shows *all* the unidirectional relationships between the source and
    target entities.

    """

    source  = fields.Object('TypePadObject')
    """The entity (`User` or `Group`) from which this `Relationship` arises."""
    target  = fields.Object('TypePadObject')
    """The entity (`User` or `Group`) that is the object of this
    `Relationship`."""
    status  = fields.Object('RelationshipStatus')
    """A `RelationshipStatus` describing the types of relationship this
    `Relationship` instance represents."""
    links   = fields.Object('LinkSet')
    """A `LinkSet` containing other URLs and API endpoints related to this
    relationship."""
    created = fields.Dict(fields.Datetime())

    @property
    def id(self):
        """A pseudo-id that we use for caching purposes."""
        return "tag:api.typepad.com,2009:%s%s" % (self.source.xid, self.target.xid)

    @property
    def xid(self):
        return xid_from_atom_id(self.id)

    def _rel_type_updater(uri):
        def update(self):
            rel_status = RelationshipStatus.get(self.status_url(), batch=False)
            if uri:
                rel_status.types = [uri]
            else:
                rel_status.types = []
            rel_status.put()
        return update

    block   = _rel_type_updater("tag:api.typepad.com,2009:Blocked")
    unblock = _rel_type_updater(None)
    leave   = _rel_type_updater(None)

    def _rel_type_checker(uri):
        def has_edge_with_uri(self):
            return uri in self.status.types
        return has_edge_with_uri

    is_member  = _rel_type_checker("tag:api.typepad.com,2009:Member")
    is_admin   = _rel_type_checker("tag:api.typepad.com,2009:Admin")
    is_blocked = _rel_type_checker("tag:api.typepad.com,2009:Blocked")

    def status_url(self):
        return self.links['status'].href


class RelationshipStatus(TypePadObject):

    """A representation of just the relationship types of a relationship,
    without the associated endpoints."""

    types = fields.List(fields.Field())
    """A list of URIs instances that describe all the
    relationship edges included in this `RelationshipStatus`."""


class Group(TypePadObject):

    """A group that users can join, and to which users can post assets.

    TypePad API social applications are represented as groups.

    """

    object_type = "tag:api.typepad.com,2009:Group"

    id           = fields.Field()
    """A URI that uniquely identifies this `Group`.

    A group's `id` URI is unique across groups, TypePad environments, and
    time. When associating local content with a group, use this
    identifier as the "foreign key" to an API group.

    """
    url_id       = fields.Field(api_name='urlId')
    """An identifier for this `Group` that can be used in URLs.

    A group's `url_id` is unique in only one TypePad environment, so you
    should use `id`, not `url_id`, to associate data with a `Group`. When
    constructing URLs to API resources in a given TypePad environment,
    however, use `url_id`.

    """
    display_name = fields.Field(api_name='displayName')
    """
    The name chosen for the `Group` for display purposes.

    Use this name when displaying the `Group`'s name in link text or
    other text for human viewing.

    """
    tagline      = fields.Field()
    """The tagline or subtitle of this `Group`."""
    urls         = fields.List(fields.Field())
    links        = fields.Object('LinkSet')
    """A `LinkSet` containing URLs and API endpoints related to this
    `Group`."""

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
        url_id = xid_from_atom_id(id)
        assert url_id, "valid id parameter required"
        g = cls.get_by_url_id(url_id, **kwargs)
        g.__dict__['id'] = id
        return g

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        """Returns a `Group` instance by the group's url identifier.

        Asserts that the url_id parameter matches ^\w+$."""
        assert re.match('^\w+$', url_id), "invalid url_id parameter given"
        g = cls.get('/groups/%s.json' % url_id, **kwargs)
        g.__dict__['url_id'] = url_id
        return g


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
    """A `LinkSet` containing the API endpoints associated with this
    `Application`."""

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
    def user_flyouts_script(self):
        """The URL from which to request typepad user flyout javascript."""
        return self.links['user-flyouts-script'].href

    @property
    def browser_upload_endpoint(self):
        """The endpoint to use for uploading file assets directly to
        TypePad."""
        return urljoin(typepad.client.endpoint, '/browser-upload.json')

    @classmethod
    def get_by_api_key(cls, api_key, **kwargs):
        """Returns an `Application` instance by the API key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        import logging
        logging.getLogger("typepad.api").warn(
            'Application.get_by_api_key is deprecated')
        return cls.get('/applications/%s.json' % api_key, **kwargs)


class Event(TypePadObject):

    """An action that a user or group did.

    An event has an `actor`, which is the user or group that did the action; a
    set of `verbs` that describe what kind of action occured; and an `object`
    that is the object that the action was done to. In the current TypePad API
    implementation, only assets, users and groups can be the object of an
    event.

    """

    id        = fields.Field()
    """A URI that uniquely identifies this `Event`."""
    url_id    = fields.Field(api_name='urlId')
    """An identifier for this `Event` that can be used in URLs."""
    actor     = fields.Object('TypePadObject')
    """The entity (`User` or `Group`) that performed the described `Event`.

    For example, if the `Event` represents someone joining a group,
    `actor` would be the `User` who joined the group.

    """
    object    = fields.Object('TypePadObject')
    """The object (a `User`, `Group`, or `Asset`) that is the target of the
    described `Event`.

    For example, if the `Event` represents someone joining a group,
    `object` would be the group the `User` joined.

    """
    published = fields.Datetime()
    verbs     = fields.List(fields.Field())
    """A list of URIs describing what this `Event` describes.

    For example, if the `Event` represents someone joining a group,
    `verbs` would contain the one URI
    ``tag:api.typepad.com,2009:JoinedGroup``.

    """
    links        = fields.Object('LinkSet')
    """A `LinkSet` containing various URLs and API endpoints related to this
    `Event`."""

    def __unicode__(self):
        return unicode(self.object)

    @property
    def xid(self):
        return xid_from_atom_id(self.id)


class Provider(TypePadObject):

    name = fields.Field()
    uri  = fields.Field()
    icon = fields.Field()


class Source(TypePadObject):

    id       = fields.Field()
    links    = fields.Object('LinkSet')
    provider = fields.Object('Provider')
    source   = fields.Field()
    by_user  = fields.Field(api_name='byUser')

    def original_link(self):
        return list(self.links['rel__alternate'])[0]


class Asset(TypePadObject):

    """An item of content generated by a user."""

    object_type = "tag:api.typepad.com,2009:Asset"

    known_object_types = [
        "tag:api.typepad.com,2009:Post",
        "tag:api.typepad.com,2009:Photo",
        "tag:api.typepad.com,2009:Video",
        "tag:api.typepad.com,2009:Audio",
        "tag:api.typepad.com,2009:Link",
        "tag:api.typepad.com,2009:Comment",
        "tag:api.typepad.com,2009:Document"
    ]

    id           = fields.Field()
    """A URI that uniquely identifies this `Asset`."""
    url_id       = fields.Field(api_name='urlId')
    """An identifier for this `Asset` that can be used in URLs."""
    title        = fields.Field()
    """The title of the asset as provided by its author.

    For some types of asset, the title may be an empty string. This
    indicates the asset has no title.

    """
    author       = fields.Object('User')
    """The `User` who created the `Asset`."""
    published    = fields.Datetime()
    """A `datetime.datetime` indicating when the `Asset` was created."""
    updated      = fields.Datetime()
    """A `datetime.datetime` indicating when the `Asset` was last modified."""
    summary      = fields.Field()
    """For a media type of `Asset`, the HTML description or caption given by
    its author."""
    content      = fields.Field()
    """For a text type of `Asset`, the HTML content of the `Asset`."""
    categories   = fields.List(fields.Object('Tag'))
    """A list of `Tag` instances associated with the `Asset`."""
    status       = fields.Object('PublicationStatus')
    """The `PublicationStatus` describing the state of the `Asset`."""
    links        = fields.Object('LinkSet')
    """A `LinkSet` containing various URLs and API endpoints related to this
    `Asset`."""
    in_reply_to  = fields.Object('AssetRef', api_name='inReplyTo')
    """For comment `Asset` instances, an `AssetRef` describing the asset on
    which this instance is a comment."""

    source       = fields.Object('Source')
    text_format  = fields.Field(api_name='textFormat')
    groups       = fields.List(fields.Field())

    crosspost_accounts = fields.List(fields.Field(), api_name='crosspostAccounts')
    """A list of elsewhere account IDs to crosspost to."""

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
        url_id = xid_from_atom_id(id)
        assert url_id, "valid id parameter required"
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        """Returns an `Asset` instance by the url id for the asset.

        Asserts that the url_id parameter matches ^\w+$."""
        assert re.match('^\w+$', url_id), "invalid url_id parameter given"
        a = cls.get('/assets/%s.json' % url_id, **kwargs)
        a.__dict__['url_id'] = url_id
        a.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
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

    favorites = fields.Link(ListOf('Favorite'))

    @property
    def asset_ref(self):
        """An `AssetRef` instance representing this asset."""
        return AssetRef(url_id=self.url_id,
                        ref=self.id,
                        author=self.author,
                        href='/assets/%s.json' % self.url_id,
                        type='application/json',
                        object_types=self.object_types)

    def __unicode__(self):
        return self.title or self.summary or self.content

    def primary_object_type(self):
        if not self.object_types: return None
        for object_type in self.object_types:
            if object_type in self.known_object_types: return object_type
        return None


class Comment(Asset):

    """A text comment posted in reply to some other asset."""

    object_type = "tag:api.typepad.com,2009:Comment"


class Favorite(Asset):

    """A favorite of some other asset.

    Asserts that the user_id and asset_id parameter match ^\w+$."""

    object_type = "tag:api.typepad.com,2009:Favorite"

    @classmethod
    def get_by_user_asset(cls, user_id, asset_id, **kwargs):
        assert re.match('^\w+$', user_id), "invalid user_id parameter given"
        assert re.match('^\w+$', asset_id), "invalid asset_id parameter given"
        return cls.get('/favorites/%s:%s.json' % (asset_id, user_id),
            **kwargs)

    @classmethod
    def head_by_user_asset(cls, *args, **kwargs):
        fav = cls.get_by_user_asset(*args, **kwargs)
        return fav.head()


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
    """A URI that uniquely identifies the referenced `Asset`.

    The URI matches the one in the referenced `Asset` instance's ``id``
    field.

    """
    url_id = fields.Field(api_name='urlId')
    """An identifier for this `Asset` that can be used in URLs.

    The identifier matches the one in the referenced `Asset` instance's
    ``url_id``.

    """
    href   = fields.Field()
    """The URL at which a representation of the corresponding asset can be
    retrieved."""
    type   = fields.Field()
    """The MIME type of the representation available from the ``href`` URL."""
    author = fields.Object('User')
    """The `User` who created the referenced asset."""

    def reclass_for_data(self, data):
        """Returns ``False``.

        This method prevents `AssetRef` instances from being reclassed when
        updated from a data dictionary based on the dictionary's
        ``objectTypes`` member.

        """
        # AssetRefs are for any object type, so don't reclass them.
        return False


class PublicationStatus(TypePadObject):

    """A container for the flags that represent an asset's publication status.

    Publication status is currently represented by two flags: published and
    spam. The published flag is false when an asset is held for moderation,
    and can be set to true to publish the asset. The spam flag is true when
    TypePad's spam filter has determined that an asset is spam, or when the
    asset has been marked as spam by a moderator.

    """

    published = fields.Field()
    """A boolean flag indicating whether the `Asset` with this
    `PublicationStatus` is available for public viewing (``True``) or
    held for moderation (``False``)."""
    spam      = fields.Field()
    """A boolean flag indicating whether the `Asset` with this
    `PublicationStatus` has been marked as spam by the automated filter
    or a site moderator (``True``) or not (``False``)."""


class Tag(TypePadObject):

    """A textual tag applied to an asset by its author."""

    term  = fields.Field()
    """The word or phrase that constitutes the tag."""
    count = fields.Field()
    """The number of times the `Tag` has been used in the requested context.

    When returned in the list of tags for a group, the count is the
    number of times the `Tag` has been used for assets in that group.
    When returned in the list of tags for a `User`, the count is the
    number of times the tag has been used on that author's assets. When
    returned in the list of tags for an `Asset`, the count is ``1`` if
    the tag has been applied to that asset.

    """

    object_types = None


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

        return response, content


browser_upload = BrowserUploadEndpoint()
