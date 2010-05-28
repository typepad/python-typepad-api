==============================
Getting started with `typepad`
==============================

Let's look at some examples to see what you can do with the `typepad` library and the TypePad API.


Setting up the `typepad` library
================================

First, if you'd like to follow along in your Python shell, you can install the `typepad` library with ``pip`` or ``easy_install`` (you need only use one)::

   $ pip install typepad
   $ easy_install typepad

Then you can start the Python shell and make `typepad` available by importing it::

   $ python
   Python 2.6.1 (r261:67515, Feb 11 2010, 00:51:29) 
   [GCC 4.2.1 (Apple Inc. build 5646)] on darwin
   Type "help", "copyright", "credits" or "license" for more information.
   >>> import typepad
   >>>

Now we're ready to try some requests.


Looking at users
================

When making requests for users, you'll need to know an *identifier* for the user account you want to know about. Usually this is the *URL identifier*, the account name that starts with ``6p``. For users, though, you can also use the *preferred username* they've set in TypePad. This is the part you can enter in the "Profile URL" section when `editing your profile`_.

.. _editing your profile: http://www.typepad.com/profile/edit

Retrieving a user's profile
---------------------------

Once you have an URL identifier or preferred username, you can **get a user object** this way::

   >>> user = typepad.User.get_by_url_id('markpasc')
   >>> user.display_name
   'markpasc'
   >>>

Retrieving a user's profile events
----------------------------------

In addition to the `User` object data, you can request several property endpoints for that user directly from the object. Here, let's **get that user's events**, the things they did on TypePad recently that shows on their profile::

   >>> events = user.events
   >>> len(events)
   50
   >>> event = events[0]
   >>> event.verb
   'AddedFavorite'
   >>> str(event.published)
   '2010-05-27 20:00:21'
   >>> event.object.title
   'A face'
   >>>

As you can see, this set of ``user.events`` has 50 items in it. However, the user's events endpoint actually has many more::

   >>> events.estimated_total_results
   832
   >>>

Many endpoints are *stream* endpoints, meaning they only return some results in each request. As long as there are some, we can **get the next set of results**::

   >>> more_events = events.next()
   >>> len(more_events)
   50
   >>> event = more_events[0]
   >>> event.verb
   'NewAsset'
   >>> str(event.published)
   '2010-05-10 17:31:16'
   >>> event.object.title
   'A new Super Mario Bros.'
   >>>


Working with blogs
==================

TypePad is mostly about blogs, so let's see what we can do with them.

Listing a user's blogs
----------------------

You can also **list what blogs a user has**. (Without authentication, you'll only see the account's public, shared blogs, but that's okay for now.)

::

   >>> user = typepad.User.get_by_url_id('markpasc')
   >>> blogs = user.blogs
   >>> len(blogs)
   3
   >>> [blog.title for blog in blogs]
   ['markpasc', 'Advent Calendar of 2009 Advent Calendars 2009', 'Best Endtimes Ever']
   >>>

Seeing the posts in a blog
--------------------------

Let's pick one blog to look at::

   >>> blog = blogs[0]
   >>> blog.title
   'markpasc'
   >>> blog.home_url
   'http://markpasc.typepad.com/blog/'
   >>>

Once we have the blog, we can **list what posts are available** in that blog::

   >>> posts = blog.post_assets
   >>> len(posts)
   50
   >>> post = posts[0]
   >>> post.title
   'Bicycle rush hour'
   >>> post.permalink_url
   'http://markpasc.typepad.com/blog/2010/05/bicycle-rush-hour.html'
   >>> post.published
   datetime.datetime(2010, 5, 15, 21, 51, 26)
   >>>


Further work
============

These simple requests should you give you a bit of a feel for the TypePad API. When you're ready to move on, try:

* :doc:`ref/api/index`
* `The TypePad API reference documentation`_
* `Help from developer.typepad.com`_

.. _The TypePad API reference documentation: http://www.typepad.com/services/apidocs
.. _Help from developer.typepad.com: http://developer.typepad.com/help/
