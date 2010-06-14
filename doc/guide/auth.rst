=============================
Making authenticated requests
=============================

So far, we've only made *unauthenticated* requests. As you can only read public content with unauthenticated requests, to build a more complex application you'll have to make *authenticated* requests. Let's look at how to do that.


Joining a TypePad application
=============================

The TypePad API thinks of different API clients as *applications*. When you build a web site or client program that uses TypePad resources, your program will identify itself to TypePad as an application. Other TypePad members can then *allow* your application to see and act on their TypePad content.

Registering a TypePad application
---------------------------------

All authentication tokens in TypePad belong to applications, so first you'll need to register an application. You can do this in TypePad by going to `the Account → Developer page`_ and clicking the "API: Apply Here" button. As we'll be working with blogs, pick "Application (desktop, mobile, web)" for your application type. (The "Community" option is for community applications like Motion that use groups instead of blogs.)

.. _the Account → Developer page: http://www.typepad.com/account/access/developer

Once you've registered your TypePad application, click "View & Edit Details" in the application list. Here, under "API Key," you'll find the *consumer token* and an *anonymous access token* for your application. These are OAuth tokens, so each of these tokens have a *key* part and a *secret* part. We'll use these tokens with the OAuth library to make requests for your application. Let's make an `OAuthConsumer` instance with your application's consumer token (that is, the "Consumer Key" and "Consumer Secret" parts of the "API Key")::

   >>> from oauth.oauth import OAuthConsumer
   >>> consumer = OAuthConsumer('b658d74d5ef8653b', 'fHHGZ1iI')
   >>> consumer.key, consumer.secret
   ('b658d74d5ef8653b', 'fHHGZ1iI')
   >>>

Finding your application
------------------------

Now that you have an application, you can ask the API about it. In your application's details, just above the "API Key" is a field labeled "Application XID." This is your application's URL identifier. Back in the Python shell, use that URL identifier to load the `Application` object::

   >>> app = typepad.Application.get_by_id('6p0120a96c7944970b')
   >>> app.name
   'My Test App'
   >>>

Joining your application
------------------------

So that you can experiment with authenticated requests, we'll use the `interactive_authorize()` method of `typepad.client` to join your application. OAuth can seem complicated, but you can use this special interactive flow right in the Python shell so you can get right back to making requests. (It uses the *out of band* authentication mode, so if you're making a mobile app or some other sort of app that isn't a web site, this will look a lot like when your users sign in to your app too.)

::

   >>> access_token = typepad.client.interactive_authorize(consumer, app)

   To join your application 'my test app', follow this link and click "Allow":

   <https://www.typepad.com/secure/services/api/6p0120a96c7944970b/oauth-approve?oauth_token=df67...1c75>

   Enter the verifier code TypePad gave you: 

Open the link in your browser. If you're already signed in to TypePad, you'll see the "Allow" button immediately; otherwise you'll have to sign in first. Click "Allow," and TypePad will give you back the verifier code to let you approve the application.

::

   Enter the verifier code TypePad gave you: 74790350

   Yay! This new access token authorizes this typepad.client to act as markpasc (6p00d83451ce6b69e2). Here's the token:

       Key:    BOGYsZiz2IB0kDzX
       Secret: RgNYgELkbPaMsKkw

   Pass this access token to typepad.client.add_credentials() to re-authorize as markpasc later.

   >>> access_token.key, access_token.secret
   ('BOGYsZiz2IB0kDzX', 'RgNYgELkbPaMsKkw')
   >>>

The `interactive_authorize()` method already configured the `typepad.client` with this key, though, so you can immediately make authorized requests as that TypePad user.


Making some requests
====================

Now that you've set up your `typepad.client` with your access token, you're all ready to make some requests! Have fun!
