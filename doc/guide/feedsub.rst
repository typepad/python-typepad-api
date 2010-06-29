=========================
The feed subscription API
=========================

TypePad provides a feed subscription API that lets you subscribe to TypePad and web feed content. Once your application is subscribed to a feed, TypePad will push new items that appear in that feed to an endpoint on your application.

The feed subscription API is only available using authenticated requests. Use your TypePad application's and anonymous access token to subscribe to feeds and modify subscriptions. For more on authentication, see :doc:`../tut/auth`.

Subscribing a `Group`
=====================

A good use of the feed subscription API is to automatically post from third-party web sites into a TypePad `Group`. For instance, if you run a bicycle shop and provide a `Group` powered web site for your fans and customers, you can use the feed subscription API to automatically post all your Twitter tweets to the group where your fans can comment on them.

To add a subscription to a group, use the `Group.create_external_feed_subscription()` method.

.. function:: typepad.Group.create_external_feed_subscription(feed_idents, filter_rules, post_as_user_id)

   Creates a new feed subscription for the group.

   The subscription is subscribed to the feeds named in ``feed_idents``, a list of feed URLs. The items discovered in these feeds are filtered by ``filter_rules``, a list of search queries, before being posted to the group: if the subscription has filter rules, only items that match all of the rules are delivered. Items that are not filtered out are posted to the group as the `User` identified by ``post_as_user_id``, a TypePad user URL identifier.

   The return value is an object the ``subscription`` attribute of which is the `ExternalFeedSubscription` for the new subscription.

Once your `Group` has some subscriptions, you can also retrieve those subscriptions as the group's `external_feed_subscriptions` list.

.. attribute:: typepad.Group.external_feed_subscriptions

   A list of `ExternalFeedSubscription` instances representing the group's subscriptions.


Subscribing an `Application`
============================

In addition to subscribing feed items directly into groups, you can also subscribe to feed content to have it pushed by TypePad to your web application. Once subscribed, TypePad will send HTTP requests to your web app when new feed content is available. (This does mean your web application must be visible to TypePad over the public Internet to use this API.) While subscription occurs through the TypePad API, subscriptions are verified and content is pushed using the PubSubHubbub protocol.

To create a new subscription, use the `Application.create_external_feed_subscription()` method.

.. function:: typepad.Application.create_external_feed_subscription(callback_url, feed_idents, filter_rules, verify_token, secret=None)

   Creates and immediately verifies a new feed subscription for the application.

   The subscription is subscribed to the feeds named in ``feed_idents``, a list of feed URLs. The items discovered in these feeds are filtered by ``filter_rules``, a list of search queries, before being posted to the group. Items that are not filtered out are posted in HTTP ``POST`` requests to ``callback_url``, your application's feed subscription callback URL, according to the PubSubHubbub protocol.

   If ``secret`` is provided, its string value will be stored as a special signing token, and new content will be posted to your callback URL using PubSubHubbub's Authenticated Content Distribution protocol.

   This method will return an object with a ``subscription`` attribute containing an `ExternalFeedSubscription` instance representing the new subscription.

.. note::

   TypePad will attempt to verify your callback URL *during* your call to this method; your web application must be available to respond to TypePad while this call occurs. For more on the format of the verification and content requests, and a reference to Authentication Content Distribution, see `the TypePad endpoint documentation`_.

As with `Group` instances, `Application` instances also provide lists of their existing subscriptions in their `external_feed_subscriptions` endpoints.

.. attribute:: typepad.Application.external_feed_subscriptions

   A list of `ExternalFeedSubscription` instances representing the `Application` instance's subscriptions.

These subscriptions can be modified in the same ways as `Group` subscriptions, described above.

.. _the TypePad endpoint documentation: http://www.typepad.com/services/apidocs/endpoints/applications/%253Cid%253E/create-external-feed-subscription


Modifying subscriptions
=======================

You can modify an existing `ExternalFeedSubscription` instance in several ways, whether it was newly created or pulled from the list endpoint.

If you have only the ID of an `ExternalFeedSubscription`, load the instance with the `get_by_url_id()` method.

.. automethod:: typepad.api.ExternalFeedSubscription.get_by_url_id

   Returns the `ExternalFeedSubscription` identified by ``url_id``.

For any `ExternalFeedSubscription` instance, you can list its feeds using its `feeds` endpoint, as well as change its feeds using the `add_feeds()` and `remove_feeds()` methods.

.. attribute:: typepad.ExternalFeedSubscription.feeds

   A list of the feed URLs (as strings) to which the `ExternalFeedSubscription` is subscribed.

.. method:: typepad.ExternalFeedSubscription.add_feeds(feed_idents)

   Adds the specified feed identifiers to the `ExternalFeedSubscription`.

   For ``feed_idents``, specify a list of feed URLs to add to the subscription. Feed identifiers that are already part of the subscription are ignored. This method returns no value.

.. method:: typepad.ExternalFeedSubscription.remove_feeds(feed_idents)

   Removes the specified feed identifiers from the `ExternalFeedSubscription`.

   For ``feed_idents``, specify a list of feed URLs to remove from the subscription. Feed identifiers that are not part of the subscription are ignored. This method returns no value.

In addition to changing the subscribed feeds, you can also change the filters using the `update_filters()` method.

.. method:: typepad.ExternalFeedSubscription.update_filters(filter_rules)

   Changes the subscription's filters to those specified.

   For ``filter_rules``, specify a list of strings containing search queries by which to filter. The subscription's existing filters will be replaced by the filters you specify. To remove all the filters from a subscription, pass an empty list for ``filter_rules``. This method returns no value.

You can also change the way a subscription is delivered. For a `Group` subscription, use the `ExternalFeedSubscription` instance's `update_user()` method; for an `Application` subscription, the `update_notification_settings()` method.

.. method:: typepad.ExternalFeedSubscription.update_user(post_as_user_id)

   Changes a `Group` subscription to deliver feed items to the group as posted by the identified user.

   Specify the new author's TypePad URL identifier as ``post_as_user_id``.

.. method:: typepad.ExternalFeedSubscription.update_notification_settings(callback_url, secret=None, verify_token=None)

   Changes the callback URL or secure secret used to deliver this subscription's new feed items to your web application.

   Specify your application's callback URL for the ``callback_url`` parameter. If ``callback_url`` is different from the subscription's existing callback URL (that is, you're asking to change the callback URL), TypePad will send the new URL a subscription verification request; in that case, a verification token to use in that request is required in the ``verify_token`` parameter.

   If you specify a ``secret``, TypePad will use that secret to deliver future content per PubSubHubbub's Authenticated Content Distribution protocol. If no secret is provided, future content delivery will not be authenticated.
