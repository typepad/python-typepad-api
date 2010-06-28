=========================
The feed subscription API
=========================

TypePad provides a feed subscription API that lets you subscribe to TypePad and web feed content. Once your application is subscribed to a feed, TypePad will push new items that appear in that feed to an endpoint on your application.

Subscribing a `Group`
=====================

A good use of the feed subscription API is to automatically post from third-party web sites into a TypePad `Group`. For instance, if you run a bicycle shop and provide a `Group` powered web site for your fans and customers, you can use the feed subscription API to automatically post all your Twitter tweets to the group where your fans can comment on them.

To add a subscription to a group, use the `Group.create_external_feed_subscription()` method.

.. function:: typepad.Group.create_external_feed_subscription(feed_idents, filter_rules, post_as_user_id)

   Creates a new feed subscription for the group.

   The subscription is subscribed to the feeds named in ``feed_idents``, a list of feed URLs. The items discovered in these feeds are filtered by ``filter_rules``, a list of search queries, before being posted to the group. Items that are not filtered out are posted to the group as the `User` identified by ``post_as_user_id``, a TypePad user URL identifier.

   The return value is an object the ``subscription`` attribute of which is the `ExternalFeedSubscription` for the new subscription.

Once your `Group` has some subscriptions, you can also retrieve those subscriptions as the group's `external_feed_subscriptions` list.

.. attribute:: typepad.Group.external_feed_subscriptions

   A list of `ExternalFeedSubscription` instances representing the group's subscriptions.

Modifying subscriptions
=======================

You can modify an existing `ExternalFeedSubscription` instance in several ways, whether it was newly created or pulled from the list endpoint.

Subscribing an `Application`
============================

In addition to subscribing feed items directly into groups, you can also subscribe to feed content to have it pushed by TypePad to your web application. Once subscribed, TypePad will send HTTP requests to your web app when new feed content is available. (This does mean your web application must be visible to TypePad over the public Internet to use this API.) While subscription occurs through the TypePad API, subscriptions are verified and content is pushed using the PubSubHubbub protocol.

To create a new subscription, use the `Application.create_external_feed_subscription()` method.

.. function:: typepad.Application.create_external_feed_subscription(callback_url, feed_idents, filter_rules, verify_token, secret=None)

   Creates and immediately verifies a new feed subscription for the application.

   The subscription is subscribed to the feeds named in ``feed_idents``, a list of feed URLs. The items discovered in these feeds are filtered by ``filter_rules``, a list of search queries, before being posted to the group. Items that are not filtered out are posted in HTTP ``POST`` requests to ``callback_url``, your application's feed subscription callback URL, according to the PubSubHubbub protocol.

   If ``secret`` is provided, its string value will be stored as a special signing token, and new content will be posted to your callback URL using PubSubHubbub's Authenticated Content Distribution protocol.

   This method will return an object with a ``subscription`` attribute containing an `ExternalFeedSubscription` instance representing the new subscription.

TypePad will attempt to verify your callback URL *during* your call to this method; your web application must be available to respond to TypePad while this call occurs. For more on the format of the verification and content requests, and a reference to Authentication Content Distribution, see the `TypePad endpoint documentation`_.

As with `Group` instances, `Application` instances also provide lists of their existing subscriptions in their `external_feed_subscriptions` endpoints.

.. attribute:: typepad.Application.external_feed_subscriptions

   A list of `ExternalFeedSubscription` instances representing the `Application` instance's subscriptions.

These subscriptions can be modified in the same ways as `Group` subscriptions, described above.

.. _TypePad endpoint documentation: http://www.typepad.com/services/apidocs/endpoints/applications/%253Cid%253E/create-external-feed-subscription
