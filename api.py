"""

The `typepad.api` module contains `TypePadObject` implementations of all the
content objects provided in the TypePad API.

"""

from remoteobjects.dataobject import find_by_name

from typepad.tpobject import *
from typepad import fields


class User(TypePadObject):

    """A TypePad user.

    This includes those who own TypePad blogs, those who use TypePad Connect
    and registered commenters who have either created a TypePad account or
    signed in with OpenID.

    """

    object_type = "tag:api.typepad.com,2009:User"

    id                 = fields.Field(api_name='urlId')
    atom_id            = fields.Field(api_name='id')
    display_name       = fields.Field(api_name='displayName')
    preferred_username = fields.Field(api_name='preferredUsername')
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

    @classmethod
    def get_self(cls, **kwargs):
        """Returns a `User` instance representing the account as whom the
        client library is authenticating."""
        return cls.get('/users/@self.json', **kwargs)

    @classmethod
    def get_user(cls, userid):
        """Returns a `User` instance by their username or unique identifier."""
        return cls.get('/users/%s.json' % userid)


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

    source = fields.Object('TypePadObject')
    target = fields.Object('TypePadObject')
    status = fields.Object('RelationshipStatus')


class RelationshipStatus(TypePadObject):

    """A representation of just the relationship type of a relationship,
    without the associated endpoints."""

    types = fields.List(fields.Field())


class Group(TypePadObject):

    """A group that users can join, and to which users can post assets.

    TypePad API social applications are represented as groups.

    """

    object_type = "tag:api.typepad.com,2009:Group"

    id           = fields.Field(api_name='urlId')
    atom_id      = fields.Field(api_name='id')
    display_name = fields.Field(api_name='displayName')
    tagline      = fields.Field()
    urls         = fields.List(fields.Field())
    links        = fields.Object('LinkSet')

    # TODO: these aren't really Relationships because the target is really a group
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

    @classmethod
    def get_group(cls, groupid):
        """Returns a `Group` instance by the group's unique identifier."""
        return cls.get('/groups/%s.json' % groupid)


class Application(TypePadObject):

    """An application that can authenticate to the TypePad API using OAuth.

    An application is identified by its OAuth consumer key, which in the case
    of a hosted group is the same as the identifier for the group itself.

    """

    api_key = fields.Field()
    # TODO: this can be a User or Group
    owner   = fields.Object('Group')
    links   = fields.Object('LinkSet')

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

    @classmethod
    def get_application(cls, consumer_key):
        """Returns an `Application` instance by the consumer key."""
        return cls.get('/applications/%s.json' % consumer_key)


class Event(TypePadObject):

    """An action that a user or group did.

    An event has an `actor`, which is the user or group that did the action; a
    set of `verbs` that describe what kind of action occured; and an `object`
    that is the object that the action was done to. In the current TypePad API
    implementation, only assets, users and groups can be the object of an
    event.

    """

    id        = fields.Field(api_name='urlId')
    atom_id   = fields.Field(api_name='id')
    # TODO: vary these based on verb content? oh boy
    actor     = fields.Object('User')
    object    = fields.Object('Asset')
    published = fields.Datetime()
    verbs     = fields.List(fields.Field())

    def __unicode__(self):
        return unicode(self.object)

    @classmethod
    def get_event(cls, eventid):
        """Returns an `Event` instance using the given identifier."""
        return cls.get('/events/%s.json' % eventid)

    ## TODO remove this when event.object has a url _id
    ## this is currently used to delete an object in the entry view
    def get_asset(self):
        """Returns the `Asset` instance referenced by the event."""
        cls = find_by_name('Asset')
        return cls.get_asset(self.object.id)


class Asset(TypePadObject):

    """An item of content generated by a user."""

    object_type = "tag:api.typepad.com,2009:Asset"

    # documented fields
    id           = fields.Field(api_name='urlId')
    atom_id      = fields.Field(api_name='id')
    title        = fields.Field()
    author       = fields.Object('User')
    published    = fields.Datetime()
    updated      = fields.Datetime()
    summary      = fields.Field()
    content      = fields.Field()
    # TODO: categories should be Tags?
    categories   = fields.List(fields.Field())
    status       = fields.Object('PublicationStatus')
    links        = fields.Object('LinkSet')
    in_reply_to  = fields.Object('AssetRef', api_name='inReplyTo')

    @classmethod
    def get_asset(cls, assetid):
        """Returns a `Asset` instance by the identifier for the asset."""
        a = cls.get('/assets/%s.json' % assetid)
        a.atom_id = 'tag:api.typepad.com,2009:Asset-%s' % assetid
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
        # TODO: "This is also stupid. Why not have in_reply_to just be another asset??"
        return AssetRef(id=self.id,
                        ref=self.atom_id,
                        href='/assets/%s.json' % self.id,
                        type='application/json',
                        object_types=self.object_types)

    def __unicode__(self):
        return self.title or self.summary or self.content


class Comment(Asset):

    """A text comment posted in reply to some other asset."""

    object_type = "tag:api.typepad.com,2009:Comment"


class Favorite(Asset):

    """A favorite of some other asset."""

    object_type = "tag:api.typepad.com,2009:Favorite"


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

    ref  = fields.Field()
    id   = fields.Field(api_name='urlId')
    href = fields.Field()
    type = fields.Field()


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


# TODO: write this class
class Tag(TypePadObject):
    pass
