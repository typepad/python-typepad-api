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

For these basic requests we're going to do, we'll need to disable the library's batch request feature. Do this by also entering:

   >>> typepad.TypePadObject.batch_requests = False
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
   >>> event.object.title
   'Hallo'
   >>>

Working with blogs
==================

TypePad is mostly about blogs, so let's see what we can do with them.

Listing a user's blogs
----------------------

You can also *list what blogs a user has*. (Without authentication, you'll only see the account's public, shared blogs, but that's okay for now.)

::

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
   >>> 

Once we have the blog, we can *list what posts are available* in that blog::

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

