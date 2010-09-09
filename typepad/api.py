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

    badges = fields.Link(ListOf('Badge'), api_url='/applications/%(id)s/badges.json')
    """Get a list of badges defined by this application.

    :attrtype:`list of Badge`

    """
    external_feed_subscriptions = fields.Link(ListOf('ExternalFeedSubscription'), api_url='/applications/%(id)s/external-feed-subscriptions.json')
    """Get a list of the application's active external feed subscriptions.

    :attrtype:`list of ExternalFeedSubscription`

    """
    groups = fields.Link(ListOf('Group'), api_url='/applications/%(id)s/groups.json')
    """Get a list of groups in which a client using a ``app_full`` access auth
    token from this application can act.

    :attrtype:`list of Group`

    """
    id = fields.Field()
    """A string containing the canonical identifier that can be used to identify
    this application in URLs."""
    learning_badges = fields.Link(ListOf('Badge'), api_url='/applications/%(id)s/badges/@learning.json')
    """Get a list of all learning badges defined by this application.

    :attrtype:`list of Badge`

    """
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
    public_badges = fields.Link(ListOf('Badge'), api_url='/applications/%(id)s/badges/@public.json')
    """Get a list of all public badges defined by this application.

    :attrtype:`list of Badge`

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
    create_external_feed_subscription = fields.ActionEndpoint(post_type=_CreateExternalFeedSubscriptionPost, api_url='/applications/%(id)s/create-external-feed-subscription.json', response_type=_CreateExternalFeedSubscriptionResponse)

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
    categories = fields.Link(ListObject, api_url='/assets/%(id)s/categories.json')
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
    comment_tree = fields.Link(ListOf('CommentTreeItem'), api_url='/assets/%(id)s/comment-tree.json')
    """Get a list of assets that were posted in response to the selected asset and
    their depth in the response tree

    :attrtype:`list of CommentTreeItem`

    """
    comments = fields.Link(ListOf('Comment'), api_url='/assets/%(id)s/comments.json')
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
    extended_content = fields.Link('AssetExtendedContent', api_url='/assets/%(id)s/extended-content.json')
    """Get the extended content for the asset, if any.

    Currently supported only for `Post` assets that are posted within a blog.


    :attrtype:`AssetExtendedContent`

    """
    favorite_count = fields.Field(api_name='favoriteCount')
    """The number of distinct users who have added this asset as a favorite."""
    favorites = fields.Link(ListOf('Favorite'), api_url='/assets/%(id)s/favorites.json')
    """Get a list of favorites that have been created for the selected asset.

    :attrtype:`list of Favorite`

    """
    feedback_status = fields.Link('FeedbackStatus', api_url='/assets/%(id)s/feedback-status.json')
    """Get the feedback status of the selected asset.

    PUT: Set the feedback status of the selected asset.


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
    is_conversations_answer = fields.Field(api_name='isConversationsAnswer')
    """**Deprecated.** `True` if this asset is an answer to a TypePad
    Conversations question, or absent otherwise.

    This property is deprecated and will be replaced with something more useful in
    future.

    """
    is_favorite_for_current_user = fields.Field(api_name='isFavoriteForCurrentUser')
    """`True` if this asset is a favorite for the currently authenticated user, or
    `False` otherwise.

    This property is omitted from responses to anonymous requests.

    """
    media_assets = fields.Link(ListOf('Asset'), api_url='/assets/%(id)s/media-assets.json')
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
    publication_status_obj = fields.Link('PublicationStatus', api_url='/assets/%(id)s/publication-status.json')
    """Get the publication status of the selected asset.

    PUT: Set the publication status of the selected asset.


    :attrtype:`PublicationStatus`

    """
    published = fields.Datetime()
    """The time at which the asset was created, as a W3CDTF timestamp.

    :attrtype:`datetime`

    """
    reblog_of = fields.Object('AssetRef', api_name='reblogOf')
    """**Deprecated.** If this asset was created by 'reblogging' another asset,
    this property describes the original asset.

    :attrtype:`AssetRef`

    """
    reblog_of_url = fields.Field(api_name='reblogOfUrl')
    """**Deprecated.** If this asset was created by 'reblogging' another asset or
    some other arbitrary web page, this property contains the URL of the item that
    was reblogged."""
    reblogs = fields.Link(ListOf('Post'), api_url='/assets/%(id)s/reblogs.json')
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
    add_category = fields.ActionEndpoint(post_type=_AddCategoryPost, api_url='/assets/%(id)s/add-category.json')

    class _MakeCommentPreviewPost(TypePadObject):
        content = fields.Field()
        """The body of the comment."""
    class _MakeCommentPreviewResponse(TypePadObject):
        comment = fields.Object('Asset')
        """A mockup of the future comment.

        :attrtype:`Asset`

        """
    make_comment_preview = fields.ActionEndpoint(post_type=_MakeCommentPreviewPost, api_url='/assets/%(id)s/make-comment-preview.json', response_type=_MakeCommentPreviewResponse)

    class _RemoveCategoryPost(TypePadObject):
        category = fields.Field()
        """The category to remove"""
    remove_category = fields.ActionEndpoint(post_type=_RemoveCategoryPost, api_url='/assets/%(id)s/remove-category.json')

    class _UpdatePublicationStatusPost(TypePadObject):
        draft = fields.Field()
        """A boolean indicating whether the asset is a draft"""
        publication_date = fields.Field(api_name='publicationDate')
        """The publication date of the asset"""
        spam = fields.Field()
        """A boolean indicating whether the asset is spam; Comment only"""
    update_publication_status = fields.ActionEndpoint(post_type=_UpdatePublicationStatusPost, api_url='/assets/%(id)s/update-publication-status.json')

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/assets/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/assets/%(id)s.json' % {'id': url_id}, **kwargs)
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
    excerpt = fields.Field()
    """A short, plain-text excerpt of the referenced asset's content.

    This is currently available only for `Post` assets.

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
    permalink_url = fields.Field(api_name='permalinkUrl')
    """The URL that is the referenced asset's permalink.

    This will be omitted if the asset does not have a permalink of its own (for
    example, if it's embedded in another asset) or if TypePad does not know its
    permalink.

    """
    title = fields.Field()
    """The title of the referenced asset, if it has one."""
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
    is_learning = fields.Field(api_name='isLearning')
    """A learning badge is given for a special achievement a user accomplishes
    while filling out a new account.

    `True` if this is a learning badge, or `False` if this is a normal badge.

    """


class Blog(TypePadObject):

    categories = fields.Link(ListObject, api_url='/blogs/%(id)s/categories.json')
    """Get a list of categories which are defined for the selected blog.

    :attrtype:`list`

    """
    commenting_settings = fields.Link('BlogCommentingSettings', api_url='/blogs/%(id)s/commenting-settings.json')
    """Get the commenting-related settings for this blog.

    :attrtype:`BlogCommentingSettings`

    """
    crosspost_accounts = fields.Link(ListOf('Account'), api_url='/blogs/%(id)s/crosspost-accounts.json')
    """Get  a list of accounts that can be used for crossposting with this blog.

    :attrtype:`list of Account`

    """
    description = fields.Field()
    """The description of the blog as provided by its owner."""
    home_url = fields.Field(api_name='homeUrl')
    """The URL of the blog's home page."""
    id = fields.Field()
    """A URI that serves as a globally unique identifier for the object."""
    media_assets = fields.Link(ListOf('Asset'), api_url='/blogs/%(id)s/media-assets.json')
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
    page_assets = fields.Link(ListOf('Page'), api_url='/blogs/%(id)s/page-assets.json')
    """Get a list of pages associated with the selected blog.

    POST: Add a new page to a blog


    :attrtype:`list of Page`

    """
    post_assets = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets.json')
    """Get a list of posts associated with the selected blog.

    POST: Add a new post to a blog


    :attrtype:`list of Post`

    """
    post_assets_by_category = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets/@by-category/%(category)s.json')
    """Get all visibile posts in the selected blog that have been assigned to the
    given category.

    :attrtype:`list of Post`

    """
    post_assets_by_filename = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets/@by-filename/%(fileRef)s.json', api_url_names={'file_ref': 'fileRef'})
    """Get zero or one posts matching the given year, month and filename.

    :attrtype:`list of Post`

    """
    post_assets_by_month = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets/@by-month/%(month)s.json')
    """Get all visible posts in the selected blog that have a publication date
    within the selected month, specified as a string of the form "YYYY-MM".

    :attrtype:`list of Post`

    """
    post_by_email_settings_by_user = fields.Link('PostByEmailAddress', api_url='/blogs/%(id)s/post-by-email-settings/@by-user/%(userId)s.json', api_url_names={'user_id': 'userId'})
    """Get the selected user's post-by-email address

    :attrtype:`PostByEmailAddress`

    """
    published_comments = fields.Link(ListOf('Comment'), api_url='/blogs/%(id)s/comments/@published.json')
    """Return a pageable list of published comments associated with the selected
    blog

    :attrtype:`list of Comment`

    """
    published_post_assets_by_category = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets/@published/@by-category/%(category)s.json')
    """Get the published posts in the selected blog that have been assigned to the
    given category.

    :attrtype:`list of Post`

    """
    published_post_assets_by_month = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets/@published/@by-month/%(month)s.json')
    """Get the posts that were published within the selected month (YYYY-MM) from
    the selected blog.

    :attrtype:`list of Post`

    """
    published_recent_comments = fields.Link(ListOf('Comment'), api_url='/blogs/%(id)s/comments/@published/@recent.json')
    """Return the fifty most recent published comments associated with the
    selected blog

    :attrtype:`list of Comment`

    """
    published_recent_post_assets = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets/@published/@recent.json')
    """Get the most recent 50 published posts in the selected blog.

    :attrtype:`list of Post`

    """
    recent_post_assets = fields.Link(ListOf('Post'), api_url='/blogs/%(id)s/post-assets/@recent.json')
    """Get the most recent 50 posts in the selected blog, including draft and
    scheduled posts.

    :attrtype:`list of Post`

    """
    stats = fields.Link('BlogStats', api_url='/blogs/%(id)s/stats.json')
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
    add_category = fields.ActionEndpoint(post_type=_AddCategoryPost, api_url='/blogs/%(id)s/add-category.json')

    class _BeginImportPost(TypePadObject):
        create_users = fields.Field(api_name='createUsers')
        """Attempt to create new users based on ones found in the imported data.

        This is not yet supported.

        """
        match_users = fields.Field(api_name='matchUsers')
        """Attempt to create new users based on ones found in the imported data.

        This is not yet supported.

        """
    class _BeginImportResponse(TypePadObject):
        job = fields.Object('ImporterJob')
        """The `ImporterJob` object representing the job that was created.

        :attrtype:`ImporterJob`

        """
    begin_import = fields.ActionEndpoint(post_type=_BeginImportPost, api_url='/blogs/%(id)s/begin-import.json', response_type=_BeginImportResponse)

    class _DiscoverExternalPostAssetPost(TypePadObject):
        permalink_url = fields.Field(api_name='permalinkUrl')
        """The URL of the page whose external post stub is being retrieved."""
    class _DiscoverExternalPostAssetResponse(TypePadObject):
        asset = fields.Object('Asset')
        """The asset that acts as a stub for the given permalink.

        :attrtype:`Asset`

        """
    discover_external_post_asset = fields.ActionEndpoint(post_type=_DiscoverExternalPostAssetPost, api_url='/blogs/%(id)s/discover-external-post-asset.json', response_type=_DiscoverExternalPostAssetResponse)

    class _RemoveCategoryPost(TypePadObject):
        category = fields.Field()
        """The category to remove"""
    remove_category = fields.ActionEndpoint(post_type=_RemoveCategoryPost, api_url='/blogs/%(id)s/remove-category.json')

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/blogs/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/blogs/%(id)s.json' % {'id': url_id}, **kwargs)
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
    """A URI that serves as a globally unique identifier for the event."""
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

    This can be used to recognise where the same event is returned in response to
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
        return urljoin(typepad.client.endpoint, '/events/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/events/%(id)s.json' % {'id': url_id}, **kwargs)
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
    feeds = fields.Link(ListObject, api_url='/external-feed-subscriptions/%(id)s/feeds.json')
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
    add_feeds = fields.ActionEndpoint(post_type=_AddFeedsPost, api_url='/external-feed-subscriptions/%(id)s/add-feeds.json')

    class _RemoveFeedsPost(TypePadObject):
        feed_idents = fields.List(fields.Field(), api_name='feedIdents')
        """A list of identifiers to be removed from the subscription's set of feeds.

        :attrtype:`list`

        """
    remove_feeds = fields.ActionEndpoint(post_type=_RemoveFeedsPost, api_url='/external-feed-subscriptions/%(id)s/remove-feeds.json')

    class _UpdateFiltersPost(TypePadObject):
        filter_rules = fields.List(fields.Field(), api_name='filterRules')
        """The new list of rules for filtering notifications to this subscription;
        this will replace the subscription's existing rules.

        :attrtype:`list`

        """
    update_filters = fields.ActionEndpoint(post_type=_UpdateFiltersPost, api_url='/external-feed-subscriptions/%(id)s/update-filters.json')

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
    update_notification_settings = fields.ActionEndpoint(post_type=_UpdateNotificationSettingsPost, api_url='/external-feed-subscriptions/%(id)s/update-notification-settings.json')

    class _UpdateUserPost(TypePadObject):
        post_as_user_id = fields.Field(api_name='postAsUserId')
        """The `url_id` of the user who will own the assets and events posted into the
        group's stream by this subscription.

        The user must be an administrator of the group.

        """
    update_user = fields.ActionEndpoint(post_type=_UpdateUserPost, api_url='/external-feed-subscriptions/%(id)s/update-user.json')

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/external-feed-subscriptions/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/external-feed-subscriptions/%(id)s.json' % {'id': url_id}, **kwargs)
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
        return urljoin(typepad.client.endpoint, '/favorites/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/favorites/%(id)s.json' % {'id': url_id}, **kwargs)
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


class ImportAsset(TypePadObject):

    author = fields.Object('ImportAuthor')
    """Object representing as much detail as available about the author of the
    imported asset

    :attrtype:`ImportAuthor`

    """
    content = fields.Field()
    """Body or content of the imported asset"""
    foreign_id = fields.Field(api_name='foreignId')
    """Foreign site ID for the asset"""
    object_type = fields.Field(api_name='objectType')
    """The type of the imported asset"""
    published = fields.Field()
    """The time at which the asset was published, as a W3CDTF timestamp"""
    title = fields.Field()
    """Title of the imported asset"""


class ImportAuthor(TypePadObject):

    display_name = fields.Field(api_name='displayName')
    """Foreign author's displayed name"""
    email = fields.Field()
    """Foreign author's email address"""
    homepage_url = fields.Field(api_name='homepageUrl')
    """URL for foreign author's homepage"""
    openid_identifier = fields.Field(api_name='openidIdentifier')
    """Foreign author's OpenID identifier"""
    typepad_user_id = fields.Field(api_name='typepadUserId')
    """Known TypePad user id for foreign author"""


class ImporterJob(TypePadObject):

    assets_imported = fields.Field(api_name='assetsImported')
    """Number of assets imported by this job"""
    create_users = fields.Field(api_name='createUsers')
    """`True` if TypePad will create new users for the auther information given in
    the submitted payloads."""
    last_foreign_id = fields.Field(api_name='lastForeignId')
    """The foreign ID of the last asset importered"""
    last_submit_time = fields.Field(api_name='lastSubmitTime')
    """The time the last asset was submitted, as a W3CDTF timestamp."""
    match_users = fields.Field(api_name='matchUsers')
    """`True` if TypePad will attempt to find matching users for the author
    information given in the submitted payloads."""
    url_id = fields.Field(api_name='urlId')
    """ID of the import job"""


class ObjectProperty(TypePadObject):

    doc_string = fields.Field(api_name='docString')
    """A human-readable description of this property."""
    name = fields.Field()
    """The name of the property."""
    type = fields.Field()
    """The name of the type of this property."""


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
    status_obj = fields.Link('RelationshipStatus', api_url='/relationships/%(id)s/status.json')
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
        return urljoin(typepad.client.endpoint, '/relationships/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/relationships/%(id)s.json' % {'id': url_id}, **kwargs)
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


class TrendingAssets(TypePadObject):

    pass

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
    suppress_events = fields.Field(api_name='suppressEvents')
    """**Editable.** An optional, write-only flag indicating that asset creation
    should not trigger notification events such as emails or dashboard entries.

    Not available to all applications.

    """


class Comment(Asset):

    """A text comment posted in reply to some other asset."""

    _class_object_type = "Comment"

    in_reply_to = fields.Object('AssetRef', api_name='inReplyTo')
    """A reference to the asset that this comment is in reply to.

    :attrtype:`AssetRef`

    """
    root = fields.Object('AssetRef')
    """A reference to the root asset that this comment is descended from.

    This will be the same as `in_reply_to` unless this comment is a reply to
    another comment.


    :attrtype:`AssetRef`

    """
    suppress_events = fields.Field(api_name='suppressEvents')
    """**Editable.** An optional, write-only flag indicating that asset creation
    should not trigger notification events such as emails or dashboard entries.

    Not available to all applications.

    """


class Group(Entity):

    """A group that users can join, and to which users can post assets.

    TypePad API social applications are represented as groups.

    """

    _class_object_type = "Group"

    admin_memberships = fields.Link(ListOf('Relationship'), api_url='/groups/%(id)s/memberships/@admin.json')
    """Get a list of relationships that have the Admin type between users and the
    selected group.

    :attrtype:`list of Relationship`

    """
    audio_assets = fields.Link(ListOf('Audio'), api_url='/groups/%(id)s/audio-assets.json')
    """Get a list of recently created Audio assets from the selected group.

    POST: Create a new Audio asset within the selected group.


    :attrtype:`list of Audio`

    """
    avatar_link = fields.Object('ImageLink', api_name='avatarLink')
    """A link to an image representing this group.

    :attrtype:`ImageLink`

    """
    blocked_memberships = fields.Link(ListOf('Relationship'), api_url='/groups/%(id)s/memberships/@blocked.json')
    """Get a list of relationships that have the Blocked type between users and
    the selected groups.

    (Restricted to group admin.)


    :attrtype:`list of Relationship`

    """
    display_name = fields.Field(api_name='displayName')
    """The display name set by the group's owner."""
    events = fields.Link(ListOf('Event'), api_url='/groups/%(id)s/events.json')
    """Get a list of events describing actions performed in the selected group.

    :attrtype:`list of Event`

    """
    external_feed_subscriptions = fields.Link(ListOf('ExternalFeedSubscription'), api_url='/groups/%(id)s/external-feed-subscriptions.json')
    """Get a list of the group's active external feed subscriptions.

    :attrtype:`list of ExternalFeedSubscription`

    """
    link_assets = fields.Link(ListOf('Link'), api_url='/groups/%(id)s/link-assets.json')
    """Returns a list of recently created Link assets from the selected group.

    POST: Create a new Link asset within the selected group.


    :attrtype:`list of Link`

    """
    member_memberships = fields.Link(ListOf('Relationship'), api_url='/groups/%(id)s/memberships/@member.json')
    """Get a list of relationships that have the Member type between users and the
    selected group.

    :attrtype:`list of Relationship`

    """
    memberships = fields.Link(ListOf('Relationship'), api_url='/groups/%(id)s/memberships.json')
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
    photo_assets = fields.Link(ListOf('Photo'), api_url='/groups/%(id)s/photo-assets.json')
    """Get a list of recently created Photo assets from the selected group.

    POST: Create a new Photo asset within the selected group.


    :attrtype:`list of Photo`

    """
    post_assets = fields.Link(ListOf('Post'), api_url='/groups/%(id)s/post-assets.json')
    """Get a list of recently created Post assets from the selected group.

    POST: Create a new Post asset within the selected group.


    :attrtype:`list of Post`

    """
    site_url = fields.Field(api_name='siteUrl')
    """The URL to the front page of the group website."""
    tagline = fields.Field()
    """A tagline describing the group, as set by the group's owner."""
    video_assets = fields.Link(ListOf('Video'), api_url='/groups/%(id)s/video-assets.json')
    """Get a list of recently created Video assets from the selected group.

    POST: Create a new Video asset within the selected group.


    :attrtype:`list of Video`

    """

    class _AddMemberPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The `url_id` of the user who is being added."""
    add_member = fields.ActionEndpoint(post_type=_AddMemberPost, api_url='/groups/%(id)s/add-member.json')

    class _BlockUserPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The `url_id` of the user who is being blocked."""
    block_user = fields.ActionEndpoint(post_type=_BlockUserPost, api_url='/groups/%(id)s/block-user.json')

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
        """The `url_id` of the user who will own the assets and events posted into the
        group's stream by this subscription.

        The user must be an administrator of the group.

        """
    class _CreateExternalFeedSubscriptionResponse(TypePadObject):
        subscription = fields.Object('ExternalFeedSubscription')
        """The subscription object that was created.

        :attrtype:`ExternalFeedSubscription`

        """
    create_external_feed_subscription = fields.ActionEndpoint(post_type=_CreateExternalFeedSubscriptionPost, api_url='/groups/%(id)s/create-external-feed-subscription.json', response_type=_CreateExternalFeedSubscriptionResponse)

    class _RemoveMemberPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The `url_id` of the user who is being removed."""
    remove_member = fields.ActionEndpoint(post_type=_RemoveMemberPost, api_url='/groups/%(id)s/remove-member.json')

    class _UnblockUserPost(TypePadObject):
        user_id = fields.Field(api_name='userId')
        """The `url_id` of the user who is being unblocked."""
    unblock_user = fields.ActionEndpoint(post_type=_UnblockUserPost, api_url='/groups/%(id)s/unblock-user.json')

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/groups/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/groups/%(id)s.json' % {'id': url_id}, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%s' % url_id
        return obj

        

class ImportComment(ImportAsset):

    in_reply_to_foreign_id = fields.Field(api_name='inReplyToForeignId')
    """Foreign site ID for the parent of this comment"""
    status = fields.Field()
    """Keyword indicating publication status of comment"""


class ImportPage(ImportAsset):

    pass

class ImportPost(ImportAsset):

    pass

class Link(Asset):

    """A shared link to some URL."""

    _class_object_type = "Link"

    suppress_events = fields.Field(api_name='suppressEvents')
    """**Editable.** An optional, write-only flag indicating that asset creation
    should not trigger notification events such as emails or dashboard entries.

    Not available to all applications.

    """
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
    suppress_events = fields.Field(api_name='suppressEvents')
    """**Editable.** An optional, write-only flag indicating that asset creation
    should not trigger notification events such as emails or dashboard entries.

    Not available to all applications.

    """


class Photo(Asset):

    """An entry in a blog."""

    _class_object_type = "Photo"

    image_link = fields.Object('ImageLink', api_name='imageLink')
    """A link to the image that is this Photo asset's content.

    :attrtype:`ImageLink`

    """
    suppress_events = fields.Field(api_name='suppressEvents')
    """**Editable.** An optional, write-only flag indicating that asset creation
    should not trigger notification events such as emails or dashboard entries.

    Not available to all applications.

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
    suppress_events = fields.Field(api_name='suppressEvents')
    """**Editable.** An optional, write-only flag indicating that asset creation
    should not trigger notification events such as emails or dashboard entries.

    Not available to all applications.

    """


class User(Entity):

    """A TypePad user.

    This includes those who own TypePad blogs, those who use TypePad Connect
    and registered commenters who have either created a TypePad account or
    signed in with OpenID.

    """

    _class_object_type = "User"

    admin_memberships = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/memberships/@admin.json')
    """Get a list of relationships that have an Admin type that the selected user
    has with groups.

    :attrtype:`list of Relationship`

    """
    avatar_link = fields.Object('ImageLink', api_name='avatarLink')
    """A link to an image representing this user.

    :attrtype:`ImageLink`

    """
    badges = fields.Link(ListOf('UserBadge'), api_url='/users/%(id)s/badges.json')
    """Get a list of badges that the selected user has won.

    :attrtype:`list of UserBadge`

    """
    blogs = fields.Link(ListOf('Blog'), api_url='/users/%(id)s/blogs.json')
    """Get a list of blogs that the selected user has access to.

    :attrtype:`list of Blog`

    """
    display_name = fields.Field(api_name='displayName')
    """The user's chosen display name."""
    elsewhere_accounts = fields.Link(ListOf('Account'), api_url='/users/%(id)s/elsewhere-accounts.json')
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
    events = fields.Link(StreamOf('Event'), api_url='/users/%(id)s/events.json')
    """Get a list of events describing actions that the selected user performed.

    :attrtype:`list of Event`

    """
    events_by_group = fields.Link(ListOf('Event'), api_url='/users/%(id)s/events/@by-group/%(groupId)s.json', api_url_names={'group_id': 'groupId'})
    """Get a list of events describing actions that the selected user performed in
    a particular group.

    :attrtype:`list of Event`

    """
    favorites = fields.Link(ListOf('Favorite'), api_url='/users/%(id)s/favorites.json')
    """Get a list of favorites that were listed by the selected user.

    POST: Create a new favorite in the selected user's list of favorites.


    :attrtype:`list of Favorite`

    """
    follower_relationships = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/relationships/@follower.json')
    """Get a list of relationships that have the Contact type that the selected
    user has with other users.

    :attrtype:`list of Relationship`

    """
    follower_relationships_by_group = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/relationships/@follower/@by-group/%(groupId)s.json', api_url_names={'group_id': 'groupId'})
    """Get a list of relationships that have the Contact type that the selected
    user has with other users, constrained to members of a particular group.

    :attrtype:`list of Relationship`

    """
    following_relationships = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/relationships/@following.json')
    """Get a list of relationships that have the Contact type that other users
    have with the selected user.

    :attrtype:`list of Relationship`

    """
    following_relationships_by_group = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/relationships/@following/@by-group/%(groupId)s.json', api_url_names={'group_id': 'groupId'})
    """Get a list of relationships that have the Contact type that other users
    have with the selected user, constrained to members of a particular group.

    :attrtype:`list of Relationship`

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
    learning_badges = fields.Link(ListOf('UserBadge'), api_url='/users/%(id)s/badges/@learning.json')
    """Get a list of learning badges that the selected user has won.

    :attrtype:`list of UserBadge`

    """
    location = fields.Field()
    """**Deprecated.** The user's location, as a free-form string provided by
    them.

    Use the the `location` property of the related `UserProfile` object, which can
    be retrieved from the ``/users/{id}/profile`` endpoint.

    """
    member_memberships = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/memberships/@member.json')
    """Get a list of relationships that have a Member type that the selected user
    has with groups.

    :attrtype:`list of Relationship`

    """
    memberships = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/memberships.json')
    """Get a list of relationships that the selected user has with groups.

    :attrtype:`list of Relationship`

    """
    memberships_by_group = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/memberships/@by-group/%(groupId)s.json', api_url_names={'group_id': 'groupId'})
    """Get a list containing only the relationship between the selected user and a
    particular group, or an empty list if the user has no relationship with the
    group.

    :attrtype:`list of Relationship`

    """
    notifications = fields.Link(ListOf('Event'), api_url='/users/%(id)s/notifications.json')
    """Get a list of events describing actions by users that the selected user is
    following.

    :attrtype:`list of Event`

    """
    notifications_by_group = fields.Link(ListOf('Event'), api_url='/users/%(id)s/notifications/@by-group/%(groupId)s.json', api_url_names={'group_id': 'groupId'})
    """Get a list of events describing actions in a particular group by users that
    the selected user is following.

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
    profile = fields.Link('UserProfile', api_url='/users/%(id)s/profile.json')
    """Get a more extensive set of user properties that can be used to build a
    user profile page.

    :attrtype:`UserProfile`

    """
    profile_page_url = fields.Field(api_name='profilePageUrl')
    """The URL of the user's TypePad profile page."""
    public_badges = fields.Link(ListOf('UserBadge'), api_url='/users/%(id)s/badges/@public.json')
    """Get a list of public badges that the selected user has won.

    :attrtype:`list of UserBadge`

    """
    relationships = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/relationships.json')
    """Get a list of relationships that the selected user has with other users,
    and that other users have with the selected user.

    :attrtype:`list of Relationship`

    """
    relationships_by_group = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/relationships/@by-group/%(groupId)s.json', api_url_names={'group_id': 'groupId'})
    """Get a list of relationships that the selected user has with other users,
    and that other users have with the selected user, constrained to members of a
    particular group.

    :attrtype:`list of Relationship`

    """
    relationships_by_user = fields.Link(ListOf('Relationship'), api_url='/users/%(id)s/relationships/@by-user/%(userId)s.json', api_url_names={'user_id': 'userId'})
    """Get a list of relationships that the selected user has with a single other
    user.

    :attrtype:`list of Relationship`

    """

    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/users/%(id)s.json' % {'id': self.url_id})

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
        obj = cls.get('/users/%(id)s.json' % {'id': url_id}, **kwargs)
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
    suppress_events = fields.Field(api_name='suppressEvents')
    """**Editable.** An optional, write-only flag indicating that asset creation
    should not trigger notification events such  as emails or dashboard entries.

    Not available to all applications.

    """
    video_link = fields.Object('VideoLink', api_name='videoLink')
    """A link to the video that is this Video asset's content.

    :attrtype:`VideoLink`

    """


browser_upload = BrowserUploadEndpoint()
