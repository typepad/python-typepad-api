TypePad Content Objects
=======================

.. automodule:: typepad.api

   .. autoclass:: User
      :members:

      .. attribute:: id

         A URI that uniquely identifies this `User`.

         A user's `id` URI is unique across groups, TypePad environments, and
         time. When associating local content to a user, use this identifier
         as the "foreign key" to an API user.

      .. attribute:: url_id
      
         An identifier for this `User` that can be used in URLs.

         A user's `url_id` is unique only across groups in one TypePad
         environment, so you should use `id`, not `url_id`, to associate data
         with a `User`. When constructing URLs to API resources in a given
         TypePad environment, however, use `url_id`.

      .. attribute:: display_name

         The name chosen by the `User` for display purposes.

         Use this name when displaying the `User`'s name in link text or other
         text for human viewing.

      .. attribute:: preferred_username

         The identifying part of the `User`'s chosen TypePad Profile URL.

         This identifier is unique across groups, but not across TypePad
         environments. TypePad users can change their Profile URLs, so this
         identifier can also change over time for a given user. Use this name
         when constructing a link to the user's profile on your local site.
         (Use the appropriate `Link` from the `User` instance's `links` for
         the full TypePad Profile URL.)

      .. attribute:: about_me

         The biographical text provided by the `User`.

         This text is displayed on the user's TypePad Profile page. The string
         may contain multiple lines of text separated by newline characters.

      .. attribute:: interests

         A list of strings identifying interests, provided by the `User`.

      .. attribute:: links

         A `LinkSet` containing various URLs and API endpoints related to this
         `User`.

   .. autoclass:: ElsewhereAccount
      :members:

      .. attribute:: domain

         The DNS domain of the site to which the account belongs.

      .. attribute:: username

         The username of the account, if known and appropriate.

         Some services don't have `username` attributes, only `user_id`
         attributes.

      .. attribute:: user_id

         The primary identifier of the account, if known.

      .. attribute:: url

         The URL of the corresponding profile page on the service's web site,
         if known.

      .. attribute:: provider_name

         The name of the service providing this account, suitable for
         presentation to human viewers.

      .. attribute:: provider_url

         The URL of the home page of the service providing this account.

      .. attribute:: provider_icon_url

         The URL of a 16×16 pixel icon representing the service providing this
         account.

   .. autoclass:: Relationship
      :members:

      .. attribute:: source

         The entity (`User` or `Group`) from which this `Relationship` arises.

      .. attribute:: target

         The entity (`User` or `Group`) that is the object of this
         `Relationship`.

      .. attribute:: status

         A `RelationshipStatus` describing the types of relationship this
         `Relationship` instance represents.

      .. attribute:: links

         A `LinkSet` containing other URLs and API endpoints related to this
         relationship.

   .. autoclass:: RelationshipType
      :members:

   .. autoclass:: RelationshipStatus
      :members:

      .. attribute:: types

         A list of `RelationshipType` instances that describe all the
         relationship edges included in this `RelationshipStatus`.

   .. autoclass:: Group
      :members:

      .. attribute:: id

         A URI that uniquely identifies this `Group`.

         A group's `id` URI is unique across groups, TypePad environments, and
         time. When associating local content with a group, use this
         identifier as the "foreign key" to an API group.

      .. attribute:: url_id

         An identifier for this `Group` that can be used in URLs.

         A group's `url_id` is unique in only one TypePad environment, so you
         should use `id`, not `url_id`, to associate data with a `Group`. When
         constructing URLs to API resources in a given TypePad environment,
         however, use `url_id`.

      .. attribute:: display_name

         The name chosen for the `Group` for display purposes.

         Use this name when displaying the `Group`'s name in link text or
         other text for human viewing.

      .. attribute:: tagline

         The tagline or subtitle of this `Group`.

      .. attribute:: links

         A `LinkSet` containing URLs and API endpoints related to this
         `Group`.

   .. autoclass:: Application
      :members:

      .. attribute:: api_key

         The consumer key for this Application.

      .. attribute:: owner

         The entity (`Group` or `User`) that owns this Application.

      .. attribute:: links

         A `LinkSet` containing the API endpoints associated with this
         Application.

   .. autoclass:: Event
      :members:

      .. attribute:: id

         A URI that uniquely identifies this `Event`.

      .. attribute:: url_id

         An identifier for this `Event` that can be used in URLs.

      .. attribute:: actor

         The entity (`User` or `Group`) that performed the described `Event`.

         For example, if the `Event` represents someone joining a group,
         `actor` would be the `User` who joined the group.

      .. attribute:: object

         The object (a `User`, `Group`, or `Asset`) that is the target of the
         described `Event`.

         For example, if the `Event` represents someone joining a group,
         `object` would be the group the `User` joined.

      .. attribute:: verbs

         A list of URIs describing what this `Event` describes.

         For example, if the `Event` represents someone joining a group,
         `verbs` would contain the one URI
         ``tag:api.typepad.com,2009:JoinedGroup``.

   .. autoclass:: Asset
      :members:

      .. attribute:: id

         A URI that uniquely identifies this `Asset`.

      .. attribute:: url_id

         An identifier for this `Asset` that can be used in URLs.

      .. attribute:: title

         The title of the asset as provided by its author.

         For some types of asset, the title may be an empty string. This
         indicates the asset has no title.

      .. attribute:: author

         The `User` who created the `Asset`.

      .. attribute:: published

         A `datetime.datetime` indicating when the `Asset` was created.

      .. attribute:: updated

         A `datetime.datetime` indicating when the `Asset` was last modified.

      .. attribute:: summary

         For a media type of `Asset`, the HTML description or caption given by
         its author.

      .. attribute:: content

         For a text type of `Asset`, the HTML content of the `Asset`.

      .. attribute:: categories

         A list of `Tag` instances associated with the `Asset`.

      .. attribute:: status

         The `PublicationStatus` describing the state of the `Asset`.

      .. attribute:: links

         A `LinkSet` containing various URLs and API endpoints related to this
         `User`.

      .. attribute:: in_reply_to

         For comment `Asset` instances, an `AssetRef` describing the asset on
         which this instance is a comment.

      .. attribute:: source
      .. attribute:: text_format

   .. autoclass:: Comment
      :members:

   .. autoclass:: Favorite
      :members:

   .. autoclass:: Post
      :members:

   .. autoclass:: Photo
      :members:

   .. autoclass:: Audio
      :members:

   .. autoclass:: Video
      :members:

   .. autoclass:: LinkAsset
      :members:

   .. autoclass:: Document
      :members:

   .. autoclass:: AssetRef
      :members:

      .. attribute:: ref

         A URI that uniquely identifies the referenced `Asset`.

         The URI matches the one in the referenced `Asset` instance's ``id``
         field.

      .. attribute:: url_id

         An identifier for this `Asset` that can be used in URLs.

         The identifier matches the one in the referenced `Asset` instance's
         ``url_id``.

      .. attribute:: href

         The URL at which a representation of the corresponding asset can be
         retrieved.

      .. attribute:: type

         The MIME type of the representation available from the ``href`` URL.

      .. attribute:: author

         The `User` who created the referenced asset.

   .. autoclass:: PublicationStatus
      :members:

      .. attribute:: published

         A boolean flag indicating whether the `Asset` with this
         `PublicationStatus` is available for public viewing (``True``) or
         held for moderation (``False``).

      .. attribute:: spam

         A boolean flag indicating whether the `Asset` with this
         `PublicationStatus` has been marked as spam by the automated filter
         or a site moderator (``True``) or not (``False``).

   .. autoclass:: Tag
      :members:

      .. attribute:: term

         The word or phrase that constitutes the tag.

      .. attribute:: count

         The number of times the `Tag` has been used in the requested context.

         When returned in the list of tags for a group, the count is the
         number of times the `Tag` has been used for assets in that group.
         When returned in the list of tags for a `User`, the count is the
         number of times the tag has been used on that author's assets. When
         returned in the list of tags for an `Asset`, the count is ``1`` if
         the tag has been applied to that asset.
