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

    # TODO
    # - featured members (i don't think we have filters for them yet)
    #   - that we cannot block a featured member
    # - test for failure of post by non-member / blocked user
    # - asset deletion failure by a non-creator, non-admin user
    # - comment deletion failure by non-commenter user

Input test data should have this form:

    testdata = {
        'configuration': {
            'backend_url': '...',
            'oauth_consumer_key': '...',
            'oauth_consumer_secret': '...',
            'cookies': { 'cookie_name': 'value' }
        },
        'admin': {
            'xid': '...',
            'oauth_key': '...',
            'oauth_secret': '...'
        },
        'member': {
            'xid': '...',
            'oauth_key': '...',
            'oauth_secret': '...'
        },
        'blocked': {
            'xid': '...',
            'oauth_key': '...',
            'oauth_secret': '...',
        },
        'featured': {
            'xid': '...',
            'oauth_key': '...',
            'oauth_secret': '...',
        },
        'group': {
            'xid': '...',
            'name': '...'
            'oauth_key': '...',
            'oauth_secret': '...'
        }
    }

    the member should follow admin
    the admin should follow member

    the member should have 2 or more elsewhere accounts

    'blocked' identifies a member who will become blocked by the
    test suite

Numbering prefix scheme for tests.
Some tests should be run in a specific order. The only way to do this
is through the test method name, as tests are run in alphabetic order.

    0 - POSTs for setting up data for tests

    1 - GET requests, relying on test data as described above.

    2 - Relationship test to unblock the blocked member
    3 - Test to (re-)block the user who was blocked to begin with

    4 - PUT requests

    5 - POST requests for parent objects (assets)
    6 - POST requests for child objects (favorites, comments)

    6z - HEAD, OPTIONS requests made after POSTs but before DELETEs

    7 - DELETE requests for child objects (favorites, comments)
    8 - DELETE requests for top-level objects (assets)

    9 - DELETE for remaining assets (final cleanup)

"""


import base64
import cgi
from copy import deepcopy
from datetime import datetime
import httplib
import os
from pprint import pprint
import re
from StringIO import StringIO
import time
import unittest
from urllib import urlencode, unquote
from urlparse import urlsplit, urlunsplit, urlparse

import httplib2
import nose
import nose.plugins.attrib
import nose.tools
from oauth import oauth
from remoteobjects.http import HttpObject
import simplejson as json

import typepad


TEST_IMAGE_CONTENT = "\n".join(
    """iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAAAqUlEQVRIx8XTsQ2AIBCFYcM+OoOV"""
    """lQu4gxM4jQswAyUrsAI1A6BXaKIiiLkHxSV0338EGu99U2nEPn1NvK0VcOI1Ai546YAHXjIgiJcK"""
    """eMVLBERxdEASRwYQ3qVwVMBnHBEQxK21ozFmQge8bq61nqWUKzIgiDvnBtpcKbVQAJ3vNwHdnDCC"""
    """78MZEH1w6Bv4/NoRbyDrq3F/Qzb8TwArnhvAjucECG74mA3T52uZi1CUIgAAAABJRU5ErkJggg=="""
)



def load_test_data():
    filename = os.getenv('TEST_TYPEPAD_JSON', os.getenv('TEST_TYPEPAD'))
    if not filename:
        raise nose.SkipTest('no TypePad tests without TEST_TYPEPAD_JSON')

    f = open(filename, 'r')
    s = f.read()
    f.close()
    return json.loads(s)


def setUpModule():
    global testdata
    testdata = load_test_data()

    if 'configuration' not in testdata:
        raise ValueError('cannot run tests without configuration in test data')

    typepad.client.endpoint = testdata['configuration']['backend_url']
    testdata['assets'] = []
    testdata['assets_created'] = []
    testdata['comments_created'] = []

    if 'cookies' in testdata['configuration']:
        typepad.client.cookies.update(testdata['configuration']['cookies'])


def attr(*args, **kwargs):
    """Decorator wrapper for the nose 'attrib' attr decorator.
    
    This attr decorator recognizes the 'user' attribute when assigned and
    calls the `credentials_for` method of the TestTypePad class to apply the
    appropriate OAuth credentials.

    This wrapper also attempts to derive the HTTP method from the docstring of
    the wrapped function and assigns a 'method' attribute if found.
    """
    def wrap(fn):
        user = kwargs.get('user', None)
        if fn.__doc__ is not None:
            m = re.match(r'^(GET|DELETE|PUT|POST|OPTIONS|HEAD) ', fn.__doc__)
            if m is not None:
                verb = m.groups()[0]
                kwargs['method'] = verb

        @nose.tools.make_decorator(fn)
        @nose.plugins.attrib.attr(*args, **kwargs)
        def test_user(self, *args, **kwargs):
            if user is not None:
                self.credentials_for(user)
            try:
                return fn(self, *args, **kwargs)
            finally:
                self.clear_credentials()
        return test_user

    # This is called immediately, so don't need to carry name over.
    return wrap


class TestTypePad(unittest.TestCase):

    """Superclass for live TypePad API integration tests.

    This class provides support for using the `attr()` decorator to pick as
    which test user a test runs.

    """

    def credentials_for(self, ident):
        """Configures the test client to use the credentials keyed on
        ``ident`` in the test data."""
        if ident not in self.testdata:
            raise nose.SkipTest('no credentials for %s tests' % ident)
        consumer = oauth.OAuthConsumer(
            self.testdata['configuration']['oauth_consumer_key'],
            self.testdata['configuration']['oauth_consumer_secret'],
        )
        token = oauth.OAuthToken(
            self.testdata[ident]['oauth_key'],
            self.testdata[ident]['oauth_secret'],
        )
        backend = urlparse(self.testdata['configuration']['backend_url'])
        typepad.client.clear_credentials()
        typepad.client.add_credentials(consumer, token, domain=backend[1])

    def clear_credentials(self):
        """Clears the test client's credentials."""
        typepad.client.clear_credentials()

    def assertForbidden(self, *args, **kwargs):
        self.assertRaises(HttpObject.Forbidden, *args, **kwargs)

    def assertUnauthorized(self, *args, **kwargs):
        self.assertRaises(HttpObject.Unauthorized, *args, **kwargs)

    def assertNotFound(self, *args, **kwargs):
        self.assertRaises(HttpObject.NotFound, *args, **kwargs)

    def assertRequestError(self, *args, **kwargs):
        self.assertRaises(HttpObject.RequestError, *args, **kwargs)

    @classmethod
    def setUpClass(cls):
        global testdata
        cls.testdata = deepcopy(testdata)

    def setUp(self):
        # force this on; other tests may have disabled it
        typepad.TypePadObject.batch_requests = True


class TestGroup(TestTypePad):

    @attr(user='member')
    def test_0_setup_test_data(self):
        """Sets up some test data for our group."""

        group_id = self.testdata['group']['xid']
        member_id = self.testdata['member']['xid']

        post1 = self.post_asset()
        post1.content = "This post is needed to test list operations."
        typepad.Group.get_by_url_id(group_id).post_assets.post(post1)
        self.assertValidAsset(post1)

        self.testdata['assets_created'].append(post1.url_id)

        # lets pause to reflect (and allow timestamps between these assets to differ)
        time.sleep(2)

        post2 = self.post_asset()
        post2.content = "This post will be favorited and commented on."
        typepad.Group.get_by_url_id(group_id).post_assets.post(post2)
        self.assertValidAsset(post2)

        self.testdata['assets_created'].append(post2.url_id)

        # the older post should be favorited

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        typepad.client.complete_batch()

        fav = typepad.Favorite()
        fav.in_reply_to = post1.asset_ref
        user.favorites.post(fav)

        self.assertValidFavorite(fav)

        # the older post should have 2 comments

        content = (
            """Lorem ipsum dolor sit amet, consectetur adipisicing elit, """
            """sed do eiusmod tempor incididunt ut labore et dolore magna """
            """aliqua. Ut enim ad minim veniam, quis nostrud exercitation """
            """ullamco laboris nisi ut aliquip ex ea commodo consequat. """
            """Duis aute irure dolor in reprehenderit in voluptate velit """
            """esse cillum dolore eu fugiat nulla pariatur. Excepteur """
            """sint occaecat cupidatat non proident, sunt in culpa qui """
            """officia deserunt mollit anim id est laborum."""
        )

        comment1 = typepad.Comment()
        comment1.title = ''
        comment1.content = content
        post1.comments.post(comment1)

        # validate comment asset now that it's been posted
        self.assertValidAsset(comment1)
        self.assertEquals(comment1.in_reply_to.url_id, post1.url_id)
        self.assertEquals(comment1.content, content)

        self.testdata['comments_created'].append(comment1.url_id)

        content = 'Yeah, what he said.'

        comment2 = typepad.Comment()
        comment2.title = ''
        comment2.content = content
        post1.comments.post(comment2)

        self.assertValidAsset(comment2)
        self.assertEquals(comment2.in_reply_to.url_id, post1.url_id)

        self.testdata['comments_created'].append(comment2.url_id)

        # now, load testdata['assets'] with these test assets
        self.load_test_assets()

    @attr(user='group')
    def test_1_GET_api_key_key(self):
        """GET /api-keys/<key>.json (group)

        Tests that the /api-keys endpoint really returns the
        configured API key, with its associated Application.

        """
        key = self.testdata['configuration']['oauth_consumer_key']

        typepad.client.batch_request()
        key_obj = typepad.ApiKey.get_by_api_key(key)
        typepad.client.complete_batch()

        self.assert_(isinstance(key_obj, typepad.ApiKey))
        self.assertEquals(key_obj.api_key, key)
        self.assert_(isinstance(key_obj.owner, typepad.Application))

    @attr(user='group')
    def test_1_GET_auth_token_key_token(self):
        """GET /auth-tokens/<key>:<token>.json (group)

        Tests that the /auth-tokens endpoint really returns the
        configured anonymous AuthToken, with its related Group.

        """
        key = self.testdata['configuration']['oauth_consumer_key']
        token = self.testdata['group']['oauth_key']

        typepad.client.batch_request()
        token_obj = typepad.AuthToken.get_by_key_and_token(key, token)
        typepad.client.complete_batch()

        self.assert_(isinstance(token_obj, typepad.AuthToken))
        self.assertEquals(token_obj.auth_token, token)
        self.assert_(isinstance(token_obj.target, typepad.Group))

    @attr(user='group')
    def test_1_GET_assets_id(self):
        """GET /assets/<id>.json (group)
        
        Tests the /assets endpoint using the first 18 assets found in the
        group event stream (loaded during the test setup method).
        """

        self.assert_(len(self.testdata['assets']) >= 2,
            'Must have 2 or more assets to test')

        member_id = self.testdata['member']['xid']
        group_id = self.testdata['group']['xid']
        assets = []

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        # '18' because the batch processor is limited to 20 subrequests.
        for asset_id in self.testdata['assets'][:18]:
            assets.append(typepad.Asset.get_by_url_id(asset_id))
        user = typepad.User.get_by_url_id(member_id)
        typepad.client.complete_batch()

        self.assertValidGroup(group)
        self.assertValidUser(user)

        for asset in assets:
            self.assert_(group.id in asset.groups)
            self.assertValidAsset(asset)

    @attr(user='group')
    def test_1_GET_assets_id__invalid(self):
        """GET /assets/invalid.json (group)
        
        Tests the /assets endpoint using an invalid asset id. This should
        result in a 404 error.
        """

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id('invalid')
        self.assertNotFound(typepad.client.complete_batch)

    @attr(user='group')
    def test_8a_OPTIONS_assets_id__post__by_group(self):
        """OPTIONS /assets/<id>.json (group)

        Tests OPTIONS of an asset using group credentials.
        """

        self.assert_(len(self.testdata['assets_created']))

        asset_id = self.testdata['assets_created'][0]

        typepad.client.batch_request()
        opt = typepad.Asset.get_by_url_id(asset_id).options()
        typepad.client.complete_batch()

        self.assert_(not opt.can_delete(), "group should NOT be able to delete")

    @attr(user='group')
    def test_8a_OPTIONS_assets_id__comment__by_group(self):
        """OPTIONS /assets/<id>.json (group)

        Tests OPTIONS of a comment using group credentials.
        """

        self.assert_(len(self.testdata['comments_created']))

        asset_id = self.testdata['comments_created'][0]

        typepad.client.batch_request()
        opt = typepad.Asset.get_by_url_id(asset_id).options()
        typepad.client.complete_batch()

        self.assert_(not opt.can_delete(), "group should NOT be able to delete comment")

    @attr(user='group')
    def test_8_DELETE_assets_id__by_group(self):
        """DELETE /assets/<id>.json (group)

        Tests deletion of an asset using group credentials. This should result
        in a 403 error (FORBIDDEN).
        """

        self.assert_(len(self.testdata['assets_created']))

        asset_id = self.testdata['assets_created'][0]

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        typepad.client.complete_batch()

        self.assertValidAsset(asset)
        self.assertForbidden(asset.delete)

    @attr(user='group')
    def test_8_DELETE_assets_id__comment__by_group(self):
        """DELETE /assets/<id>.json (comment asset; group)

        Tests deletion of a comment using group credentials. This should
        result in a 403 error (FORBIDDEN).
        """

        self.assert_(len(self.testdata['comments_created']))

        asset_id = self.testdata['comments_created'][0]

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        typepad.client.complete_batch()

        self.assertValidAsset(asset)
        self.assertForbidden(asset.delete)

    @attr(user='admin')
    def test_8a_OPTIONS_assets_id__post__by_admin(self):
        """OPTIONS /assets/<id>.json (admin)

        Tests OPTIONS of an asset using admin credentials.
        """

        self.assert_(len(self.testdata['assets_created']))

        asset_id = self.testdata['assets_created'][0]

        typepad.client.batch_request()
        opt = typepad.Asset.get_by_url_id(asset_id).options()
        typepad.client.complete_batch()

        self.assert_(opt.can_delete(), "admin should be able to delete")

    @attr(user='admin')
    def test_8a_OPTIONS_assets_id__comment__by_admin(self):
        """OPTIONS /assets/<id>.json (admin)

        Tests OPTIONS of an comment using admin credentials.
        """

        self.assert_(len(self.testdata['comments_created']))

        asset_id = self.testdata['comments_created'][0]

        typepad.client.batch_request()
        opt = typepad.Asset.get_by_url_id(asset_id).options()
        typepad.client.complete_batch()

        self.assert_(opt.can_delete(), "admin should be able to delete comment")

    @attr(user='admin')
    def test_8_DELETE_assets_id__by_admin(self):
        """DELETE /assets/<id>.json (admin)

        Tests deletion of an asset using admin credentials.
        """

        self.assert_(len(self.testdata['assets_created']))

        asset_id = self.testdata['assets_created'].pop()

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        typepad.client.complete_batch()

        self.assertValidAsset(asset)
        asset.delete()

        # now, see if we can select it. hopefully this fails.
        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        self.assertNotFound(typepad.client.complete_batch)

    @attr(user='admin')
    def test_8_DELETE_assets_id__comment__by_admin(self):
        """DELETE /assets/<id>.json (comment asset; admin)

        Tests deletion of a comment using admin credentials.
        """

        self.assert_(len(self.testdata['comments_created']))

        asset_id = self.testdata['comments_created'].pop()

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        typepad.client.complete_batch()

        self.assertValidAsset(asset)
        asset.delete()

        # now, see if we can select it. hopefully this fails.
        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        self.assertNotFound(typepad.client.complete_batch)

    @attr(user='member')
    def test_6z_OPTIONS_assets_id__post__by_member(self):
        """OPTIONS /assets/<id>.json (member)

        Tests OPTIONS of an asset using member credentials.
        """

        self.assert_(len(self.testdata['assets_created']))

        asset_id = self.testdata['assets_created'][0]

        typepad.client.batch_request()
        opt = typepad.Asset.get_by_url_id(asset_id).options()
        typepad.client.complete_batch()

        self.assert_(opt.can_delete(), "member should be able to delete")

    @attr(user='member')
    def test_6z_OPTIONS_assets_id__comment__by_member(self):
        """OPTIONS /assets/<id>.json (member)

        Tests OPTIONS of an asset using member credentials.
        """

        self.assert_(len(self.testdata['comments_created']))

        asset_id = self.testdata['comments_created'][0]

        typepad.client.batch_request()
        opt = typepad.Asset.get_by_url_id(asset_id).options()
        typepad.client.complete_batch()

        self.assert_(opt.can_delete(), "member should be able to delete comment")

    @attr(user='member')
    def test_9_DELETE_assets_id__post__by_member(self):
        """DELETE /assets/<id>.json (member)

        Tests deletion of an asset using member credentials.
        """

        self.assert_(len(self.testdata['assets_created']))

        for asset_id in self.testdata['assets_created']:
            typepad.client.batch_request()
            asset = typepad.Asset.get_by_url_id(asset_id)
            typepad.client.complete_batch()

            self.assertValidAsset(asset)
            asset.delete()

            # now, see if we can select it. hopefully this fails.
            typepad.client.batch_request()
            asset = typepad.Asset.get_by_url_id(asset_id)
            self.assertNotFound(typepad.client.complete_batch)

        self.testdata['assets_created'] = []

    @attr(user='member')
    def test_9_DELETE_assets_id__comment__by_member(self):
        """DELETE /assets/<id>.json (comment asset; member)

        Tests deletion of a comment using member credentials.
        """

        self.assert_(len(self.testdata['comments_created']))

        for asset_id in self.testdata['comments_created']:
            typepad.client.batch_request()
            asset = typepad.Asset.get_by_url_id(asset_id)
            typepad.client.complete_batch()

            self.assertValidAsset(asset)
            asset.delete()

            # now, see if we can select it. hopefully this fails.
            typepad.client.batch_request()
            asset = typepad.Asset.get_by_url_id(asset_id)
            self.assertNotFound(typepad.client.complete_batch)

        self.testdata['comments_created'] = []

    # @attr(user='group')
    # def test_4_PUT_assets_id__by_group(self):
    #     """PUT /assets/<id>.json (group)
    #     
    #     Tests updating an asset using group's credentials. This should
    #     result in a 403 error (FORBIDDEN).
    #     """
    # 
    #     asset_id = self.testdata['assets'][0]
    # 
    #     typepad.client.batch_request()
    #     asset = typepad.Asset.get_by_url_id(asset_id)
    #     typepad.client.complete_batch()
    # 
    #     self.assertValidAsset(asset)
    # 
    #     # Lets change this asset and put it back and see what happens
    #     orig_title = asset.title
    #     asset.title = 'Changed by test suite by group'
    #     # FIXME: https://intranet.sixapart.com/bugs/default.asp?87859
    #     # self.assertForbidden(asset.put)
    #     try:
    #         asset.put()
    #         self.fail('group credentials allowed an update to an asset')
    #     except:
    #         pass
    # 
    #     # Re-select this asset to verify it has not been updated.
    # 
    #     typepad.client.batch_request()
    #     asset2 = typepad.Asset.get_by_url_id(asset_id)
    #     typepad.client.complete_batch()
    # 
    #     self.assertValidAsset(asset2)
    # 
    #     self.assertEquals(asset2.title, orig_title)
    # 
    # @attr(user='member')
    # def test_4_PUT_assets_id__by_member(self):
    #     """PUT /assets/<id>.json (member)
    # 
    #     Tests updating an asset using member credentials.
    #     """
    # 
    #     raise nose.SkipTest(
    #         'FIXME: https://intranet.sixapart.com/bugs/default.asp?87900')
    # 
    #     asset_id = self.testdata['assets'][0]
    # 
    #     typepad.client.batch_request()
    #     asset = typepad.Asset.get_by_url_id(asset_id)
    #     typepad.client.complete_batch()
    # 
    #     self.assertValidAsset(asset)
    # 
    #     # Lets change this asset and put it back and see what happens
    #     asset.title = 'Changed by test suite by creator'
    #     asset.put()
    # 
    #     # Re-select this asset to verify it has been updated.
    #     typepad.client.batch_request()
    #     asset2 = typepad.Asset.get_by_url_id(asset_id)
    #     typepad.client.complete_batch()
    # 
    #     self.assertValidAsset(asset2)
    # 
    #     self.assertEquals(asset2.title, 'Changed by test suite by creator')
    # 
    #     asset.title = ''
    #     asset.put()
    # 
    # @attr(user='admin')
    # def test_4_PUT_assets_id__by_admin(self):
    #     """PUT /assets/<id>.json (admin)
    #     
    #     Tests updating an asset using admin credentials.
    #     """
    # 
    #     raise nose.SkipTest(
    #         'FIXME: https://intranet.sixapart.com/bugs/default.asp?87900')
    # 
    #     asset_id = self.testdata['assets'][0]
    # 
    #     typepad.client.batch_request()
    #     asset = typepad.Asset.get_by_url_id(asset_id)
    #     typepad.client.complete_batch()
    # 
    #     self.assertValidAsset(asset)
    # 
    #     # Lets change this asset and put it back and see what happens
    #     asset.title = 'Changed by test suite by admin'
    #     asset.put()
    # 
    #     # Re-select this asset to verify it has been updated.
    #     typepad.client.batch_request()
    #     asset2 = typepad.Asset.get_by_url_id(asset_id)
    #     typepad.client.complete_batch()
    # 
    #     self.assertValidAsset(asset2)
    #     self.assertEquals(asset2.title, 'Changed by test suite by admin')
    # 
    #     asset.title = ''
    #     asset.put()

    @attr(user='group')
    def test_1_GET_assets_id_comments(self):
        """GET /assets/<id>/comments.json (group)
        
        Tests selection of comments for a specific asset.
        """

        self.assert_(len(self.testdata['assets']) >= 2,
            'Must have 2 or more assets to test')

        asset_id = self.testdata['assets'][1]

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        listset = self.filterEndpoint(asset.comments)
        typepad.client.complete_batch()

        self.assertValidAsset(asset)
        self.assertValidFilter(listset)

        comments = listset[0]
        for comment in comments:
            self.assertValidAsset(comment)

    @attr(user='member')
    def test_6_POST_assets_id_comments(self):
        """POST /assets/<id>/comments.json (member)
        
        Tests posting a comment to an asset.
        """

        asset_id = self.testdata['assets'][1]

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        typepad.client.complete_batch()

        self.assertValidAsset(asset)

        content = "Hey there, here's a comment."
        comment = typepad.Comment()
        comment.title = ''
        comment.content = content
        asset.comments.post(comment)
        # validate comment asset now that it's been posted
        self.assertValidAsset(comment)
        self.assertEquals(comment.in_reply_to.url_id, asset.url_id)
        self.assertEquals(comment.content, content)

        self.testdata['comments_created'].append(comment.url_id)

    @attr(user='group')
    def test_1_GET_assets_id_favorites(self):
        """GET /assets/<id>/favorites.json (group)
        
        Tests selecting favorites for a specific asset.
        """

        self.assert_(len(self.testdata['assets']) >= 2,
            'Must have 2 or more assets to test')

        asset_id = self.testdata['assets'][1]
        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        asset = typepad.Asset.get_by_url_id(asset_id)
        favs = asset.favorites.filter()
        # FIXME: this requires 2 or more favorites on the top-most asset
        # listset = self.filterEndpoint(asset.favorites)
        typepad.client.complete_batch()

        self.assertValidAsset(asset)
        # self.assertValidFilter(listset)

        # favs = listset[0]
        for fav in favs:
            self.assertValidFavorite(fav)

        self.assertEquals(favs.entries[0].author.url_id, member_id)
        self.assertEquals(favs.entries[0].in_reply_to.url_id, asset_id)

    def test_5_POST_batch_processor(self):
        """POST /batch-processor.json
        """

        raise nose.SkipTest(
            'We test this endpoint through our other tests.')

    def upload_asset(self, ident, data, content):
        """Helper method for posting a file to the TypePad API.

        ident is one of the user identifiers (group, member, admin, blocked)
        content is the base64 encoded file contents to post."""

        self.credentials_for(ident)

        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        typepad.client.complete_batch()

        self.assertValidGroup(group)

        fileobj = StringIO(base64.decodestring(content))

        asset = typepad.Asset.from_dict(data)

        object_type = asset.object_type
        post_type = object_type.lower()

        asset.groups = [ group.id ]
        response, content = typepad.api.browser_upload.upload(
            asset, fileobj, post_type=post_type,
            redirect_to='http://example.com/none')

        self.assert_(response)
        self.assertEquals(response.status, httplib.FOUND)
        self.assert_('location' in response)

        urlparts = urlsplit(response['location'])
        params = cgi.parse_qs(urlparts[3])

        self.assert_('status' in params)

        if ident in ('member', 'admin', 'featured'): # test for a successful upload
            self.assert_('error' not in params)
            self.assert_(int(params['status'][0]) != httplib.BAD_REQUEST, 'returned status is BAD_REQUEST')
            self.assert_('asset_url' in params)
            parts = urlparse(params['asset_url'][0])

            self.credentials_for('group')
            posted_asset = typepad.Asset.get(parts[2], batch=False)

            self.assertValidAsset(posted_asset)

            self.testdata['assets_created'].append(posted_asset.url_id)
        else: # test for a failure
            self.assertEquals(int(params['status'][0]), httplib.FORBIDDEN)

    @attr(user='member')
    def test_5_POST_browser_upload__photo__by_member(self):
        """POST /browser-upload.json (photo; member)
        """

        asset = {
            'content': 'This is a test upload',
            'objectType': 'Photo',
        }
        self.upload_asset('member', asset, TEST_IMAGE_CONTENT)

    @attr(user='member')
    def test_5_POST_browser_upload__audio__by_member(self):
        """POST /browser-upload.json (audio; member)
        """

        asset = {
            'content': 'A small audio post',
            'objectType': 'Audio',
        }
        content = "\n".join(
            """//tQZAAAAAAAf4UAAAgAAA0goAABFVWnQ7kKAAAAADSDAAAAgEAYCAQCAUBAIAYABADkguG8AkDk"""
            """fDIoN1fFnCC3hiIUiHw/hiEUkGrgt+/xNoZFC30R0GKtf8MjCkQ1aGARSQau//C34TaGKQtBD9gs"""
            """iBuL//E2hgEG+h0QWRACggFhIGQIgwFrskkYnP+A4CBhn4GyjgYlABnSABQoWkLQQtFGOFBGQBA4"""
            """6Yt+iBgxLf4fMMaIKjMkcLmIMdIqVTInk1l3////84jMUlGSAP/7QGQAiPJHRcrvAqAIAAANIOAA"""
            """AQeBEymgH5PgAAA0gAAABAAAA/3+sEX+9Wut7erUtfU3umtal9m3qzMxKJsl77/rf39a///MS6gi"""
            """iXwAAyBiYZgdkdQGiyUAMLhRhCUcRiXTXv+nsW38QgAbf/WBl/fed5Rptb7a3MVWOXc70ykQs3mp"""
            """f9f62T////3q7q/FGXmBgIeBdgOXiNbqQ/T1Bbv+nsV/IwAAAAPv/rAw9dt6+dpk//swZAcI8dZF"""
            """SugF5PgAAA0gAAABB4ETK6AGsWAAADSAAAAEX211Szeu3iKBY76J/r9vVP///+u4duR9eAVD5sTh"""
            """mJwSsR/4xSW7D9P/xb+8Acff6gRUR/PcvPU+a7RFTLQNnus2mJa9l7fr////+yRqTI6hGIJiQDJH"""
            """yAwGDhSJHGaZ41qf/ZQWR2ZNAAAAF+/+qCX///3qKDfN//tAZAeI8o5GSmgn5ygAAA0gAAABCXUb"""
            """J6CLnKAAADSAAAAEsq85hVkCaxGSImdmOZWUdDr3mM9f2Rm8/70MY89/vPtSGKKnaQ5qdZUCZx2y"""
            """gJqhgPfemZ3I9SiwTxOFgwU1z//WcAF229oAH///1h0gu4MEYfy5SzWWejulaIN6Oylm6yG/+lDS"""
            """lmeuOEqjVd2WczaIIKBpfc4QQQaHQwCF0lTQw7z/W5TZTEpY8Cv//QoAAAD/+0BkAYryVkXK6CLf"""
            """KAAADSAAAAEI0RcpoI9coAAANIAAAAQb//7IJf///f6OqGjAdJ5azqGeyw8uj0Gv1dqpoVUIU/9N"""
            """XIp0Y+vcN25i9DcAuuyAs4cPKNLSTXJLYcmZ+kBchWBEkOm7/kABtYGv///hnyQRCMcyqSQ6zSZr"""
            """uJ0z2SyL0ENbc2PYy+TPbv/n/bTpM5d/Xd/3OXPrADKzFV28i8CxrCXVeHtIafGVW/+I6gAABv/7"""
            """MGQBiPG2QspoAaN4AAANIAAAAQZZCymgCbHgAAA0gAAABBfv/qwwq+/kiPImEgsdBUEkBPDchpup"""
            """NFFV3c4jU2vq6///6u/+rSRJoAxIHiNX//3U/6QBv//rA1ZNaF+Xq7JdlCq7sqGSqLSToxqtgjnk"""
            """0X16bLVX9tupq//TJAH8Shznq+//+ToADgMD/kL////////QkEISrv/7EGQIj/CGQkuYAT8IAAAN"""
            """IAAAAQAAAaQAAAAgAAA0gAAABExBTUUzLjk4qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"""
            """qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//sQZCIP8AAAaQAAAAgAAA0gAAABAAABpAAA"""
            """ACAAADSAAAAEqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"""
            """qqqqqqqqqqqqqqqqqqqqqqqqqqo="""
        )
        self.upload_asset('member', asset, content)

    @attr(user='group')
    def test_5_POST_browser_upload__photo__by_group(self):
        """POST /browser-upload.json (photo; group)
        """

        asset = {
            'content': 'This is a test upload',
            'objectType': 'Photo',
        }
        content = "\n".join(
            """iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAAAqUlEQVRIx8XTsQ2AIBCFYcM+OoOV"""
            """lQu4gxM4jQswAyUrsAI1A6BXaKIiiLkHxSV0338EGu99U2nEPn1NvK0VcOI1Ai546YAHXjIgiJcK"""
            """eMVLBERxdEASRwYQ3qVwVMBnHBEQxK21ozFmQge8bq61nqWUKzIgiDvnBtpcKbVQAJ3vNwHdnDCC"""
            """78MZEH1w6Bv4/NoRbyDrq3F/Qzb8TwArnhvAjucECG74mA3T52uZi1CUIgAAAABJRU5ErkJggg=="""
        )
        self.upload_asset('group', asset, content)

    @attr(user='group')
    def test_1_GET_events_id(self):
        """GET /events/<id>.json (group)
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?87901')

    @attr(user='group')
    def test_1_GET_favorites_id(self):
        """GET /favorites/<id>.json (group)
        
        Tests selection of a single favorite object.
        """

        self.assert_(len(self.testdata['assets']) >= 2,
            'Must have 2 or more assets to test')

        # asset:user
        member_id = self.testdata['member']['xid']
        asset_id = self.testdata['assets'][1]

        typepad.client.batch_request()
        fav = typepad.Favorite.get_by_user_asset(member_id, asset_id)
        typepad.client.complete_batch()

        self.assertValidFavorite(fav)
        self.assertEquals(fav.in_reply_to.url_id, asset_id)
        self.assertEquals(fav.author.url_id, member_id)

    @attr(user='member')
    def test_6z_HEAD_favorites_id(self):
        """HEAD /favorites/<asset_id>:<user_id>.json (group)
        
        Tests existence of a favorite using group credentials.
        """
        # '6z' will sort this test so it runs prior to the favorite deletion
        # tests.
        self.assert_(len(self.testdata['assets_created']) > 0)

        asset_id = self.testdata['assets_created'][0]
        member_id = self.testdata['member']['xid']
        admin_id = self.testdata['admin']['xid']

        typepad.client.batch_request()
        fav = typepad.Favorite.head_by_user_asset(member_id, asset_id)
        not_fav = typepad.Favorite.head_by_user_asset(admin_id, asset_id)
        typepad.client.complete_batch()

        self.assert_(fav.found(), "asset is not a favorite by member but should be")
        self.assert_(not not_fav.found(), "asset is a favorite of admin but shouldn't be")

    @attr(user='group')
    def test_7_DELETE_favorites_id__by_group(self):
        """DELETE /favorites/<id>.json (group)
        
        Tests deletion of a favorite object using group credentials.
        """

        self.assert_(len(self.testdata['assets_created']))

        member_id = self.testdata['member']['xid']
        asset_id = self.testdata['assets_created'][0]

        self.assertForbidden(
            typepad.Favorite.get_by_user_asset(member_id, asset_id).delete)

    @attr(user='member')
    def test_7_DELETE_favorites_id__by_member(self):
        """DELETE /favorites/<id>.json (member)
        
        Tests deletion of a favorite object using member credentials.
        """

        self.assert_(len(self.testdata['assets_created']))

        member_id = self.testdata['member']['xid']
        asset_id = self.testdata['assets_created'][0]

        typepad.Favorite.get_by_user_asset(member_id, asset_id).delete()

        typepad.client.batch_request()
        fav = typepad.Favorite.get_by_user_asset(member_id, asset_id)
        self.assertNotFound(typepad.client.complete_batch)

    @attr(user='group')
    def test_1_GET_groups_id(self):
        """GET /groups/<id>.json (group)
        
        Tests selection of a group object using group credentials.
        """

        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        typepad.client.complete_batch()

        self.assertValidGroup(group)
        self.assertEquals(group.url_id, group_id)
        self.assertEquals(group.display_name, self.testdata['group']['name'])

    @attr(user='group')
    def test_1_GET_groups_id_events(self):
        """GET /groups/<id>/events.json (group)
        
        Tests endpoint for selecting the group event stream.
        """

        self.assert_(len(self.testdata['assets']) >= 2,
            'Must have 2 or more assets to test')

        group_id = self.testdata['group']['xid']
        member_id = self.testdata['member']['xid']
        asset_id = self.testdata['assets'][0]

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        listset = self.filterEndpoint(group.events)
        typepad.client.complete_batch()

        self.assertValidGroup(group)
        self.assertEquals(group.url_id, group_id)
        self.assertValidFilter(listset)

        # FIXME: https://intranet.sixapart.com/bugs/default.asp?87911
        # FIXME: https://intranet.sixapart.com/bugs/default.asp?88008
        events = [x for x in listset[0] if x.object and len(x.object.groups) > 0]
        for event in events:
            self.assertValidEvent(event)

        self.assertEquals(events[0].actor.url_id, member_id)
        self.assertEquals(events[0].object.url_id, asset_id)
        self.assertEquals(events[0].object.author.url_id, member_id)
        self.assertTrue(events[0].object.groups[0].endswith(group_id))

    @attr(user='member')
    def test_5_POST_groups_id_link_assets(self):
        """POST /groups/<id>/link-assets.json (member)
        
        Tests endpoint for creating a new link asset within the group.
        """

        group_id = self.testdata['group']['xid']

        link = self.link_asset()

        typepad.Group.get_by_url_id(group_id).link_assets.post(link)
        self.assertValidAsset(link)

        self.testdata['assets_created'].append(link.url_id)

    @attr(user='group')
    def test_1_GET_groups_id_memberships(self):
        """GET /groups/<id>/memberships.json (group)
        
        Tests selection of group memberships.
        """

        group_id = self.testdata['group']['xid']
        admin_id = self.testdata['admin']['xid']
        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        everyone = group.memberships.filter()
        typepad.client.complete_batch()

        self.assertValidGroup(group)
        for rel in everyone:
            self.assertValidRelationship(rel)

        self.assert_(len(everyone) > 0, 'memberships should be non-zero')
        self.assert_(admin_id in [a.target.url_id for a in everyone],
            'configured admin should exist in memberships')
        self.assert_(member_id in [a.target.url_id for a in everyone],
            'configured member should exist in memberships')

    @attr(user='group')
    def test_1_GET_groups_id_memberships_admin(self):
        """GET /groups/<id>/memberships/@admin.json (group)
        
        Tests selection of group administrator memberships.
        """

        group_id = self.testdata['group']['xid']
        admin_id = self.testdata['admin']['xid']

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        admins = group.memberships.filter(admin=True)
        everyone = group.memberships.filter()
        typepad.client.complete_batch()

        self.assertValidGroup(group)
        for rel in admins:
            self.assertValidRelationship(rel)
        for rel in everyone:
            self.assertValidRelationship(rel)

        # yes, we have one or more admins!
        self.assert_(len(admins) > 0, 'admin membership should be non-zero')
        self.assert_(admin_id in [a.target.url_id for a in admins],
            'configured admin should exist in admin memberships')

        self.assertNotEqual(admins.total_results, everyone.total_results,
            'Filtered member list size should be less than unfiltered list: %d != %d' %
            ( admins.total_results, everyone.total_results ))

    @attr(user='group')
    def test_1_GET_groups_id_memberships_member(self):
        """GET /groups/<id>/memberships/@member.json (group)
        
        Tests selection of a group member relationships.
        """

        group_id = self.testdata['group']['xid']
        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        listset = self.filterEndpoint(group.memberships, member=True)
        typepad.client.complete_batch()

        self.assertValidGroup(group)
        self.assertValidFilter(listset)

        members = listset[0]
        for member in members:
            self.assertValidRelationship(member)

        self.assert_(member_id in [a.target.url_id for a in members],
            'configured admin should exist in admin memberships')

    @attr(user='group')
    def test_1_GET_groups_id_notifications(self):
        """GET /groups/<id>/notifications.json (group)
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?87903')

    @attr(user='member')
    def test_5_POST_groups_id_photo_assets(self):
        """POST /groups/<id>/photo-assets.json (member)
        
        Tests posting a photo asset.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?87928')

    @attr(user='member')
    def test_5_POST_groups_id_audio_assets(self):
        """POST /groups/<id>/audio-assets.json (member)
        
        Tests posting an audio asset.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?87928')

    @attr(user='member')
    def test_5_POST_groups_id_post_assets__by_member(self):
        """POST /groups/<id>/post-assets.json (member)
        
        Tests posting a text post asset using member credentials.
        """

        group_id = self.testdata['group']['xid']

        post = self.post_asset()

        typepad.Group.get_by_url_id(group_id).post_assets.post(post)
        self.assertValidAsset(post)

        self.testdata['assets_created'].append(post.url_id)

    @attr(user='group')
    def test_5_POST_groups_id_post_assets__by_group(self):
        """POST /groups/<id>/post-assets.json (group)

        Tests posting a text post asset using group credentials.
        """

        group_id = self.testdata['group']['xid']

        post = self.post_asset()
        post.content = 'Test post asset by group'

        self.assertForbidden(
            typepad.Group.get_by_url_id(group_id).post_assets.post, post)

    @attr(user='blocked')
    def test_5_POST_groups_id_post_assets__by_blocked(self):
        """POST /groups/<id>/post-assets.json (blocked)
        
        Tests posting a text post asset using a blocked user's credentials.
        """

        group_id = self.testdata['group']['xid']

        post = self.post_asset()
        post.content = 'Test post asset by blocked user'

        self.assertForbidden(
            typepad.Group.get_by_url_id(group_id).post_assets.post, post)

    @attr(user='member')
    def test_5_POST_groups_id_video_assets(self):
        """POST /groups/<id>/video-assets.json
        
        Tests posting a video asset using member credentials.
        """

        group_id = self.testdata['group']['xid']

        video = self.video_asset()

        typepad.Group.get_by_url_id(group_id).video_assets.post(video)
        self.assertValidAsset(video)

        self.testdata['assets_created'].append(video.url_id)

    @attr(user='group')
    def test_5_POST_groups_id_video_assets__by_group(self):
        """POST /groups/<id>/video-assets.json

        Tests posting a video asset using group credentials.
        """

        group_id = self.testdata['group']['xid']

        video = self.video_asset()
        video.content = 'Test video post by group'

        self.assertForbidden(
            typepad.Group.get_by_url_id(group_id).video_assets.post, video)

    @attr(user='blocked')
    def test_5_POST_groups_id_video_assets__by_blocked(self):
        """POST /groups/<id>/video-assets.json (blocked)

        Tests posting a video asset using a blocked user's credentials.
        """

        group_id = self.testdata['group']['xid']
        video = self.video_asset()

        self.assertForbidden(
            typepad.Group.get_by_url_id(group_id).video_assets.post, video)

    @attr(user='group')
    def test_1_GET_relationships_id(self):
        """GET /relationships/<id>.json (group)
        
        Tests the selection of a single relationship object.
        """

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        followers = user.relationships.filter(follower=True, max_results=1)
        typepad.client.complete_batch()

        self.assertValidUser(user)

        rel = followers[0]
        self.assertValidRelationship(rel)

        rel_link = rel.make_self_link()

        typepad.client.batch_request()
        rel2 = typepad.Relationship.get(rel_link)
        typepad.client.complete_batch()

        self.assertValidRelationship(rel2)

    @attr(user='group')
    def test_1_GET_relationship_id_status(self):
        """GET /relationships/<id>/status.json (group)
        
        Tests the selection of a relationship's status.
        """

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        followers = user.relationships.filter(follower=True, max_results=1)
        typepad.client.complete_batch()

        self.assertValidUser(user)

        rel = followers[0]
        self.assertValidRelationship(rel)

        typepad.client.batch_request()
        try:
            status = rel.status_obj
        finally:
            typepad.client.complete_batch()

        self.assertValidRelationshipStatus(status)

    def update_relationship(self, ident, action):
        """Updates the group relationship of a particular user."""

        if not ident in self.testdata:
            raise nose.SkipTest("missing configuration for %s user" % ident)

        group_id = self.testdata['group']['xid']
        user_id = self.testdata[ident]['xid']

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(group_id)
        typepad.client.complete_batch()

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(user_id)
        memberships = user.memberships.filter(by_group=group)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assert_(len(memberships) == 1)
        self.assertValidRelationship(memberships[0])
        self.assertEquals(memberships[0].source.url_id, group_id)

        if action == 'block':
            self.assert_(not memberships[0].is_blocked())
            memberships[0].block()
        elif action == 'unblock':
            self.assert_(memberships[0].is_blocked())
            status = typepad.RelationshipStatus.get(memberships[0].status_obj._location, batch=False)
            status.types = ["tag:api.typepad.com,2009:Member"]
            status.put()

        typepad.client.batch_request()
        new_membership = user.memberships.filter(by_group=group)
        typepad.client.complete_batch()

        self.assert_(len(new_mebership) == 1)
        self.assertValidRelationship(new_membership[0])

        # confirm relationship now reflects status we expect
        if action == 'block':
            self.assert_(new_membership[0].is_blocked())
            self.assert_(not new_membership[0].is_member())
        elif action == 'unblock':
            self.assert_(not new_membership[0].is_blocked())
            self.assert_(new_membership[0].is_member())

    @attr(user='admin')
    def test_4_PUT_relationships_id_status__block_blocked__by_admin(self):
        """PUT /relationships/<id>/status.json (block; admin)
        
        Tests the endpoint to update a relationship status.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?88982')

        # This endpoint can only be used by an administrator.
        self.update_relationship('blocked', 'block')

    @attr(user='admin')
    def test_3_PUT_relationships_id_status__block_admin__by_admin(self):
        """PUT /relationships/<id>/status.json (block admin; admin)
        
        Tests the endpoint to update a relationship status.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?88982')

        # This request should fail, since we should not be allowed to
        # block ourselves, or other admins.
        self.assertForbidden(self.update_relationship, 'admin', 'block')

    @attr(user='admin')
    def test_3_PUT_relationships_id_status__block_featured__by_admin(self):
        """PUT /relationships/<id>/status.json (block featured; admin)
        
        Tests the endpoint to update a relationship status.
        """

        # This request should fail, since we should not be allowed to
        # block featured users
        self.assertForbidden(self.update_relationship, 'featured', 'block')

    @attr(user='group')
    def test_3_PUT_relationships_id_status__block_blocked__by_group(self):
        """PUT /relationships/<id>/status.json (group)
        """

        # self.assertForbidden(self.update_relationship, 'blocked', 'block')
        try:
            self.update_relationship('blocked', 'block')
            self.fail('group credentials allowed an block to a user')
        except:
            pass

    @attr(user='member')
    def test_3_PUT_relationships_id_status__block_blocked__by_member(self):
        """PUT /relationships/<id>/status.json (member)
        """

        # self.assertForbidden(self.update_relationship, 'blocked', 'block')
        try:
            self.update_relationship('blocked', 'block')
            self.fail('member credentials allowed an block to a user')
        except:
            pass

    @attr(user='admin')
    def test_2_PUT_relationship_id_status__unblock_blocked__by_admin(self):
        """PUT /relationships/<id>/status.json (block; admin)
        
        Tests the endpoint to update a relationship status.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?89008')

        self.update_relationship('blocked', 'unblock')

    @attr(user='group')
    def test_1_GET_users_id(self):
        """GET /users/<id>.json (group)
        
        Tests the selection of a single user object.
        """

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertEquals(user.url_id, member_id)

    @attr(user='group')
    def test_1_GET_users__(self):
        """GET /users/.json (group)
        """

        typepad.client.batch_request()
        try:
            self.assertRaises(ValueError, typepad.User.get_by_url_id, '')
        finally:
            typepad.client.complete_batch()

    @attr(user='group')
    def test_1_GET_users_id_elsewhere_accounts(self):
        """GET /users/<id>/elsewhere-accounts.json (group)
        
        Tests the selection of the elsewhere account for the configured
        member.
        """

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.elsewhere_accounts)
        typepad.client.complete_batch()

        self.assertValidFilter(listset)
        elsewhere = listset[0]

        self.assertValidUser(user)
        self.assert_(elsewhere is not None)
        self.assert_(len(elsewhere) > 0)

    @attr(user='group')
    def test_1_GET_users_id_events(self):
        """GET /users/<id>/events.json (group)
        
        Tests the selection of an event stream for a specific user.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?87756')

    @attr(user='group')
    def test_1_GET_users_id_events_by_group_id(self):
        """GET /users/<id>/events/@by-group/<id>.json (group)
        
        Tests the selection of the group-specific event stream for a specific
        user.
        """

        member_id = self.testdata['member']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.events, by_group=group_id)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        events = listset[0]
        for event in events:
            self.assertValidEvent(event)

        self.assertEquals(events[0].actor.url_id, member_id)
        self.assertEquals(events[0].object.author.url_id, member_id)
        self.assertTrue(events[0].object.groups[0].endswith(group_id))

    @attr(user='member')
    def test_6_POST_users_id_favorites(self):
        """POST /users/<id>/favorites.json (member)
        
        Tests the endpoint for creating a new favorite for a user.
        """

        # we wind up deleting two favorites (one by member, one by admin),
        # so lets make sure we created at least 2
        self.assert_(len(self.testdata['assets_created']) >= 2)

        for asset_id in self.testdata['assets_created']:
            member_id = self.testdata['member']['xid']

            typepad.client.batch_request()
            user = typepad.User.get_by_url_id(member_id)
            asset = typepad.Asset.get_by_url_id(asset_id)
            typepad.client.complete_batch()

            self.assertValidUser(user)
            self.assertValidAsset(asset)

            fav = typepad.Favorite()
            fav.in_reply_to = asset.asset_ref
            user.favorites.post(fav)

            self.assertValidFavorite(fav)

            typepad.client.batch_request()
            fav2 = typepad.Favorite.get_by_user_asset(member_id, asset_id)
            typepad.client.complete_batch()

            self.assertValidFavorite(fav2)

    @attr(user='group')
    def test_6z_GET_users_id_favorites(self):
        """GET /users/<id>/favorites.json (group)
        
        Tests the selection of the favorites for a specific user.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?92991')

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.favorites)
        typepad.client.complete_batch()

        self.assertValidFilter(listset)
        favs = listset[0]
        for fav in favs:
            self.assertValidFavorite(fav)

    @attr(user='group')
    def test_1_GET_users_id_memberships(self):
        """GET /users/<id>/memberships.json (group)
        
        Tests the endpoint for selecting memberships for a specific user.
        """

        member_id = self.testdata['member']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.memberships)
        typepad.client.complete_batch()

        self.assertValidFilter(listset)

        memberships = listset[0]
        self.assert_(group_id in [x.source.url_id for x in memberships])

    @attr(user='group')
    def test_1_GET_users_id_memberships_admin(self):
        """GET /users/<id>/memberships/@admin.json (group)
        
        Tests the endpoint for selecting a user's relationships for groups
        they administer.
        """

        admin_id = self.testdata['admin']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(admin_id)
        listset = self.filterEndpoint(user.memberships, admin=True)
        typepad.client.complete_batch()

        # FIXME: https://intranet.sixapart.com/bugs/default.asp?88434
        # self.assertValidFilter(listset)

        memberships = listset[0]
        self.assert_(group_id in [x.source.url_id for x in memberships])

    @attr(user='group')
    def test_1_GET_users_id_memberships_by_group_id(self):
        """GET /users/<id>/memberships/@by-group/<id>.json (group)

        Tests the endpoint for selecting a group membership for a specific
        user.
        """

        member_id = self.testdata['member']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        memberships = user.memberships.filter()
        # FIXME: can't use this without having 2 or more group memberships
        # listset = self.filterEndpoint(user.memberships,
        #     by_group=group_id)
        typepad.client.complete_batch()

        # self.assertValidFilter(listset)

        # memberships = listset[0]
        self.assert_(member_id in [x.target.url_id for x in memberships])

    @attr(user='group')
    def test_1_GET_users_id_memberships_member(self):
        """GET /users/<id>/memberships/@member.json (group)
        
        Tests the endpoint for selecting a user's relationships for
        groups they are a member of.
        """

        member_id = self.testdata['member']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        memberships = user.memberships.filter(member=True)
        # FIXME: can't use this without having 2 or more member memberships
        # listset = self.filterEndpoint(user.memberships, member=True)
        typepad.client.complete_batch()

        # self.assertValidFilter(listset)

        # memberships = listset[0]
        self.assert_(group_id in [x.source.url_id for x in memberships])

    @attr(user='group')
    def test_1_GET_users_id_notifications(self):
        """GET /users/<id>/notifications.json (group)
        
        Tests the endpoint for gathering a user's notifications.
        """

        raise nose.SkipTest(
            'FIXME: https://intranet.sixapart.com/bugs/default.asp?95720')

        self.assert_(len(self.testdata['assets']) >= 2,
            'Must have 2 or more assets to test')

        admin_id = self.testdata['admin']['xid']
        asset_id = self.testdata['assets'][1]

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(admin_id)
        listset = self.filterEndpoint(user.notifications)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        inbox = listset[0]
        for event in inbox:
            self.assertValidEvent(event)

        self.assert_(asset_id in [x.object.url_id for x in inbox])

    @attr(user='group')
    def test_1_GET_users_id_relationships(self):
        """GET /users/<id>/relationships.json (group)

        Tests the endpoint for selecting all of a user's relationships.
        """

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.relationships)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        contacts = listset[0]
        for contact in contacts:
            self.assertValidRelationship(contact)

        self.assert_(member_id in [x.source.url_id for x in contacts])

    @attr(user='group')
    def test_1_GET_users_id_relationships_by_group_id(self):
        """GET /users/<id>/relationships/@by-group/<id>.json (group)

        Selects user relationships within a specific group.
        """

        member_id = self.testdata['member']['xid']
        admin_id = self.testdata['admin']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.relationships, by_group=group_id)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        contacts = listset[0]
        for contact in contacts:
            self.assertValidRelationship(contact)

        self.assert_(member_id in [x.source.url_id for x in contacts])

    @attr(user='group')
    def test_1_GET_users_id_relationships_follower(self):
        """GET /users/<id>/relationships/@follower.json (group)

        Tests the endpoint for selecting the user's followers.
        """

        member_id = self.testdata['member']['xid']
        admin_id = self.testdata['admin']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.relationships, follower=True)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        contacts = listset[0]
        for contact in contacts:
            self.assertValidRelationship(contact)

        self.assert_(admin_id in [x.source.url_id for x in contacts])
        self.assert_(member_id in [x.target.url_id for x in contacts])

    @attr(user='group')
    def test_1_GET_users_id_relationships_follower_by_group_id(self):
        """GET /users/<id>/relationships/@follower/@by-group/<id>.json (group)

        Tests the endpoint for selecting the user's followers within a group.
        """

        member_id = self.testdata['member']['xid']
        admin_id = self.testdata['admin']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.relationships,
            follower=True, by_group=group_id)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        contacts = listset[0]
        for contact in contacts:
            self.assertValidRelationship(contact)

        self.assert_(admin_id in [x.source.url_id for x in contacts])
        self.assert_(member_id in [x.target.url_id for x in contacts])

    @attr(user='group')
    def test_1_GET_users_id_relationships_following(self):
        """GET /users/<id>/relationships/@following.json (group)
        
        Tests selection of a user's global following list.
        """

        member_id = self.testdata['member']['xid']
        admin_id = self.testdata['admin']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.relationships, following=True)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        contacts = listset[0]
        for contact in contacts:
            self.assertValidRelationship(contact)

        self.assert_(member_id in [x.source.url_id for x in contacts])
        self.assert_(admin_id in [x.target.url_id for x in contacts])

    @attr(user='group')
    def test_1_GET_users_id_relationships_following_by_group_id(self):
        """GET /users/<id>/relationships/@following/@by-group/<id>.json (group)
        
        Tests selection of a user's following list within a group.
        """

        member_id = self.testdata['member']['xid']
        admin_id = self.testdata['admin']['xid']
        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_by_url_id(member_id)
        listset = self.filterEndpoint(user.relationships, following=True,
            by_group=group_id)
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertValidFilter(listset)

        contacts = listset[0]
        for contact in contacts:
            self.assertValidRelationship(contact)

        self.assert_(member_id in [x.source.url_id for x in contacts])
        self.assert_(admin_id in [x.target.url_id for x in contacts])

    @attr(user='member')
    def test_1_GET_users_self__by_member(self):
        """GET /users/@self (member)
        """

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        user = typepad.User.get_self()
        typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertEquals(user.url_id, member_id)

        scheme, netloc, path, query, fragment = urlsplit(user._location)
        self.assertEquals(path, '/users/%s.json' % user.url_id)

    @attr(user='group')
    def test_1_GET_users_id__using_id(self):
        """GET /users/id.json (group)
        """

        member_id = self.testdata['member']['xid']

        typepad.client.batch_request()
        try:
            user = typepad.User.get_by_url_id(member_id)
        finally:
            typepad.client.complete_batch()

        self.assertValidUser(user)
        self.assertEquals(user.url_id, member_id)

    @attr(user='group')
    def test_1_GET_assets_id__using_id(self):
        """GET /assets/id.json (group)
        """

        asset_id = self.testdata['assets'][1]

        typepad.client.batch_request()
        try:
            asset = typepad.Asset.get_by_url_id(asset_id)
        finally:
            typepad.client.complete_batch()

        self.assertValidAsset(asset)
        self.assertEquals(asset.url_id, asset_id)

    @attr(user='group')
    def test_1_GET_groups_id__using_id(self):
        """GET /groups/id.json (group)
        """

        group_id = self.testdata['group']['xid']

        typepad.client.batch_request()
        try:
            group = typepad.Group.get_by_url_id(group_id)
        finally:
            typepad.client.complete_batch()

        self.assertValidGroup(group)
        self.assertEquals(group.url_id, group_id)

    ### Supporting functions for this test suite

    def setUp(self):
        super(TestGroup, self).setUp()

        if not len(self.testdata['assets']):
            self.load_test_assets()

    @attr(user='group')
    def load_test_assets(self):
        """Fetches the event stream for the group and populates the testdata
        dictionary with the assets found."""

        typepad.client.batch_request()
        group = typepad.Group.get_by_url_id(self.testdata['group']['xid'])
        events = group.events.filter()
        typepad.client.complete_batch()

        self.testdata['assets'] = []
        for event in events:
            # FIXME: https://intranet.sixapart.com/bugs/default.asp?88008
            if event.object and len(event.object.groups) > 0:
                self.testdata['assets'].append(event.object.url_id)

    def assertValidAsset(self, asset):
        """Checks given asset for properties that should be present on all assets.
        """

        self.assert_(isinstance(asset, typepad.Asset),
            'object %r is not a typepad.Asset' % asset)
        self.assert_(asset.author)
        self.assertValidUser(asset.author)
        # asset.content is not required for some asset types
        # self.assert_(asset.content)
        self.assert_(asset.text_format)
        self.assert_(asset.text_format in ('text', 'html'))
        # FIXME: https://intranet.sixapart.com/bugs/default.asp?88008
        # self.assert_(len(asset.groups) > 0)
        self.assert_(asset.id)
        self.assert_(asset.url_id)
        self.assert_(len(asset.object_types) > 0)
        self.assert_(asset.object_type)
        self.assert_(asset.published)

        self.assert_(asset.make_self_link())
        self.assert_(asset.favorite_count is not None)
        self.assert_(asset.comment_count is not None)
        # TODO: alternate was optional before, so maybe permalink_url might be None sometimes?
        self.assert_(asset.permalink_url is not None)

        object_type = asset.object_type
        self.assertValidAssetRef(asset.asset_ref)
        if object_type == 'Link':
            # additional properties we expect for link assets
            self.assert_(asset.target_url is not None)
        elif object_type == 'Photo':
            # additional properties we expect for photo assets
            self.assert_(asset.image_link is not None)
            self.assert_(asset.image_link.url_template is not None)
            self.assert_(asset.image_link.width is not None)
            self.assert_(asset.image_link.height is not None)
        elif object_type == 'Audio':
            self.assert_(asset.audio_link is not None)
            self.assert_(asset.audio_link.url is not None)
        elif object_type == 'Post':
            pass
        elif object_type == 'Comment':
            # FIXME: we have a data problem for one of our comments; parent object was deleted but the comment remained
            if len(asset.groups) > 0:
                self.assert_(asset.in_reply_to)
                self.assertValidAssetRef(asset.in_reply_to)
        elif object_type == 'Video':
            self.assert_(asset.video_link is not None)
            self.assert_(asset.video_link.embed_code is not None)

            preview = asset.preview_image_link
            if preview is not None:
                self.assert_(preview.url_template is not None)
                self.assert_(preview.width is not None)
                self.assert_(preview.height is not None)
        else:
            self.fail('asset has an unexpected objectType: %s' % \
                object_type)
        if asset.source:
            self.assert_(asset.source.permalink_url)
            self.assert_(asset.source.provider)

            self.assert_(asset.source.provider['icon'])
            self.assert_(asset.source.provider['name'])
            self.assert_(asset.source.provider['uri'])

    def assertValidUser(self, user):
        """Checks given asset for properties that should be present on all assets.
        """

        self.assert_(isinstance(user, typepad.User),
            'object %r is not a typepad.User' % user)
        self.assert_(user.id)
        self.assert_(user.url_id)
        self.assert_(len(user.object_types) > 0)
        self.assertEquals(user.object_types[0],
            'tag:api.typepad.com,2009:User')
        self.assertEquals(user.object_type, 'User')
        # this asserts as false when the user's interests is empty
        # self.assert_(user.interests)

        self.assert_(user.make_self_link())
        self.assert_(user.profile_page_url is not None)
        self.assert_(user.avatar_link is not None)
        try:
            self.assert_(user.avatar_link.url_template is not None)
        except AssertionError:
            self.assert_(user.avatar_link.url is not None)
        self.assert_(user.avatar_link.width is not None)
        self.assert_(user.avatar_link.height is not None)

    def assertValidEvent(self, event):
        """Checks given asset for properties that should be present on all assets."""

        self.assert_(isinstance(event, typepad.Event),
            'object %r is not a typepad.Event' % event)
        self.assert_(event.id)
        self.assert_(event.url_id)
        self.assert_(event.published)
        self.assert_(event.make_self_link())
        self.assert_(len(event.verbs) > 0)
        m = re.match(r'^tag:api\.typepad\.com,2009:([A-Za-z]+)$',
            event.verbs[0])
        self.assert_(m,
            "%s does not match '^tag:api\.typepad\.com,2009:[A-Za-z]+$'" \
            % event.verbs[0])
        event_type = m.group(1)
        self.assert_(event.actor)
        self.assertValidUser(event.actor)
        # FIXME: https://intranet.sixapart.com/bugs/default.asp?87911
        if event.object is None:
            pass
        elif event_type in ('AddedFavorite', 'NewAsset'):
            self.assertValidAsset(event.object)
        elif event_type == 'JoinedGroup':
            self.assertValidGroup(event.object)
        elif event_type == 'AddedNeighbor':
            self.assertValidUser(event.object)
        else:
            self.fail("Event type %s is not recognized" % event_type)

    def assertValidGroup(self, group):
        """Checks given asset for properties that should be present on all assets.
        """

        self.assert_(isinstance(group, typepad.Group),
            'object %r is not a typepad.Group' % group)
        self.assert_(group.id)
        self.assert_(group.url_id)
        self.assert_(group.display_name)
        self.assert_(group.make_self_link())
        self.assert_(len(group.object_types) > 0)
        self.assertEquals(group.object_types[0],
            'tag:api.typepad.com,2009:Group')
        self.assertEquals(group.object_type, 'Group')

    def assertValidApplication(self, app):
        self.assert_(isinstance(app, typepad.Application),
            'object %r is not a typepad.Application' % app)
        links = ('oauth_request_token_url', 'oauth_authorization_url',
            'oauth_access_token_url', 'oauth_identification_url',
            'session_sync_script_url', 'signout_url',
            'user_flyouts_script_url')
        for link in links:
            self.assert_(getattr(app, link) is not None)
        self.assert_(app.browser_upload_endpoint)

    def assertValidFavorite(self, fav):
        self.assert_(isinstance(fav, typepad.Favorite),
            'object %r is not a typepad.Favorite' % fav)
        self.assert_(fav.id)
        self.assert_(fav.url_id)
        # FIXME: https://intranet.sixapart.com/bugs/default.asp?87913
        # self.assert_(fav.published)
        self.assertValidUser(fav.author)
        self.assertValidAssetRef(fav.in_reply_to)

    def assertValidRelationshipStatus(self, rel):
        self.assert_(isinstance(rel, typepad.RelationshipStatus),
            'object %r is not a typepad.Relationship' % rel)
        self.assert_(rel.types)
        self.assert_(len(rel.types) > 0)
        for type_ in rel.types:
            self.assert_(type_ in (
                'tag:api.typepad.com,2009:Contact',
                'tag:api.typepad.com,2009:Admin',
                'tag:api.typepad.com,2009:Blocked',
                'tag:api.typepad.com,2009:Member'),
                "type '%s' is unrecognized" % type_
            )

    def assertValidRelationship(self, rel):
        self.assert_(isinstance(rel, typepad.Relationship),
            'object %r is not a typepad.Relationship' % rel)
        self.assert_(rel.url_id)
        self.assert_(rel.make_self_link())
        self.assert_(rel.status)
        # FIXME: https://intranet.sixapart.com/bugs/default.asp?87929
        # Most user-to-user relationships have created and status.types,
        # but there are some odd cases that don't.
        if isinstance(rel.source, typepad.Group) or \
            isinstance(rel.target, typepad.Group):
            self.assert_(rel.created)
            self.assert_(len(rel.status.types) > 0)
            self.assert_(rel.status.types[0] in rel.created)
        self.assert_(rel.source)
        if rel.source.object_type == 'Group':
            self.assertValidGroup(rel.source)
        elif rel.source.object_type == 'User':
            self.assertValidUser(rel.source)
        else:
            self.fail('unexpected object type %s for relationship source' % \
                rel.source.object_types[0])
        self.assert_(rel.target)
        if rel.target.object_type == 'Group':
            self.assertValidGroup(rel.target)
        elif rel.target.object_type == 'User':
            self.assertValidUser(rel.target)
        else:
            self.fail('unexpected object type %s for relationship target' % \
                rel.target.object_type)

    def assertValidAssetRef(self, ref):
        self.assert_(ref.url_id)
        self.assert_(isinstance(ref, typepad.AssetRef),
            'object %r is not a typepad.AssetRef' % ref)
        self.assert_(ref.href)
        self.assertEquals(ref.type, 'application/json')
        self.assertValidUser(ref.author)
        self.assert_(ref.object_types)
        self.assert_(len(ref.object_types) > 0)
        self.assert_(ref.object_types[0].startswith('tag:api.typepad.com'))
        self.assert_(ref.object_type)

    def filterEndpoint(self, endpoint, *args, **kwargs):
        full = endpoint.filter(**kwargs)
        slice1 = endpoint.filter(start_index=2, **kwargs)
        slice2 = endpoint.filter(max_results=1, **kwargs)
        slice3 = endpoint.filter(start_index=2, max_results=1, **kwargs)
        slice4 = endpoint.filter(max_results=0, **kwargs)
        return (full, slice1, slice2, slice3, slice4)

    def assertValidFilter(self, listset):
        (full, slice1, slice2, slice3, slice4) = listset
        self.assert_(isinstance(full, typepad.ListObject) or isinstance(full, typepad.StreamObject),
            'object %r is not a typepad.ListObject or typepad.StreamObject' % full)

        self.assert_(len(full.entries) <= 50, 'API result exceeded 50 entries')

        self.assertEquals(len(slice2.entries), 1, 'Slice %r had %d entries (expected 1)'
            % (slice2, len(slice2.entries)))
        if full.total_results > 1:
            self.assertEquals(len(slice3.entries), 1, 'Slice %r had %d entries (expected 1)'
                % (slice3, len(slice3.entries)))
        else:
            self.assertEquals(len(slice3.entries), 0, 'Slice %r had %d entries (expected 0)'
                % (slice3, len(slice3.entries)))
        self.assertEquals(len(slice4.entries), 0, 'Slice %r had %d entries (expected 0)'
            % (slice4, len(slice4.entries)))

    def post_asset(self):
        """Creates a Post asset instance for testing purposes."""

        post = typepad.Post()
        post.title = ''
        post.content = 'Test text post'

        return post

    def video_asset(self):
        """Creates a Video asset instance for testing purposes."""
        video = typepad.Video()
        video.title = ''
        video.video_link = typepad.VideoLink(
            permalink_url='http://www.youtube.com/watch?v=pWdZTqHtJ3U')
        video.content = 'Test video post'
        return video

    def link_asset(self):
        """Creates a Link asset instance for testing purposes."""
        link = typepad.Link()
        link.target_url = 'http://www.typepad.com/'
        link.title = ''
        link.content = 'Test link post'
        return link


class TestBlog(TestTypePad):

    def setUp(self):
        super(TestBlog, self).setUp()

        if not hasattr(self, 'blogger'):
            self.credentials_for('blogger')
            try:
                typepad.client.batch_request()
                try:
                    self.blogger = typepad.User.get_self()
                    self.blogs = self.blogger.blogs
                finally:
                    typepad.client.complete_batch()

                try:
                    self.blog = self.blogs[0]
                except (IndexError, AttributeError):
                    self.blog = None
            finally:
                self.clear_credentials()

    @attr(user='blogger')
    def test_blog(self):
        self.assertEquals(self.blogger.url_id, self.testdata['blogger']['xid'])
        self.assertEquals(1, len(self.blogs))

        blog = self.blogs[0]
        self.assert_(isinstance(blog, typepad.Blog))
        self.assertEquals(blog.object_type, 'Blog')
        self.assert_(blog.url_id)
        self.assert_(blog.title)
        self.assert_(blog.home_url)
        self.assert_(isinstance(blog.owner, typepad.User))
        self.assertEquals(blog.owner.url_id, self.blogger.url_id)
        try:
            blog.description
        except Exception:
            self.fail('blog has no description field')

        # Can't update a blog through the API.
        blog.title = 'moose'
        self.assertRaises(blog.BadResponse, lambda: blog.put())

    @attr(user='blogger')
    def test_categories(self):
        cats = self.blog.categories
        self.assertEquals(len(cats), 13)
        cat_labels = sorted(cats)
        self.assertEquals(cat_labels, ["Books", "Current Affairs", "Film", "Food and Drink", "Games", "Music",
            "Religion", "Science", "Sports", "Television", "Travel", "Web/Tech", "Weblogs"])

        # Can add a category.
        ret = self.blog.add_category(category="Asfdasf")
        self.assert_(ret is None)
        cats = self.blog.categories
        self.assertEquals(len(cats), 14)
        self.assert_("Asfdasf" in cats)

        # Adding an existing category does nothing.
        ret = self.blog.add_category(category="Asfdasf")
        self.assert_(ret is None)
        cats = self.blog.categories
        self.assertEquals(len(cats), 14)
        self.assert_("Asfdasf" in cats)

        # Can remove a category.
        ret = self.blog.remove_category(category="Asfdasf")
        self.assert_(ret is None)
        cats = self.blog.categories
        self.assertEquals(len(cats), 13)
        self.assert_("Asfdasf" not in cats)

        # Removing a category that doesn't exist is a Bad Request.
        self.assertRequestError(lambda: self.blog.remove_category(category="Asfdasf"))

    @attr(user='blogger')
    def test_comment_settings(self):
        settings = self.blog.commenting_settings
        self.assert_(isinstance(settings, typepad.BlogCommentingSettings))

        # These are all boolean flags, so they should all be present, whatever their value.
        self.assert_(isinstance(settings.signin_allowed, bool))
        self.assert_(isinstance(settings.signin_required, bool))
        self.assert_(isinstance(settings.email_address_required, bool))
        self.assert_(isinstance(settings.captcha_required, bool))
        self.assert_(isinstance(settings.moderation_enabled, bool))
        self.assert_(isinstance(settings.html_allowed, bool))
        self.assert_(isinstance(settings.urls_auto_linked, bool))

    def test_comments_basic(self):
        self.credentials_for('blogger')
        testpost = typepad.Post(title='Post for comments test', content='')
        try:
            self.blog.post_assets.post(testpost)
        finally:
            self.clear_credentials()

        try:
            self.credentials_for('group')  # anonymous
            comment = typepad.Comment(content='hi a test comment')
            self.assert_(comment.url_id is None)

            # Anonymous comments require name and email fields we don't support yet.
            try:
                self.assertRaises(testpost.comments.RequestError,
                    lambda: testpost.comments.post(comment))
            finally:
                self.clear_credentials()

            self.credentials_for('blogger')
            try:
                testpost.comments.post(comment)
            finally:
                self.clear_credentials()
            self.assert_(comment.url_id is not None)

            try:
                # Can't get private comments when unauthenticated.
                unauth_blog = typepad.Blog.get_by_url_id(self.blog.url_id)  # gimme a http: url
                self.assertRaises(unauth_blog.comments.BadResponse,  # 405
                    lambda: unauth_blog.comments.deliver())
                self.assertRaises(unauth_blog.comments.Unauthorized,
                    lambda: unauth_blog.comments.filter(published=True).deliver())
                new_comments = unauth_blog.comments.filter(published=True, recent=True)
                self.assert_(len(new_comments) > 0)
                self.assertEquals(new_comments[0].url_id, comment.url_id)

                # Can't get private comments for a blog when anonymously authorized.
                self.credentials_for('group')  # anonymous
                try:
                    self.assertRaises(self.blog.comments.BadResponse,  # 405
                        lambda: self.blog.comments.deliver())
                    self.assertRaises(self.blog.comments.Unauthorized,
                        lambda: self.blog.comments.filter(published=True).deliver())
                    new_comments = self.blog.comments.filter(published=True, recent=True)
                    self.assert_(len(new_comments) > 0)
                    self.assertEquals(new_comments[0].url_id, comment.url_id)
                finally:
                    self.clear_credentials()

                # Yay, the author can get all the comment sets.
                self.credentials_for('blogger')
                try:
                    self.assertRaises(self.blog.comments.BadResponse,  # 405
                        lambda: self.blog.comments.deliver())
                    publ_comments = self.blog.comments.filter(published=True)
                    self.assert_(len(publ_comments) > 0)
                    self.assertEquals(publ_comments[0].url_id, comment.url_id)
                    new_comments = self.blog.comments.filter(published=True, recent=True)
                    self.assert_(len(new_comments) > 0)
                    self.assertEquals(new_comments[0].url_id, comment.url_id)
                finally:
                    self.clear_credentials()
            finally:
                self.credentials_for('blogger')
                try:
                    comment.delete()
                finally:
                    self.clear_credentials()

        finally:
            self.credentials_for('blogger')
            try:
                testpost.delete()
            finally:
                self.clear_credentials()

    @attr(user='blogger')
    def test_crosspost_accounts(self):
        # The blog isn't configured to crosspost, but make sure we can request the endpoint.
        self.assertEquals(len(self.blog.crosspost_accounts), 0)

    @attr(user='blogger')
    def test_media_assets(self):
        # Can't GET the assets.
        self.assertRaises(self.blog.media_assets.BadResponse,  # 405
            lambda: self.blog.media_assets.deliver())

        # Try posting an image there.
        req = self.blog.media_assets.get_request(method='POST',
            headers={'content-type': 'image/png'})
        req['body'] = base64.decodestring(TEST_IMAGE_CONTENT)

        resp, cont = typepad.client.request(**req)
        media_asset = typepad.Asset()
        media_asset.update_from_response(req['uri'], resp, cont)
        try:
            self.assert_(isinstance(media_asset, typepad.Photo))
        finally:
            media_asset.delete()

    @attr(user='blogger')
    def test_new_post(self):
        posts = self.blog.post_assets

        newpost = typepad.Post(
            title='Hi a test post',
            content='This is my test post. Is it not nifty?',
            filename='asfdasf',
            categories=['Weblogs'],
        )
        self.assert_(newpost.url_id is None)

        posts.post(newpost)

        try:
            self.assert_(newpost.url_id is not None)
            self.assert_(newpost.permalink_url)
            self.assert_('asfdasf' in newpost.permalink_url)
            self.assert_(isinstance(newpost.published, datetime))
            self.assertEquals(newpost.text_format, 'html')
            self.assert_(newpost.rendered_content is not None)

            self.assertEquals(newpost.author.url_id, self.blogger.url_id)
            self.assertEquals(newpost.container.object_type, 'Blog')
            self.assert_(not newpost.publication_status.draft)

            # It's not a draft post, so it should be available in all the "published" endpoints.
            has_newpost = lambda x: self.assert_([post for post in x if post.url_id == newpost.url_id])

            has_newpost(self.blog.post_assets.filter(recent=True))
            has_newpost(self.blog.post_assets.filter(published=True, recent=True))

            self.assertRaises(self.blog.post_assets.RequestError,
                lambda: self.blog.post_assets.filter(by_category='Weblogs').deliver())

            yearmonth = newpost.published.strftime('%Y-%m')
            self.assertRaises(self.blog.post_assets.RequestError,
                lambda: self.blog.post_assets.filter(by_month=yearmonth).deliver())

        finally:
            newpost.delete()

    @attr(user='blogger')
    def test_post_by_email(self):
        self.assertRaises(self.blog.post_by_email_settings.BadResponse,
            lambda: self.blog.post_by_email_settings.filter(by_user=self.blogger.url_id).deliver())

    def test_stats(self):
        # No one views this blog so there shouldn't be any stats, but we can check we can request the endpoint.
        unauth_blog = typepad.Blog.get_by_url_id(self.blog.url_id)
        self.assertRaises(unauth_blog.stats.Forbidden,
            lambda: unauth_blog.stats.deliver())

        self.credentials_for('group')  # anonymous
        try:
            self.assertRaises(self.blog.stats.Forbidden,
                lambda: self.blog.stats.deliver())
        finally:
            self.clear_credentials()

        self.credentials_for('blogger')
        try:
            stats = self.blog.stats
            stats.deliver()

            # It might be empty, but let's assert it's the right shape anyhow.
            self.assert_(isinstance(stats.total_page_views, int))
            self.assert_(isinstance(stats.daily_page_views, dict))
            all = lambda s: reduce(lambda x,y: x and y, s)
            self.assert_(all(isinstance(k, basestring) for k in stats.daily_page_views.keys()))
            self.assert_(all(isinstance(v, int) for v in stats.daily_page_views.values()))
        finally:
            self.clear_credentials()


if __name__ == '__main__':
    from tests import utils
    utils.log()
    unittest.main()
