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

from urlparse import urljoin

from remoteobjects.dataobject import find_by_name

from typepad.tpobject import *
from typepad.tpobject import _ImageResizer, _VideoResizer
from typepad import fields
import typepad


class Account(TypePadObject):

    """A user account on an external website."""

    crosspostable = fields.Field()
    """`True` if this account can be used to crosspost, or `False` otherwise.

    An account can be used to crosspost if its service supports crossposting and
    the user has enabled crossposting for the specific account.

    """
    domain = fields.Field()
    """The DNS domain of the service that provides the account."""
    id = fields.Field()
    """A URI that serves as a globally unique identifier for the account."""
    provider_icon_url = fields.Field(api_name='providerIconUrl')
    """The URL of a 16-by-16 pixel icon that represents the service that provides
    this account."""
    provider_name = fields.Field(api_name='providerName')
    """A human-friendly name for the service that provides this account."""
    provider_url = fields.Field(api_name='providerURL')
    """**Deprecated.** The URL of the home page of the service that provides this
    account."""
    url = fields.Field()
    """The URL of the user's profile or primary page on the remote site, if known."""
    user_id = fields.Field(api_name='userId')
    """The machine identifier or primary key for the account, if known.

    (Some sites only have a `username`.)

    """
    username = fields.Field()
    """The username of the account, if known.

    (Some sites only have a `user_id`.)

    """

    @property
    def xid(self):
        return self.id.rsplit(':', 1)[-1]


class ApiKey(TypePadObject):

    api_key = fields.Field(api_name='apiKey')
    """The actual API key string.

    Use this as the consumer key when making an OAuth request.

    """
    owner = fields.Object('Application')
    """The application that owns this API key.

    :attrtype:`Application`

    """

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/api-keys/%s.json' % self.api_key)

    @classmethod
    def get_by_api_key(cls, api_key):
        """Returns an `ApiKey` instance with the given consumer key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        return cls.get('/api-keys/%s.json' % api_key)


class Application(TypePadObject):

    """An application that can authenticate to the TypePad API using OAuth.

    An application is identified by its OAuth consumer key, which in the case
    of a hosted group is the same as the identifier for the group itself.

    """

    _class_object_type = "Application"

    external_feed_subscriptions = fields.Link(ListOf('ExternalFeedSubscription'), api_name='external-feed-subscriptions')
    """Get a list of the application's active external feed subscriptions.

    :attrtype:`list of ExternalFeedSubscription`

    """
    groups = fields.Link(ListOf('Group'))
    """Get a list of groups in which a client using a ``app_full`` access auth
    token from this application can act.

    :attrtype:`list of Group`

    """
    id = fields.Field()
    """A string containing the canonical identifier that can be used to identify
    this application in URLs."""
    name = fields.Field()
    """The name of the application as provided by its developer."""
    oauth_access_token_url = fields.Field(api_name='oauthAccessTokenUrl')
    """The URL of the OAuth access token endpoint for this application."""
    oauth_authorization_url = fields.Field(api_name='oauthAuthorizationUrl')
    """The URL to send the user's browser to for the user authorization step."""
    oauth_identification_url = fields.Field(api_name='oauthIdentificationUrl')
    """The URL to send the user's browser to in order to identify who is logged in
    (that is, the "sign in" link)."""
    oauth_request_token_url = fields.Field(api_name='oauthRequestTokenUrl')
    """The URL of the OAuth request token endpoint for this application."""
    object_type = fields.Field(api_name='objectType')
    """The keyword identifying the type of object this is.

    For an Application object, `object_type` will be ``Application``.

    """
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    """**Deprecated.** The object types for this object.

    This set will contain the string ``tag:api.typepad.com,2009:Application`` for
    an Application object.


    :attrtype:`list`

    """
    session_sync_script_url = fields.Field(api_name='sessionSyncScriptUrl')
    """The URL of the session sync script."""
    signout_url = fields.Field(api_name='signoutUrl')
    """The URL to send the user's browser to in order to sign them out of TypePad."""
    user_flyouts_script_url = fields.Field(api_name='userFlyoutsScriptUrl')
    """The URL of a script to embed to enable the user flyouts functionality."""

    class _CreateExternalFeedSubscriptionPost(TypePadObject):
        callback_url = fields.Field(api_name='callbackUrl')
        """The URL which will receive notifications of new content in the subscribed
        feeds."""
        feed_idents = fields.List(fields.Field(), api_name='feedIdents')
        """A list of identifiers of the initial set of feeds to be subscribed to.

        :attrtype:`list`

        """
        filter_rules = fields.List(fields.Field(), api_name='filterRules')
        """A list of rules for filtering notifications to this subscription; each rule
        is a query string using the search API's syntax.

        :attrtype:`list`

        """
        secret = fields.Field()
        """An optional subscriber-provided opaque token that will be used to compute
        an HMAC digest to be sent along with each item delivered to the
        `callback_url`."""
        verify_token = fields.Field(api_name='verifyToken')
        """A subscriber-provided opaque token that will be echoed back in the
        verification request to assist the subscriber in identifying which
        subscription request is being verified."""
    class _CreateExternalFeedSubscriptionResponse(TypePadObject):
        subscription = fields.Object('ExternalFeedSubscription')
        """The subscription object that was created.

        :attrtype:`ExternalFeedSubscription`

        """
    create_external_feed_subscription = fields.ActionEndpoint(api_name='create-external-feed-subscription', post_type=_CreateExternalFeedSubscriptionPost, response_type=_CreateExternalFeedSubscriptionResponse)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/applications/%s.json' % self.id)

    @classmethod
    def get_by_id(cls, id, **kwargs):
        if id == '':
            raise ValueError("An id is required")
        obj = cls.get('/applications/%s.json' % id, **kwargs)
        obj.__dict__['id'] = id
        return obj

    @classmethod
    def get_by_api_key(cls, api_key, **kwargs):
        """Returns an `Application` instance by the API key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        import logging
        logging.getLogger("typepad.api").warn(
            '%s.get_by_api_key is deprecated' % cls.__name__)
        return cls.get('/applications/%s.json' % api_key, **kwargs)

    @property
    def browser_upload_endpoint(self):
        """The endpoint to use for uploading file assets directly to
        TypePad."""
        return urljoin(typepad.client.endpoint, '/browser-upload.json')

    user_flyouts_script = renamed_property(old='user_flyouts_script', new='user_flyouts_script_url')


class Asset(TypePadObject):

    """An item of content generated by a user."""

    _class_object_type = "Asset"

    author = fields.Object('User')
    """The user who created the selected asset.

    :attrtype:`User`

    """
    categories = fields.Link(ListObject)
    """Get a list of categories into which this asset has been placed within its
    blog.

    Currently supported only for `Post` assets that are posted within a blog.


    :attrtype:`list`

    """
    comment_count = fields.Field(api_name='commentCount')
    """The number of comments that have been posted in reply to this asset.

    This number includes comments that have been posted in response to other
    comments.

    """
    comment_tree = fields.Link(ListOf('CommentTreeItem'), api_name='comment-tree')
    """Get a list of assets that were posted in response to the selected asset and
    their depth in the response tree

    :attrtype:`list of CommentTreeItem`

    """
    comments = fields.Link(ListOf('Comment'))
    """Get a list of assets that were posted in response to the selected asset.

    POST: Create a new Comment asset as a response to the selected asset.


    :attrtype:`list of Comment`

    """
    container = fields.Object('ContainerRef')
    """An object describing the group or blog to which this asset belongs.

    :attrtype:`ContainerRef`

    """
    content = fields.Field()
    """The raw asset content.

    The `text_format` property describes how to format this data. Use this
    property to set the asset content in write operations. An asset posted in a
    group may have a `content` value up to 10,000 bytes long, while a `Post` asset
    in a blog may have up to 65,000 bytes of content.

    """
    crosspost_accounts = fields.List(fields.Field(), api_name='crosspostAccounts')
    """**Editable.** A set of identifiers for `Account` objects to which to
    crosspost this asset when it's posted.

    This property is omitted when retrieving existing assets.


    :attrtype:`list`

    """
    description = fields.Field()
    """The description of the asset."""
    excerpt = fields.Field()
    """A short, plain-text excerpt of the entry content.

    This is currently available only for `Post` assets.

    """
    extended_content = fields.Link('AssetExtendedContent', api_name='extended-content')
    """Get the extended content for the asset, if any.

    Currently supported only for `Post` assets that are posted within a blog.


    :attrtype:`AssetExtendedContent`

    """
    favorite_count = fields.Field(api_name='favoriteCount')
    """The number of distinct users who have added this asset as a favorite."""
    favorites = fields.Link(ListOf('Favorite'))
    """Get a list of favorites that have been created for the selected asset.

    :attrtype:`list of Favorite`

    """
    feedback_status = fields.Link('FeedbackStatus', api_name='feedback-status')
    """Get the feedback status of selected asset  PUT: Set the feedback status of
    selected asset

    :attrtype:`FeedbackStatus`

    """
    groups = fields.List(fields.Field())
    """**Deprecated.** An array of strings containing the `id` URI of the `Group`
    object that this asset is mapped into, if any.

    This property has been superseded by the `container` property.


    :attrtype:`list`

    """
    id = fields.Field()
    """A URI that serves as a globally unique identifier for the user."""
    is_favorite_for_current_user = fields.Field(api_name='isFavoriteForCurrentUser')
    """`True` if this asset is a favorite for the currently authenticated user, or
    `False` otherwise.

    This property is omitted from responses to anonymous requests.

    """
    media_assets = fields.Link(ListOf('Asset'), api_name='media-assets')
    """Get a list of media assets that are embedded in the content of the selected
    asset.

    :attrtype:`list of Asset`

    """
    object_type = fields.Field(api_name='objectType')
    """The keyword identifying the type of asset this is."""
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    """**Deprecated.** An array of object type identifier URIs identifying the
    type of this asset.

    Only the one object type URI for the particular type of asset this asset is
    will be present.


    :attrtype:`list`

    """
    permalink_url = fields.Field(api_name='permalinkUrl')
    """The URL that is this asset's permalink.

    This will be omitted if the asset does not have a permalink of its own (for
    example, if it's embedded in another asset) or if TypePad does not know its
    permalink.

    """
    publication_status = fields.Object('PublicationStatus', api_name='publicationStatus')
    """**Editable.** An object describing the visibility status and publication
    date for this asset.

    Only visibility status is editable.


    :attrtype:`PublicationStatus`

    """
    publication_status_obj = fields.Link('PublicationStatus', api_name='publication-status')
    """Get the publication status of selected asset  PUT: Set the publication
    status of selected asset

    :attrtype:`PublicationStatus`

    """
    published = fields.Datetime()
    """The time at which the asset was created, as a W3CDTF timestamp.

    :attrtype:`datetime`

    """
    reblogs = fields.Link(ListOf('Post'))
    """Get a list of posts that were posted as reblogs of the selected asset.

    :attrtype:`list of Post`

    """
    rendered_content = fields.Field(api_name='renderedContent')
    """The content of this asset rendered to HTML.

    This is currently available only for `Post` and `Page` assets.

    """
    source = fields.Object('AssetSource')
    """An object describing the site from which this asset was retrieved, if the
    asset was obtained from an external source.

    :attrtype:`AssetSource`

    """
    text_format = fields.Field(api_name='textFormat')
    """A keyword that indicates what formatting mode to use for the content of
    this asset.

    This can be ``html`` for assets the content of which is HTML,
    ``html_convert_linebreaks`` for assets the content of which is HTML but where
    paragraph tags should be added automatically, or ``markdown`` for assets the
    content of which is Markdown source. Other formatting modes may be added in
    future. Applications that present assets for editing should use this property
    to present an appropriate editor.

    """
    title = fields.Field()
    """The title of the asset."""
    url_id = fields.Field(api_name='urlId')
    """A string containing the canonical identifier that can be used to identify
    this object in URLs.

    This can be used to recognise where the same user is returned in response to
    different requests, and as a mapping key for an application's local data
    store.

    """

    class _AddCategoryPost(TypePadObject):
        category = fields.Field()
        """The category to add"""
    add_category = fields.ActionEndpoint(api_name='add-category', post_type=_AddCategoryPost)

    class _MakeCommentPreviewPost(TypePadObject):
        content = fields.Field()
        """The body of the comment."""
    class _MakeCommentPreviewResponse(TypePadObject):
        comment = fields.Object('Asset')
        """A mockup of the future comment.

        :attrtype:`Asset`

        """
    make_comment_preview = fields.ActionEndpoint(api_name='make-comment-preview', post_type=_MakeCommentPreviewPost, response_type=_MakeCommentPreviewResponse)

    class _RemoveCategoryPost(TypePadObject):
        category = fields.Field()
        """The category to remove"""
    remove_category = fields.ActionEndpoint(api_name='remove-category', post_type=_RemoveCategoryPost)

    class _UpdatePublicationStatusPost(TypePadObject):
        draft = fields.Field()
        """A boolean indicating whether the asset is a draft"""
        publication_date = fields.Field(api_name='publicationDate')
        """The publication date of the asset"""
        spam = fields.Field()
        """A boolean indicating whether the asset is spam; Comment only"""
    update_publication_status = fields.ActionEndpoint(api_name='update-publication-status', post_type=_UpdatePublicationStatusPost)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/assets/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/assets/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj

    actor = renamed_property(old='actor', new='author')

    def primary_object_type(self):
        try:
            return self.object_types[0]
        except (TypeError, IndexError):
            return

    @property
    def asset_ref(self):
        """An `AssetRef` instance representing this asset."""
        return AssetRef(url_id=self.url_id,
                        id=self.id,
                        author=self.author,
                        href='/assets/%s.json' % self.url_id,
                        type='application/json',
                        object_types=self.object_types,
                        object_type=self.object_type)

    def __unicode__(self):
        return self.title or self.content

    def __str__(self):
        return self.__unicode__()


class AssetExtendedContent(TypePadObject):

    rendered_extended_content = fields.Field(api_name='renderedExtendedContent')
    """The HTML rendered version of this asset's extended content, if it has any.

    Otherwise, this property is omitted.

    """


class AssetRef(TypePadObject):

    """A structure that refers to an asset without including its full
    content."""

    author = fields.Object('User')
    """The user who created the referenced asset.

    :attrtype:`User`

    """
    href = fields.Field()
    """The URL of a representation of the referenced asset."""
    id = fields.Field()
    """The URI from the referenced `Asset` object's `id` property."""
    object_type = fields.Field(api_name='objectType')
    """The keyword identifying the type of asset the referenced `Asset` object is."""
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    """**Deprecated.** An array of object type identifier URIs identifying the
    type of the referenced asset.

    Only the one object type URI for the particular type of asset the referenced
    asset is will be present.


    :attrtype:`list`

    """
    type = fields.Field()
    """The MIME type of the representation at the URL given in the `href`
    property."""
    url_id = fields.Field(api_name='urlId')
    """The canonical identifier from the referenced `Asset` object's `url_id`
    property."""

    def reclass_for_data(self, data):
        """Returns ``False``.

        This method prevents `AssetRef` instances from being reclassed when
        updated from a data dictionary based on the dictionary's
        ``objectTypes`` member.

        """
        # AssetRefs are for any object type, so don't reclass them.
        return False


class AssetSource(TypePadObject):

    """Information about an `Asset` instance imported from another service."""

    by_user = fields.Field(api_name='byUser')
    """**Deprecated.** `True` if this content is considered to be created by its
    author, or `False` if it's actually someone else's content imported by the
    asset author."""
    permalink_url = fields.Field(api_name='permalinkUrl')
    """The permalink URL of the resource from which the related asset was
    imported."""
    provider = fields.Dict(fields.Field())
    """**Deprecated.** Description of the external service provider from which
    this content was imported, if known.

    Contains ``name``, ``icon``, and ``uri`` properties. This property will be
    omitted if the service from which the related asset was imported is not
    recognized.


    :attrtype:`dict`

    """


class AudioLink(TypePadObject):

    """A link to an audio recording."""

    duration = fields.Field()
    """The duration of the audio stream in seconds.

    This property will be omitted if the length of the audio stream could not be
    determined.

    """
    url = fields.Field()
    """The URL of an MP3 representation of the audio stream."""


class AuthToken(TypePadObject):

    auth_token = fields.Field(api_name='authToken')
    """The actual auth token string.

    Use this as the access token when making an OAuth request.

    """
    target_object = fields.Object('TypePadObject', api_name='targetObject')
    """**Deprecated.** The root object to which this auth token grants access.

    This is a legacy field maintained for backwards compatibility with older
    clients, as auth tokens are no longer scoped to specific objects.


    :attrtype:`TypePadObject`

    """

    def make_self_link(self):
        # TODO: We don't have the API key, so we can't build a self link.
        return

    @classmethod
    def get_by_key_and_token(cls, api_key, auth_token):
        return cls.get('/auth-tokens/%s:%s.json' % (api_key, auth_token))

    target = renamed_property(old='target', new='target_object')


class Badge(TypePadObject):

    description = fields.Field()
    """A human-readable description of what a user must do to win this badge."""
    display_name = fields.Field(api_name='displayName')
    """A human-readable name for this badge."""
    id = fields.Field()
    """The canonical identifier that can be used to identify this badge in URLs.

    This can be used to recognise where the same badge is returned in response to
    different requests, and as a mapping key for an application's local data
    store.

    """
    image_link = fields.Object('ImageLink', api_name='imageLink')
    """A link to the image that depicts this badge to users.

    :attrtype:`ImageLink`

    """


class Blog(TypePadObject):

    categories = fields.Link(ListObject)
    """Get a list of categories which are defined for the selected blog.

    :attrtype:`list`

    """
    commenting_settings = fields.Link('BlogCommentingSettings', api_name='commenting-settings')
    """Get the commenting-related settings for this blog.

    :attrtype:`BlogCommentingSettings`

    """
    comments = fields.Link(ListOf('Comment'))
    crosspost_accounts = fields.Link(ListOf('Account'), api_name='crosspost-accounts')
    """Get  a list of accounts that can be used for crossposting with this blog.

    :attrtype:`list of Account`

    """
    description = fields.Field()
    """The description of the blog as provided by its owner."""
    home_url = fields.Field(api_name='homeUrl')
    """The URL of the blog's home page."""
    id = fields.Field()
    """A URI that serves as a globally unique identifier for the object."""
    media_assets = fields.Link(ListOf('Asset'), api_name='media-assets')
    """POST: Add a new media asset to the account that owns this blog.

    :attrtype:`list of Asset`

    """
    object_type = fields.Field(api_name='objectType')
    """The keyword identifying the type of object this is.

    For a Blog object, `object_type` will be ``Blog``.

    """
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    """**Deprecated.** An array of object type identifier URIs.

    This set will contain the string ``tag:api.typepad.com,2009:Blog`` for a Blog
    object.


    :attrtype:`list`

    """
    owner = fields.Object('User')
    """The user who owns the blog.

    :attrtype:`User`

    """
    page_assets = fields.Link(ListOf('Page'), api_name='page-assets')
    """Get a list of pages associated with the selected blog.

    POST: Add a new page to a blog


    :attrtype:`list of Page`

    """
    post_assets = fields.Link(ListOf('Post'), api_name='post-assets')
    """Get a list of posts associated with the selected blog.

    POST: Add a new post to a blog


    :attrtype:`list of Post`

    """
    post_by_email_settings = fields.Link('PostByEmailAddress', api_name='post-by-email-settings')
    stats = fields.Link('BlogStats')
    """Get data about the pageviews for the selected blog.

    :attrtype:`BlogStats`

    """
    title = fields.Field()
    """The title of the blog."""
    url_id = fields.Field(api_name='urlId')
    """A string containing the canonical identifier that can be used to identify
    this object in URLs.

    This can be used to recognise where the same user is returned in response to
    different requests, and as a mapping key for an application's local data
    store.

    """

    class _AddCategoryPost(TypePadObject):
        category = fields.Field()
        """The category to add"""
    add_category = fields.ActionEndpoint(api_name='add-category', post_type=_AddCategoryPost)

    class _DiscoverExternalPostAssetPost(TypePadObject):
        permalink_url = fields.Field(api_name='permalinkUrl')
        """The URL of the page whose external post stub is being retrieved."""
    class _DiscoverExternalPostAssetResponse(TypePadObject):
        asset = fields.Object('Asset')
        """The asset that acts as a stub for the given permalink.

        :attrtype:`Asset`

        """
    discover_external_post_asset = fields.ActionEndpoint(api_name='discover-external-post-asset', post_type=_DiscoverExternalPostAssetPost, response_type=_DiscoverExternalPostAssetResponse)

    class _RemoveCategoryPost(TypePadObject):
        category = fields.Field()
        """The category to remove"""
    remove_category = fields.ActionEndpoint(api_name='remove-category', post_type=_RemoveCategoryPost)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/blogs/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/blogs/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj


class BlogCommentingSettings(TypePadObject):

    captcha_required = fields.Field(api_name='captchaRequired')
    """`True` if this blog requires anonymous commenters to pass a CAPTCHA before
    submitting a comment, or `False` otherwise."""
    email_address_required = fields.Field(api_name='emailAddressRequired')
    """`True` if this blog requires anonymous comments to be submitted with an
    email address, or `False` otherwise."""
    html_allowed = fields.Field(api_name='htmlAllowed')
    """`True` if this blog allows commenters to use basic HTML formatting in
    comments, or `False` if HTML will be removed."""
    moderation_enabled = fields.Field(api_name='moderationEnabled')
    """`True` if this blog places new comments into a moderation queue for
    approval before they are displayed, or `False` if new comments may be
    available immediately."""
    signin_allowed = fields.Field(api_name='signinAllowed')
    """`True` if this blog allows users to sign in to comment, or `False` if all
    new comments are anonymous."""
    signin_required = fields.Field(api_name='signinRequired')
    """`True` if this blog requires users to be logged in in order to leave a
    comment, or `False` if anonymous comments will be rejected."""
    time_limit = fields.Field(api_name='timeLimit')
    """Number of days after a post is published that comments will be allowed.

    If the blog has no time limit for comments, this property will be omitted.

    """
    urls_auto_linked = fields.Field(api_name='urlsAutoLinked')
    """`True` if comments in this blog will automatically have any bare URLs
    turned into links, or `False` if URLs will be shown unlinked."""


class BlogStats(TypePadObject):

    daily_page_views = fields.Dict(fields.Field(), api_name='dailyPageViews')
    """A map containing the daily page views on the blog for the last 120 days.

    The keys of the map are dates in W3CDTF format, and the values are the integer
    number of page views on the blog for that date.


    :attrtype:`dict`

    """
    total_page_views = fields.Field(api_name='totalPageViews')
    """The total number of page views received by the blog for all time."""


class CommentTreeItem(TypePadObject):

    comment = fields.Object('Asset')
    """The comment asset at this point in the tree.

    :attrtype:`Asset`

    """
    depth = fields.Field()
    """The number of levels deep this comment is in the tree.

    A comment that is directly in reply to the root asset is 1 level deep. If a
    given comment has a depth of 1, all of the direct replies to that comment will
    have a depth of 2; their replies will have depth 3, and so forth.

    """


class ContainerRef(TypePadObject):

    display_name = fields.Field(api_name='displayName')
    """The display name of the blog or group, as set by its owner."""
    home_url = fields.Field(api_name='homeUrl')
    """The URL of the home page of the referenced blog or group."""
    id = fields.Field()
    """The URI from the `id` property of the referenced blog or group."""
    object_type = fields.Field(api_name='objectType')
    """The keyword identifying the type of object the referenced container is."""
    url_id = fields.Field(api_name='urlId')
    """The canonical identifier from the `url_id` property of the referenced blog
    or group."""


class Endpoint(TypePadObject):

    action_endpoints = fields.List(fields.Object('Endpoint'), api_name='actionEndpoints')
    """For noun endpoints, an array of action endpoints that it supports.

    :attrtype:`list of Endpoint`

    """
    can_have_id = fields.Field(api_name='canHaveId')
    """For noun endpoints, `True` if an id part is accepted, or `False` if the
    noun may only be used alone."""
    can_omit_id = fields.Field(api_name='canOmitId')
    """For noun endpoints, `True` if the id part can be ommitted, or `False` if it
    is always required."""
    filter_endpoints = fields.List(fields.Object('Endpoint'), api_name='filterEndpoints')
    """For endpoints that return lists, an array of filters that can be appended
    to the endpoint.

    :attrtype:`list of Endpoint`

    """
    format_sensitive = fields.Field(api_name='formatSensitive')
    """`True` if this endpoint requires a format suffix, or `False` otherwise."""
    name = fields.Field()
    """The name of the endpoint, as it appears in URLs."""
    parameterized = fields.Field()
    """For filter endpoints, `True` if a parameter is required on the filter, or
    `False` if it's a boolean filter."""
    post_object_type = fields.Object('ObjectType', api_name='postObjectType')
    """The type of object that this endpoint accepts for ``POST`` operations.

    This property is omitted if this endpoint does not accept ``POST`` requests.


    :attrtype:`ObjectType`

    """
    property_endpoints = fields.List(fields.Object('Endpoint'), api_name='propertyEndpoints')
    """For noun endpoints, an array of property endpoints that it supports.

    :attrtype:`list of Endpoint`

    """
    resource_object_type = fields.Object('ObjectType', api_name='resourceObjectType')
    """The type of object that this endpoint represents for ``GET``, ``PUT`` and
    ``DELETE`` operations.

    This property is omitted for action endpoints, as they do not represent
    resources.


    :attrtype:`ObjectType`

    """
    response_object_type = fields.Object('ObjectType', api_name='responseObjectType')
    """For action endpoints, the type of object that this endpoint returns on
    success.

    If the endpoint returns no payload on success, or if this is not an action
    endpoint, this property is omitted.


    :attrtype:`ObjectType`

    """
    supported_methods = fields.Dict(fields.Field(), api_name='supportedMethods')
    """A mapping of the HTTP methods that this endpoint accepts to the docstrings
    describing the result of each method.

    :attrtype:`dict`

    """
    supported_query_arguments = fields.List(fields.Field(), api_name='supportedQueryArguments')
    """The names of the query string arguments that this endpoint accepts.

    :attrtype:`list`

    """


class Entity(TypePadObject):

    id = fields.Field()
    """A URI that serves as a globally unique identifier for the object."""
    url_id = fields.Field(api_name='urlId')
    """A string containing the canonical identifier that can be used to identify
    this object in URLs.

    This can be used to recognise where the same user is returned in response to
    different requests, and as a mapping key for an application's local data
    store.

    """


class Event(TypePadObject):

    """An action that a user or group did.

    An event has an `actor`, which is the user or group that did the action; a
    set of `verbs` that describe what kind of action occured; and an `object`
    that is the object that the action was done to. In the current TypePad API
    implementation, only assets, users and groups can be the object of an
    event.

    """

    actor = fields.Object('Entity')
    """The user who performed the action described by this event.

    :attrtype:`Entity`

    """
    id = fields.Field()
    """A URI that serves as a globally unique identifier for the user."""
    object = fields.Object('TypePadObject')
    """The object to which the action described by this event was performed.

    :attrtype:`TypePadObject`

    """
    published = fields.Datetime()
    """The time at which the event was performed, as a W3CDTF timestamp.

    :attrtype:`datetime`

    """
    url_id = fields.Field(api_name='urlId')
    """A string containing the canonical identifier that can be used to identify
    this object in URLs.

    This can be used to recognise where the same user is returned in response to
    different requests, and as a mapping key for an application's local data
    store.

    """
    verb = fields.Field()
    """A keyword identifying the type of event this is."""
    verbs = fields.List(fields.Field())
    """**Deprecated.** An array of verb identifier URIs.

    This set will contain one verb identifier URI.


    :attrtype:`list`

    """

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/events/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/events/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj

    def __unicode__(self):
        return unicode(self.object)


class ExternalFeedSubscription(TypePadObject):

    callback_status = fields.Field(api_name='callbackStatus')
    """The HTTP status code that was returned by the last call to the
    subscription's callback URL."""
    callback_url = fields.Field(api_name='callbackUrl')
    """The URL to which to send notifications of new items in this subscription's
    feeds."""
    feeds = fields.Link(ListObject)
    """Get a list of strings containing the identifiers of the feeds to which this
    subscription is subscribed.

    :attrtype:`list`

    """
    filter_rules = fields.List(fields.Field(), api_name='filterRules')
    """A list of rules for filtering notifications to this subscription.

    Each rule is a full-text search query string, like those used with the
    ``/assets`` endpoint. An item will be delivered to the `callback_url` if it
    matches any one of these query strings.


    :attrtype:`list`

    """
    post_as_user_id = fields.List(fields.Field(), api_name='postAsUserId')
    """For a Group-owned subscription, the urlId of the User who will own the
    items posted into the group by the subscription.

    :attrtype:`list`

    """
    url_id = fields.Field(api_name='urlId')
    """The canonical identifier that can be used to identify this object in URLs.

    This can be used to recognise where the same user is returned in response to
    different requests, and as a mapping key for an application's local data
    store.

    """

    class _AddFeedsPost(TypePadObject):
        feed_idents = fields.List(fields.Field(), api_name='feedIdents')
        """A list of identifiers to be added to the subscription's set of feeds.

        :attrtype:`list`

        """
    add_feeds = fields.ActionEndpoint(api_name='add-feeds', post_type=_AddFeedsPost)

    class _RemoveFeedsPost(TypePadObject):
        feed_idents = fields.List(fields.Field(), api_name='feedIdents')
        """A list of identifiers to be removed from the subscription's set of feeds.

        :attrtype:`list`

        """
    remove_feeds = fields.ActionEndpoint(api_name='remove-feeds', post_type=_RemoveFeedsPost)

    class _UpdateFiltersPost(TypePadObject):
        filter_rules = fields.List(fields.Field(), api_name='filterRules')
        """The new list of rules for filtering notifications to this subscription;
        this will replace the subscription's existing rules.

        :attrtype:`list`

        """
    update_filters = fields.ActionEndpoint(api_name='update-filters', post_type=_UpdateFiltersPost)

    class _UpdateNotificationSettingsPost(TypePadObject):
        callback_url = fields.Field(api_name='callbackUrl')
        """The new callback URL to receive notifications of new content in this
        subscription's feeds."""
        secret = fields.Field()
        """An optional subscriber-provided opaque token that will be used to compute
        an HMAC digest to be sent along with each item delivered to the
        `callback_url`."""
        verify_token = fields.Field(api_name='verifyToken')
        """A subscriber-provided opaque token that will be echoed back in a
        verification request to the `callback_url`.

        Required, if the `callback_url` is being modified with this endpoint.

        """
    update_notification_settings = fields.ActionEndpoint(api_name='update-notification-settings', post_type=_UpdateNotificationSettingsPost)

    class _UpdateUserPost(TypePadObject):
        post_as_user_id = fields.Field(api_name='postAsUserId')
        """The `url_id` of the user who will own the assets and events posted into the
        group's stream by this subscription.

        The user must be an administrator of the group.

        """
    update_user = fields.ActionEndpoint(api_name='update-user', post_type=_UpdateUserPost)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/external-feed-subscriptions/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/external-feed-subscriptions/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj


class Favorite(TypePadObject):

    """A favorite of some other asset.

    Asserts that the user_id and asset_id parameter match ^\w+$."""

    _class_object_type = "Favorite"

    author = fields.Object('User')
    """The user who saved this favorite.

    That is, this property is the user who saved the target asset as a favorite,
    not the creator of that asset.


    :attrtype:`User`

    """
    id = fields.Field()
    """A URI that serves as a globally unique identifier for the favorite."""
    in_reply_to = fields.Object('AssetRef', api_name='inReplyTo')
    """A reference to the target asset that has been marked as a favorite.

    :attrtype:`AssetRef`

    """
    published = fields.Datetime()
    """The time that the favorite was created, as a W3CDTF timestamp.

    :attrtype:`datetime`

    """
    url_id = fields.Field(api_name='urlId')
    """A string containing the canonical identifier that can be used to identify
    this favorite in URLs.

    This can be used to recognise where the same favorite is returned in response
    to different requests, and as a mapping key for an application's local data
    store.

    """

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/favorites/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/favorites/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj

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


class FeedbackStatus(TypePadObject):

    allow_comments = fields.Field(api_name='allowComments')
    """`True` if new comments may be posted to the related asset, or `False` if no
    new comments are accepted."""
    allow_trackback = fields.Field(api_name='allowTrackback')
    """`True` if new trackback pings may be posted to the related asset, or
    `False` if no new pings are accepted."""
    show_comments = fields.Field(api_name='showComments')
    """`True` if comments should be displayed on the related asset's permalink
    page, or `False` if they should be hidden."""


class ImageLink(TypePadObject, _ImageResizer):

    """A link to an image.

    Images hosted by TypePad can be resized with image sizing specs. See
    the `url_template` field and `at_size` method.

    """

    height = fields.Field()
    """The height of the original image in pixels.

    If the height of the image is not available (for example, if the image isn't
    hosted on TypePad), this property will be omitted.

    """
    url = fields.Field()
    """The URL for the original, full size version of the image."""
    url_template = fields.Field(api_name='urlTemplate')
    """An URL template with which to build alternate sizes of this image.

    If present, replace the placeholder string ``{spec}`` with a valid sizing
    specifier to generate the URL for an alternate version of this image. This
    property is omitted if TypePad is unable to provide a scaled version of this
    image (for example, if the image isn't hosted on TypePad).

    """
    width = fields.Field()
    """The width of the original image in pixels.

    If the width of the image is not available (for example, if the image isn't
    hosted on TypePad), this property will be omitted.

    """

    href = renamed_property(old='url', new='href')


class ObjectProperty(TypePadObject):

    doc_string = fields.Field(api_name='docString')
    """A human-readable description of this property."""
    name = fields.Field()
    """The name of the property."""
    type = fields.Field()
    """The name of the type of this property."""


class ObjectType(TypePadObject):

    name = fields.Field()
    """The name of this object type.

    If this is an anonymous type representing the request or response of an action
    endpoint, this property is omitted.

    """
    parent_type = fields.Field(api_name='parentType')
    """The name of the parent type.

    This property is omitted if this object type has no parent type.

    """
    properties = fields.List(fields.Object('ObjectProperty'))
    """The properties belonging to objects of this object type.

    :attrtype:`list of ObjectProperty`

    """


class PostByEmailAddress(TypePadObject):

    email_address = fields.Field(api_name='emailAddress')
    """A private email address for posting via email."""


class PublicationStatus(TypePadObject):

    """A container for the flags that represent an asset's publication status.

    Publication status is currently represented by two flags: published and
    spam. The published flag is false when an asset is held for moderation,
    and can be set to true to publish the asset. The spam flag is true when
    TypePad's spam filter has determined that an asset is spam, or when the
    asset has been marked as spam by a moderator.

    """

    draft = fields.Field()
    """`True` if this asset is private (not yet published), or `False` if it has
    been published."""
    publication_date = fields.Field(api_name='publicationDate')
    """The time at which the related asset was (or will be) published, as a W3CDTF
    timestamp.

    If the related asset has been scheduled to be posted later, this property's
    timestamp will be in the future.

    """


class Relationship(TypePadObject):

    """The unidirectional relationship between a pair of entities.

    A Relationship can be between a user and a user (a contact relationship),
    or a user and a group (a membership). In either case, the relationship's
    status shows *all* the unidirectional relationships between the source and
    target entities.

    """

    created = fields.Dict(fields.Datetime())
    """A mapping of the relationship types present between the source and target
    objects to the times those types of relationship were established.

    The keys of the map are the relationship type URIs present in the
    relationship's `status` property; the values are W3CDTF timestamps for the
    times those relationship edges were created.


    :attrtype:`dict of datetime`

    """
    id = fields.Field()
    """A URI that serves as a globally unique identifier for the relationship."""
    source = fields.Object('Entity')
    """The source entity of the relationship.

    :attrtype:`Entity`

    """
    status = fields.Object('RelationshipStatus')
    """An object describing all the types of relationship that currently exist
    between the source and target objects.

    :attrtype:`RelationshipStatus`

    """
    status_obj = fields.Link('RelationshipStatus', api_name='status')
    """Get the status information for the selected relationship, including its
    types.

    PUT: Change the status information for the selected relationship, including
    its types.


    :attrtype:`RelationshipStatus`

    """
    target = fields.Object('Entity')
    """The target entity of the relationship.

    :attrtype:`Entity`

    """
    url_id = fields.Field(api_name='urlId')
    """A string containing the canonical identifier that can be used to identify
    this object in URLs.

    This can be used to recognise where the same relationship is returned in
    response to different requests, and as a mapping key for an application's
    local data store.

    """

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/relationships/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/relationships/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj

    def _rel_type_updater(uri):
        def update(self):
            rel_status = RelationshipStatus.get(self.status_obj._location, batch=False)
            if uri:
                rel_status.types = [uri]
            else:
                rel_status.types = []
            rel_status.put()
        return update

    block = _rel_type_updater("tag:api.typepad.com,2009:Blocked")
    unblock = _rel_type_updater(None)
    leave = _rel_type_updater(None)

    def _rel_type_checker(uri):
        def has_edge_with_uri(self):
            return uri in self.status.types
        return has_edge_with_uri

    is_member = _rel_type_checker("tag:api.typepad.com,2009:Member")
    is_admin = _rel_type_checker("tag:api.typepad.com,2009:Admin")
    is_blocked = _rel_type_checker("tag:api.typepad.com,2009:Blocked")


class RelationshipStatus(TypePadObject):

    """A representation of just the relationship types of a relationship,
    without the associated endpoints."""

    types = fields.List(fields.Field())
    """A list of relationship type URIs describing the types of the related
    relationship.

    :attrtype:`list`

    """


class UserBadge(TypePadObject):

    badge = fields.Object('Badge')
    """The badge that was won.

    :attrtype:`Badge`

    """
    earned_time = fields.Field(api_name='earnedTime')
    """The time that the user earned the badge given in `badge`."""


class UserProfile(TypePadObject):

    """Additional profile information about a TypePad user.

    This additional information is useful when showing information about a
    TypePad account directly, but is generally not required when linking to
    an ancillary TypePad account, such as the author of a post.

    """

    about_me = fields.Field(api_name='aboutMe')
    """The user's long description or biography, as a free-form string they
    provided."""
    avatar_link = fields.Object('ImageLink', api_name='avatarLink')
    """A link to an image representing this user.

    :attrtype:`ImageLink`

    """
    display_name = fields.Field(api_name='displayName')
    """The user's chosen display name."""
    email = fields.Field()
    """The user's email address.

    This property is only provided for authenticated requests if the user has
    shared it with the authenticated application, and the authenticated user is
    allowed to view it (as with administrators of groups the user has joined). In
    all other cases, this property is omitted.

    """
    follow_frame_content_url = fields.Field(api_name='followFrameContentUrl')
    """The URL of a widget that, when rendered in an ``iframe``, allows viewers to
    follow this user.

    Render this widget in an ``iframe`` 300 pixels wide and 125 pixels high.

    """
    gender = fields.Field()
    """The user's gender, as they provided it.

    This property is only provided for authenticated requests if the user has
    shared it with the authenticated application, and the authenticated user is
    allowed to view it (as with administrators of groups the user has joined). In
    all other cases, this property is omitted.

    """
    homepage_url = fields.Field(api_name='homepageUrl')
    """The address of the user's homepage, as a URL they provided.

    This property is omitted if the user has not provided a homepage.

    """
    id = fields.Field()
    """The URI from the related `User` object's `id` property."""
    interests = fields.List(fields.Field())
    """A list of interests provided by the user and displayed on their profile
    page.

    :attrtype:`list`

    """
    location = fields.Field()
    """The user's location, as a free-form string they provided."""
    membership_management_page_url = fields.Field(api_name='membershipManagementPageUrl')
    """The URL of a page where this user can manage their group memberships.

    If this is not the authenticated user's UserProfile object, this property is
    omitted.

    """
    preferred_username = fields.Field(api_name='preferredUsername')
    """The name the user has chosen for use in the URL of their TypePad profile
    page.

    This property can be used to select this user in URLs, although it is not a
    persistent key, as the user can change it at any time.

    """
    profile_edit_page_url = fields.Field(api_name='profileEditPageUrl')
    """The URL of a page where this user can edit their profile information.

    If this is not the authenticated user's UserProfile object, this property is
    omitted.

    """
    profile_page_url = fields.Field(api_name='profilePageUrl')
    """The URL of the user's TypePad profile page."""
    url_id = fields.Field(api_name='urlId')
    """The canonical identifier from the related `User` object's `url_id`
    property."""

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/users/%s/profile.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        """Returns the `UserProfile` instance with the given URL identifier."""
        if url_id == '':
            raise ValueError("An url_id is required")
        prof = cls.get('/users/%s/profile.json' % url_id, **kwargs)
        prof.__dict__['url_id'] = url_id
        prof.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return prof

    @property
    def user(self):
        """Returns a `User` instance for the TypePad member whose
        `UserProfile` this is."""
        return find_by_name('User').get_by_url_id(self.url_id)


class VideoLink(TypePadObject, _VideoResizer):

    """A link to a web video."""

    embed_code = fields.Field(api_name='embedCode')
    """An opaque HTML fragment that, when embedded in a HTML page, provides an
    inline player for the video."""
    permalink_url = fields.Field(api_name='permalinkUrl')
    """**Editable.** The permalink URL for the video on its own site.

    When posting a new video, send only the `permalink_url` property; videos on
    supported sites will be discovered and the embed code generated automatically.

    """

    html = renamed_property(old='html', new='embed_code')


class Audio(Asset):

    """An entry in a blog."""

    _class_object_type = "Audio"

    audio_link = fields.Object('AudioLink', api_name='audioLink')
    """A link to the audio stream that is this Audio asset's content.

    :attrtype:`AudioLink`

    """


class Comment(Asset):

    """A text comment posted in reply to some other asset."""

    _class_object_type = "Comment"

    in_reply_to = fields.Object('AssetRef', api_name='inReplyTo')
    """A reference to the asset that this comment is in reply to.

    :attrtype:`AssetRef`

    """


class Group(Entity):

    """A group that users can join, and to which users can post assets.

    TypePad API social applications are represented as groups.

    """

    _class_object_type = "Group"

    audio_assets = fields.Link(ListOf('Audio'), api_name='audio-assets')
    """POST: Create a new Audio asset within the selected group.

    :attrtype:`list of Audio`

    """
    avatar_link = fields.Object('ImageLink', api_name='avatarLink')
    """A link to an image representing this group.

    :attrtype:`ImageLink`

    """
    display_name = fields.Field(api_name='displayName')
    """The display name set by the group's owner."""
    events = fields.Link(ListOf('Event'))
    """Get a list of events describing actions performed in the selected group.

    :attrtype:`list of Event`

    """
    external_feed_subscriptions = fields.Link(ListOf('ExternalFeedSubscription'), api_name='external-feed-subscriptions')
    """Get a list of the group's active external feed subscriptions.

    :attrtype:`list of ExternalFeedSubscription`

    """
    link_assets = fields.Link(ListOf('Link'), api_name='link-assets')
    """POST: Create a new Link asset within the selected group.

    :attrtype:`list of Link`

    """
    memberships = fields.Link(ListOf('Relationship'))
    """Get a list of relationships between users and the selected group.

    :attrtype:`list of Relationship`

    """
    object_type = fields.Field(api_name='objectType')
    """A keyword describing the type of this object.

    For a group object, `object_type` will be ``Group``.

    """
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    """**Deprecated.** An array of object type identifier URIs.

    :attrtype:`list`

    """
    photo_assets = fields.Link(ListOf('Photo'), api_name='photo-assets')
    """POST: Create a new Photo asset within the selected group.

    :attrtype:`list of Photo`

    """
    post_assets = fields.Link(ListOf('Post'), api_name='post-assets')
    """POST: Create a new Post asset within the selected group.

    :attrtype:`list of Post`

    """
    site_url = fields.Field(api_name='siteUrl')
    """The URL to the front page of the group website."""
    tagline = fields.Field()
    """A tagline describing the group, as set by the group's owner."""
    video_assets = fields.Link(ListOf('Video'), api_name='video-assets')
    """POST: Create a new Video asset within the selected group.

    :attrtype:`list of Video`

    """

    class _AddMemberPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The urlId of the user who is being added."""
    add_member = fields.ActionEndpoint(api_name='add-member', post_type=_AddMemberPost)

    class _BlockUserPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The urlId of the user who is being blocked."""
    block_user = fields.ActionEndpoint(api_name='block-user', post_type=_BlockUserPost)

    class _CreateExternalFeedSubscriptionPost(TypePadObject):
        feed_idents = fields.List(fields.Field(), api_name='feedIdents')
        """A list of identifiers of the initial set of feeds to be subscribed to.

        :attrtype:`list`

        """
        filter_rules = fields.List(fields.Field(), api_name='filterRules')
        """A list of rules for filtering notifications to this subscription; each rule
        is a query string using the search API's syntax.

        :attrtype:`list`

        """
        post_as_user_id = fields.Field(api_name='postAsUserId')
        """the urlId of the user who will own the assets and events posted into the
        group's stream by this subscription.

        The user must be an administrator of the group.

        """
    class _CreateExternalFeedSubscriptionResponse(TypePadObject):
        subscription = fields.Object('ExternalFeedSubscription')
        """The subscription object that was created.

        :attrtype:`ExternalFeedSubscription`

        """
    create_external_feed_subscription = fields.ActionEndpoint(api_name='create-external-feed-subscription', post_type=_CreateExternalFeedSubscriptionPost, response_type=_CreateExternalFeedSubscriptionResponse)

    class _RemoveMemberPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The urlId of the user who is being removed."""
    remove_member = fields.ActionEndpoint(api_name='remove-member', post_type=_RemoveMemberPost)

    class _UnblockUserPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The urlId of the user who is being unblocked."""
    unblock_user = fields.ActionEndpoint(api_name='unblock-user', post_type=_UnblockUserPost)

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/groups/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/groups/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj


class Link(Asset):

    """A shared link to some URL."""

    _class_object_type = "Link"

    target_url = fields.Field(api_name='targetUrl')
    """The URL that is the target of this link."""


class Page(Asset):

    embedded_image_links = fields.List(fields.Object('ImageLink'), api_name='embeddedImageLinks')
    """A list of links to the images that are embedded within the content of this
    page.

    :attrtype:`list of ImageLink`

    """
    feedback_status = fields.Object('FeedbackStatus', api_name='feedbackStatus')
    """**Editable.** An object describing the comment and trackback behavior for
    this page.

    :attrtype:`FeedbackStatus`

    """
    filename = fields.Field()
    """**Editable.** The base name of the page, used to create the
    `permalink_url`."""


class Photo(Asset):

    """An entry in a blog."""

    _class_object_type = "Photo"

    image_link = fields.Object('ImageLink', api_name='imageLink')
    """A link to the image that is this Photo asset's content.

    :attrtype:`ImageLink`

    """


class Post(Asset):

    """An entry in a blog."""

    _class_object_type = "Post"

    categories = fields.List(fields.Field())
    """**Editable.** A list of categories associated with the post.

    :attrtype:`list`

    """
    embedded_audio_links = fields.List(fields.Object('AudioLink'), api_name='embeddedAudioLinks')
    """A list of links to the audio streams that are embedded within the content
    of this post.

    :attrtype:`list of AudioLink`

    """
    embedded_image_links = fields.List(fields.Object('ImageLink'), api_name='embeddedImageLinks')
    """A list of links to the images that are embedded within the content of this
    post.

    :attrtype:`list of ImageLink`

    """
    embedded_video_links = fields.List(fields.Object('VideoLink'), api_name='embeddedVideoLinks')
    """A list of links to the videos that are embedded within the content of this
    post.

    :attrtype:`list of VideoLink`

    """
    feedback_status = fields.Object('FeedbackStatus', api_name='feedbackStatus')
    """**Editable.** An object describing the comment and trackback behavior for
    this post.

    :attrtype:`FeedbackStatus`

    """
    filename = fields.Field()
    """**Editable.** The base name of the post to use when creating its
    `permalink_url`."""
    reblog_count = fields.Field(api_name='reblogCount')
    """The number of times this post has been reblogged by other people."""
    reblog_of = fields.Object('AssetRef', api_name='reblogOf')
    """A reference to a post of which this post is a reblog.

    :attrtype:`AssetRef`

    """


class User(Entity):

    """A TypePad user.

    This includes those who own TypePad blogs, those who use TypePad Connect
    and registered commenters who have either created a TypePad account or
    signed in with OpenID.

    """

    _class_object_type = "User"

    avatar_link = fields.Object('ImageLink', api_name='avatarLink')
    """A link to an image representing this user.

    :attrtype:`ImageLink`

    """
    badges = fields.Link(ListOf('UserBadge'))
    """Get a list of badges that the selected user has won.

    :attrtype:`list of UserBadge`

    """
    blogs = fields.Link(ListOf('Blog'))
    """Get a list of blogs that the selected user has access to.

    :attrtype:`list of Blog`

    """
    display_name = fields.Field(api_name='displayName')
    """The user's chosen display name."""
    elsewhere_accounts = fields.Link(ListOf('Account'), api_name='elsewhere-accounts')
    """Get a list of elsewhere accounts for the selected user.

    :attrtype:`list of Account`

    """
    email = fields.Field()
    """**Deprecated.** The user's email address.

    This property is only provided for authenticated requests if the user has
    shared it with the authenticated application, and the authenticated user is
    allowed to view it (as with administrators of groups the user has joined). In
    all other cases, this property is omitted.

    """
    events = fields.Link(StreamOf('Event'))
    """Get a list of events describing actions that the selected user performed.

    :attrtype:`list of Event`

    """
    favorites = fields.Link(ListOf('Favorite'))
    """Get a list of favorites that were listed by the selected user.

    POST: Create a new favorite in the selected user's list of favorites.


    :attrtype:`list of Favorite`

    """
    gender = fields.Field()
    """**Deprecated.** The user's gender, as they provided it.

    This property is only provided for authenticated requests if the user has
    shared it with the authenticated application, and the authenticated user is
    allowed to view it (as with administrators of groups the user has joined). In
    all other cases, this property is omitted.

    """
    interests = fields.List(fields.Field())
    """**Deprecated.** A list of interests provided by the user and displayed on
    the user's profile page.

    Use the `interests` property of the `UserProfile` object, which can be
    retrieved from the ``/users/{id}/profile`` endpoint.


    :attrtype:`list`

    """
    location = fields.Field()
    """**Deprecated.** The user's location, as a free-form string provided by
    them.

    Use the the `location` property of the related `UserProfile` object, which can
    be retrieved from the ``/users/{id}/profile`` endpoint.

    """
    memberships = fields.Link(ListOf('Relationship'))
    """Get a list of relationships that the selected user has with groups.

    :attrtype:`list of Relationship`

    """
    notifications = fields.Link(ListOf('Event'))
    """Get a list of events describing actions by users that the selected user is
    following.

    :attrtype:`list of Event`

    """
    object_type = fields.Field(api_name='objectType')
    """The keyword identifying the type of object this is.

    For a User object, `object_type` will be ``User``.

    """
    object_types = fields.List(fields.Field(), api_name='objectTypes')
    """**Deprecated.** An array of object type identifier URIs.

    :attrtype:`list`

    """
    preferred_username = fields.Field(api_name='preferredUsername')
    """The name the user has chosen for use in the URL of their TypePad profile
    page.

    This property can be used to select this user in URLs, although it is not a
    persistent key, as the user can change it at any time.

    """
    profile = fields.Link('UserProfile')
    """Get a more extensive set of user properties that can be used to build a
    user profile page.

    :attrtype:`UserProfile`

    """
    profile_page_url = fields.Field(api_name='profilePageUrl')
    """The URL of the user's TypePad profile page."""
    relationships = fields.Link(ListOf('Relationship'))
    """Get a list of relationships that the selected user has with other users,
    and that other users have with the selected user.

    :attrtype:`list of Relationship`

    """

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/users/%s.json' % self.url_id)

    @property
    def xid(self):
        return self.url_id

    @classmethod
    def get_by_id(cls, id, **kwargs):
        url_id = id.rsplit(':', 1)[-1]
        return cls.get_by_url_id(url_id, **kwargs)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        if url_id == '':
            raise ValueError("An url_id is required")
        obj = cls.get('/users/%s.json' % url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj

    @classmethod
    def get_self(cls, **kwargs):
        """Returns a `User` instance representing the account as whom the
        client library is authenticating."""
        return cls.get('/users/@self.json', **kwargs)


class Video(Asset):

    """An entry in a blog."""

    _class_object_type = "Video"

    preview_image_link = fields.Object('ImageLink', api_name='previewImageLink')
    """A link to a preview image or poster frame for this video.

    This property is omitted if no such image is available.


    :attrtype:`ImageLink`

    """
    video_link = fields.Object('VideoLink', api_name='videoLink')
    """A link to the video that is this Video asset's content.

    :attrtype:`VideoLink`

    """


browser_upload = BrowserUploadEndpoint()
