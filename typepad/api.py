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
    with a `User`. When constructing URLs to API resources in one particular
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
    (Use the `User` instance's `profile_page_url` field for the full
    TypePad Profile URL.)

    """
    email              = fields.Field()
    gender             = fields.Field()

    avatar_link = fields.Object('ImageLink', api_name='avatarLink')
    """The `Link` instance to the user's avatar picture."""
    profile_page_url = fields.Field(api_name='profilePageUrl')
    """The URL of the user's TypePad profile page."""

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

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/users/%s.json' % self.url_id)

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


class UserProfile(TypePadObject):

    """Additional profile information about a TypePad user.

    This additional information is useful when showing information about a
    TypePad account directly, but is generally not required when linking to
    an ancillary TypePad account, such as the author of a post.

    """

    id = fields.Field()
    """A URI that uniquely identifies the `User` associated with this `UserProfile`."""
    url_id = fields.Field(api_name='urlId')
    """An identifier for this `UserProfile` that can be used in URLs.

    A user's `url_id` is unique only across groups in one TypePad
    environment, so you should use `id`, not `url_id`, to associate data
    with a `User` (or `UserProfile`). When constructing URLs to API resources
    in one particular TypePad environment, however, use `url_id`.

    """
    display_name = fields.Field(api_name='displayName')
    """The related user's chosen display name."""
    email = fields.Field()
    gender = fields.Field()
    location = fields.Field()
    """The related user's location, as a free-form string provided by the user."""
    interests = fields.List(fields.Field())
    """A list of interests provided by the related user for display on their
    TypePad profile."""
    preferred_username = fields.Field(api_name='preferredUsername')
    """The name the related user chose for use in their TypePad profile URL.

    This name can be used as an ID to select this user in a transient URL.
    As this name can be changed, use the `url_id` field as a persistent key
    instead.

    """
    about_me           = fields.Field(api_name='aboutMe')
    """The biographical text provided by the `User`.

    This text is displayed on the user's TypePad Profile page. The string
    may contain multiple lines of text separated by newline characters.

    """
    avatar_link = fields.Object('ImageLink', api_name='avatarLink')
    """The `Link` instance to the related user's avatar picture."""
    profile_page_url = fields.Field(api_name='profilePageUrl')
    """The URL of the related user's TypePad profile page."""
    follow_frame_content_url = fields.Field(api_name='followFrameContentUrl')
    """The URL of the related user's following widget.

    Use this URL in an HTML iframe to provide an interface for following
    this user. The iframe should be 300 pixels wide and 125 pixels high.

    """
    profile_edit_page_url = fields.Field(api_name='profileEditPageUrl')
    """The URL of a page where the user can edit their profile information.

    This URL is only present when the `UserProfile` is requested on behalf
    of the related user. That is, the `profile_edit_page_url` is ``None``
    unless the user is viewing their own profile.

    """
    membership_management_page_url = fields.Field(api_name='membershipManagementPageUrl')
    """The URL of a page where the user can manage their community
    memberships.

    This URL is only present when the `UserProfile` is requested on behalf
    of the related user. That is, the `membership_management_page_url` is
    ``None`` unless the user is viewing their own profile.

    """
    homepage_url = fields.Field(api_name='homepageUrl')
    """The URL the related user has specified as an external website URL.

    If the related user has not specified an external website URL,
    `homepage_url` will be ``None``.

    """

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/users/%s/profile.json' % self.url_id)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        """Returns the `UserProfile` instance with the given URL identifier."""
        prof = cls.get('/users/%s/profile.json' % url_id, **kwargs)
        prof.__dict__['url_id'] = url_id
        return prof

    @property
    def user(self):
        """Returns a `User` instance for the TypePad member whose
        `UserProfile` this is."""
        return find_by_name('User').get_by_url_id(self.url_id)


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


class RelationshipStatus(TypePadObject):

    """A representation of just the relationship types of a relationship,
    without the associated endpoints."""

    types = fields.List(fields.Field())
    """A list of URIs instances that describe all the
    relationship edges included in this `RelationshipStatus`."""


class Relationship(TypePadObject):

    """The unidirectional relationship between a pair of entities.

    A Relationship can be between a user and a user (a contact relationship),
    or a user and a group (a membership). In either case, the relationship's
    status shows *all* the unidirectional relationships between the source and
    target entities.

    """

    id = fields.Field()
    """A URI that uniquely identifies this `Relationship` instance."""
    url_id = fields.Field(api_name='urlId')
    """An identifier for this `Relationship` that can be used in URLs."""
    source  = fields.Object('TypePadObject')
    """The entity (`User` or `Group`) from which this `Relationship` arises."""
    target  = fields.Object('TypePadObject')
    """The entity (`User` or `Group`) that is the object of this
    `Relationship`."""
    status  = fields.Object('RelationshipStatus')
    """A `RelationshipStatus` describing the types of relationship this
    `Relationship` instance represents."""
    created = fields.Dict(fields.Datetime())

    status_obj = fields.Link(RelationshipStatus, api_name='status')
    """A `RelationshipStatus` describing the types of relationship this
    `Relationship` instance represents.

    Unlike the `RelationshipStatus` instance in the `status` field, this
    linked `RelationshipsStatus` instance can be updated through ``POST``
    requests.

    """

    @property
    def xid(self):
        return xid_from_atom_id(self.id)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/relationships/%s.json' % self.url_id)

    def _rel_type_updater(uri):
        def update(self):
            rel_status = RelationshipStatus.get(self.status_obj._location, batch=False)
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

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/groups/%s.json' % self.url_id)

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

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/api-keys/%s.json' % self.api_key)

    @classmethod
    def get_by_api_key(cls, api_key):
        """Returns an `ApiKey` instance with the given consumer key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        return cls.get('/api-keys/%s.json' % api_key)


class AuthToken(TypePadObject):

    auth_token = fields.Field(api_name='authToken')
    target     = fields.Object('TypePadObject', api_name='targetObject')

    def make_self_link(self):
        # TODO: We don't have the API key, so we can't build a self link.
        return

    @classmethod
    def get_by_key_and_token(cls, api_key, auth_token):
        return cls.get('/auth-tokens/%s:%s.json' % (api_key, auth_token))


class Application(TypePadObject):

    """An application that can authenticate to the TypePad API using OAuth.

    An application is identified by its OAuth consumer key, which in the case
    of a hosted group is the same as the identifier for the group itself.

    """

    object_type = "tag:api.typepad.com,2009:Application"

    id           = fields.Field()
    """A URI that uniquely identifies this `Application`."""
    url_id = fields.Field()
    """The canonical identifier used to identify this `Application` in URLs."""
    name  = fields.Field()
    """The name of this `Application` as configured by the developer."""

    oauth_request_token_url = fields.Field(api_name='oauthRequestTokenUrl')
    """The service URL from which to request the OAuth request token."""
    oauth_authorization_url = fields.Field(api_name='oauthAuthorizationUrl')
    """The URL at which end users can authorize the application to access
    their accounts."""
    oauth_access_token_url = fields.Field(api_name='oauthAccessTokenUrl')
    """The service URL from which to request the OAuth access token."""
    oauth_identification_url = fields.Field(api_name='oauthIdentificationUrl')
    """The URL at which end users can identify themselves to sign into
    typepad, thereby signing into this site."""
    session_sync_script_url = fields.Field(api_name='sessionSyncScriptUrl')
    """The URL from which to request session sync javascript."""
    signout_url = fields.Field(api_name='signoutUrl')
    """The URL at which end users can sign out of TypePad."""
    user_flyouts_script_url = fields.Field(api_name='userFlyoutsScriptUrl')
    """The URL from which to request typepad user flyout javascript."""

    @property
    def browser_upload_endpoint(self):
        """The endpoint to use for uploading file assets directly to
        TypePad."""
        return urljoin(typepad.client.endpoint, '/browser-upload.json')

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/applications/%s.json' % self.url_id)

    @classmethod
    def get_by_api_key(cls, api_key, **kwargs):
        """Returns an `Application` instance by the API key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        import logging
        logging.getLogger("typepad.api").warn(
            'Application.get_by_api_key is deprecated')
        return cls.get('/applications/%s.json' % api_key, **kwargs)

    @property
    def user_flyouts_script(self):
        import logging
        logging.getLogger("typepad.api").warn(
            'Application.user_flyouts_script is deprecated; use %s.user_flyouts_script_url instead')
        return self.user_flyouts_script_url


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

    def __unicode__(self):
        return unicode(self.object)

    @property
    def xid(self):
        return xid_from_atom_id(self.id)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/events/%s.json' % self.url_id)


class Provider(TypePadObject):

    """An external service that provided an asset."""

    name = fields.Field()
    """The name of the external service."""
    uri  = fields.Field()
    """The main URL for the external service."""
    icon = fields.Field()
    """The URL for a 16 by 16 favicon for the external service."""


class Source(TypePadObject):

    """Information about an `Asset` instance imported from another service."""

    provider = fields.Object('Provider')
    """Description of the external service that provided the associated asset."""
    source   = fields.Field()
    by_user  = fields.Field(api_name='byUser')
    """Whether the associated asset was created on the external service by
    the TypePad asset's author, as opposed to imported by that TypePad user.

    For example, a YouTube video asset that the TypePad user *created* would
    have a `by_user` of ``True``. If the TypePad user instead posted someone
    else's YouTube video, `by_user` would be ``False``. (As far as TypePad is
    concerned, the TypePad user who posted it is the asset's author in either
    case.)

    """
    permalink_url = fields.Field(api_name='permalinkUrl')
    """The original URL of the imported asset on the external service."""


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
    in_reply_to  = fields.Object('AssetRef', api_name='inReplyTo')
    """For comment `Asset` instances, an `AssetRef` describing the asset on
    which this instance is a comment."""

    source       = fields.Object('Source')
    """If the `Asset` instance was imported from another service, a `Source`
    instance describing the original asset on the external service."""
    text_format  = fields.Field(api_name='textFormat')
    groups       = fields.List(fields.Field())

    rendered_content = fields.Field(api_name='renderedContent')
    """The content of this asset rendered to HTML. This is currently available only for `Post` and `Page` assets."""

    crosspost_accounts = fields.List(fields.Field(), api_name='crosspostAccounts')
    """A list of elsewhere account IDs to crosspost to."""

    comment_count = fields.Field(api_name='commentCount')
    """The number of comments left on this `Asset` instance."""
    favorite_count = fields.Field(api_name='favoriteCount')
    """The number of times this `Asset` instance has been marked as a favorite."""

    permalink_url = fields.Field(api_name='permalinkUrl')

    @property
    def xid(self):
        return xid_from_atom_id(self.id)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/assets/%s.json' % self.url_id)

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

    comments = fields.Link(ListOf('Asset'))
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


class ImageLink(TypePadObject):

    """A link to an image.

    Images hosted by TypePad can be resized with image sizing specs. See
    the `url_template` field and `at_size` method.

    """

    url = fields.Field()
    """The URL for the original full-size version of the image."""
    width = fields.Field()
    """The natural width of the original image in pixels."""
    height = fields.Field()
    """The natural height of the original image in pixels."""
    url_template = fields.Field(api_name='urlTemplate')
    """If TypePad is able to scale the image, the URL template for making
    resized image URLs.

    The URL template is combined with an *image sizing spec* to provide
    an URL to the same image at a different size.

    Only images hosted on TypePad are available in multiple sizes. Images
    such as Facebook and Twitter userpics are only available in one size.
    If an image is not resizable, its `url_template` will be ``None``.

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

    @property
    def href(self):
        import logging
        logging.getLogger("typepad.api").warn(
            '%s.href is deprecated; use %s.url instead' % self.__class__.__name__)
        return self.url


class Photo(Asset):

    """An entry in a blog."""

    object_type = "tag:api.typepad.com,2009:Photo"

    image_link = fields.Object('ImageLink', api_name='imageLink')


class AudioLink(TypePadObject):

    """A link to an audio recording."""

    url = fields.Field()
    """The URL to the MP3 representation of the audio stream."""
    duration = fields.Field()
    """The duration of the audio stream in seconds."""


class Audio(Asset):

    """An entry in a blog."""

    object_type = "tag:api.typepad.com,2009:Audio"

    audio_link = fields.Object('AudioLink', api_name='audioLink')


class VideoLink(TypePadObject):

    """A link to a web video."""

    embed_code = fields.Field(api_name='embedCode')
    """An opaque HTML fragment that, when embedded in an HTML page, will
    provide an inline player for the video."""
    permalink_url = fields.Field(api_name='permalinkUrl')
    """A URL to the HTML permalink page of the video.

    Use this field to specify the video when posting a new `Video` asset.
    When requesting an existing `Video` instance from the API,
    `permalink_url` will be ``None``.

    """

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

    @property
    def html(self):
        import logging
        logging.getLogger("typepad.api").warn(
            '%s.html is deprecated; use %s.embed_code instead' % self.__class__.__name__)
        return self.embed_code


class Video(Asset):

    """An entry in a blog."""

    object_type = "tag:api.typepad.com,2009:Video"

    video_link = fields.Object('VideoLink', api_name='videoLink')
    preview_image_link = fields.Object('ImageLink', api_name='previewImageLink')


class LinkAsset(Asset):

    """A shared link to some URL."""

    object_type = "tag:api.typepad.com,2009:Link"

    target_url = fields.Field(api_name='targetUrl')


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
