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

from datetime import datetime
import logging
import random
import re
import sys
import traceback
import unittest

import httplib2
import mox
import simplejson as json

import typepad
from tests import utils


def json_equals_func(data):
    def confirm_equals_data(text):
        return utils.json_equals(data, text)
    return confirm_equals_data


requests = {
    'get_user': (
        { 'uri': 'http://127.0.0.1:8000/users/1.json',
          'headers': {'accept': 'application/json'} },
        """{"displayName": "Deanna Conti", "email": "dconti@beli.com"}""",
    ),
    'get_group': (
        { 'uri': 'http://127.0.0.1:8000/groups/1.json',
          'headers': {'accept': 'application/json'} },
        """{"displayName": "Augue Tempor"}""",
    ),
    'get_group_members': (
        { 'uri': 'http://127.0.0.1:8000/groups/1/memberships.json',
          'headers': {'accept': 'application/json'} },
        json.dumps({
            "total-results": 5,
            "start-index":   0,
            "entries": [{
                'status': {
                    'created': {
                        'tag:api.typepad.com,2009:Admin':  '2009-01-03T00:00:00Z',
                        'tag:api.typepad.com,2009:Member': '2009-01-03T00:00:00Z',
                    },
                    'types': ('tag:api.typepad.com,2009:Admin',
                              'tag:api.typepad.com,2009:Member'),
                },
                'target': {"objectType": "Group"},
                'source': {"displayName": "Mike", "objectType": "User"},
            }] + [{
                'status': {
                    'created': {
                        'tag:api.typepad.com,2009:Member': '2009-01-03T00:00:00Z',
                    },
                    'types': ('tag:api.typepad.com,2009:Member',),
                },
                'target': {"objectType": "Group"},
                'source': u,
            } for u in (
                {"displayName": "Sherry Monaco", "objectType": "User"},
                {"displayName": "Francesca Coppola", "objectType": "User"},
                {"displayName": "David Rosato", "objectType": "User"},
                {"displayName": "Edgar Bach", "objectType": "User"},
                {"displayName": "Jarad Mccaw", "objectType": "User"},
                {"displayName": "Deanna Conti", "objectType": "User"},
            )],
        }),
    ),
    'get_group_members_offset': (
        { 'uri': 'http://127.0.0.1:8000/groups/1/memberships.json?start-index=0',
          'headers': {'accept': 'application/json'} },
        """{ "entries": [] }"""
    ),
    'create_post': (
        { 'uri': 'http://127.0.0.1:8000/groups/1/post-assets.json',
          'headers': {
              'accept': 'application/json',
              'content-type': 'application/json',
          },
          'body': """{"content": "Hi this post has some content is it not nifty", "objectType": "Post", "categories": ["fred", "wilma"], "title": "New post #47"}""",
          'method': 'POST' },
        { 'status': 201,
          'location': 'http://127.0.0.1:8000/assets/307.json',
          'content': """{
              "title": "New post #47",
              "content": "Hi this post has some content is it not nifty",
              "objectType": "Post",
              "categories": ["fred", "wilma"],
              "published": "2009-03-23T00:00:00Z",
              "updated": "2009-03-23T00:00:00Z"
          }""" },
    ),
    'get_created_post': (
        { 'uri': 'http://127.0.0.1:8000/assets/307.json',
          'headers': {'accept': 'application/json'} },
        """{
            "title": "New post #47",
            "content": "Hi this post has some content is it not nifty",
            "objectType": "Post",
            "categories": ["fred", "wilma"],
            "published": "2009-03-23T00:00:00Z",
            "updated": "2009-03-23T00:00:00Z"
        }""",
    ),
    'delete_created_post': (
        { 'uri': 'http://127.0.0.1:8000/assets/307.json',
          'method': 'DELETE',
          'headers': {'if-match': '7', 'accept': 'application/json'} },
        { 'status': 204 },
    ),
    'get_deleted_post': (
        { 'uri': 'http://127.0.0.1:8000/assets/307.json',
          'headers': {'accept': 'application/json'} },
        { 'status': 404 },
    ),
    'get_mutable_post': (
        { 'uri': 'http://127.0.0.1:8000/assets/1.json',
          'headers': {'accept': 'application/json'} },
        """{
            "title": "Fames Vivamus Placerat at Condimentum at Primis Consectetuer Nonummy Inceptos Porta dis",
            "content": "Posuere felis vestibulum nibh justo vitae elementum.",
            "objectType": "Post"
        }""",
    ),
    'put_mutated_post': (
        { 'uri': 'http://127.0.0.1:8000/assets/1.json',
          'headers': {
            'if-match': '7',
            'accept': 'application/json',
            'content-type': 'application/json',
          },
          'body': mox.Func(json_equals_func({"content": "Yay this is my post", "objectType": "Post", "title": "Omg hai"})),
          'method': 'PUT' },
        { 'content': """{"content": "Yay this is my post", "objectType": "Post", "title": "Omg hai"}""",
          'etag': 'xyz' },
    ),
    'post_comment_preview': (
        { 'uri': 'http://127.0.0.1:8000/assets/1/make-comment-preview.json',
          'headers': {
            'accept': 'application/json',
            'content-type': 'application/json',
          },
          'body': mox.Func(json_equals_func({"content": "hi hello my comment hi"})),
          'method': 'POST' },
        """{"comment": {"content": "hi hello my comment hi"}}""",
    ),
}


class TestHttp(unittest.TestCase):

    def http(self, key, credentials=None):
        try:
            req = requests[key]
        except KeyError:
            raise Exception('No such mock request %s' % key)

        mock = utils.mock_http(*req)
        mock.endpoint = 'http://api.typepad.com'
        typepad.client = mock

        return mock

    def setUp(self):
        self.typepad_client = typepad.client
        typepad.TypePadObject.batch_requests = False

    def tearDown(self):
        typepad.client = self.typepad_client
        del self.typepad_client

    def test_user(self):
        h = self.http('get_user')
        user = typepad.User.get('http://127.0.0.1:8000/users/1.json', http=h)
        self.assertEquals(user.display_name, 'Deanna Conti')
        mox.Verify(h)

    def test_group(self):
        h = self.http('get_group')
        group = typepad.Group.get('http://127.0.0.1:8000/groups/1.json', http=h)
        self.assertEquals(group.display_name, 'Augue Tempor')
        mox.Verify(h)

    def test_group_members(self):
        g = typepad.Group()
        g._location = 'http://127.0.0.1:8000/groups/1.json'

        h = self.http('get_group_members')
        m = g.memberships
        m._http = h
        self.assertEquals(len(m.entries), 7)
        self.assertEquals([u.source.display_name for u in m.entries],
            ['Mike', 'Sherry Monaco', 'Francesca Coppola', 'David Rosato', 'Edgar Bach', 'Jarad Mccaw', 'Deanna Conti'])
        mox.Verify(h)

        # Test sequence behavior of the API list.
        self.assertEquals(m.entries.__len__(), 7)
        self.assertEquals(m.__len__(), 7)
        self.assertEquals(len(m), 7)
        self.assert_(isinstance(m[0], typepad.RemoteObject))
        self.assertEquals(m[0].source.display_name, 'Mike')
        self.assertEquals([u.source.display_name for u in m[1:3]],
            ['Sherry Monaco', 'Francesca Coppola'])

        # Test limit/offset parameters.
        h = self.http('get_group_members_offset')
        m = g.memberships.filter(start_index=0)
        m._http = h
        m.deliver()
        mox.Verify(h)

    def test_create_delete_post(self):
        g = typepad.Group.get('http://127.0.0.1:8000/groups/1.json')

        p = typepad.Post(
            title="New post #47",
            content="Hi this post has some content is it not nifty",
            categories=["fred", "wilma"],
        )

        h = self.http('create_post', credentials=('mmalone@example.com', 'password'))
        g.post_assets.post(p, http=h)
        mox.Verify(h)

        self.assert_(p._location is not None)
        self.assertEquals(p.title, "New post #47")
        self.assert_(hasattr(p, 'published'))
        self.assert_(p.published is not None)

        self.assert_(len(p.categories), 2)
        self.assertEquals(p.categories, ["fred", "wilma"])

        h = self.http('get_created_post')
        post_got = typepad.Post.get(p._location, http=h)
        self.assertEquals(post_got.title, 'New post #47')
        self.assertEquals(post_got._location, p._location)
        mox.Verify(h)

        h = self.http('delete_created_post', credentials=('mmalone@example.com', 'password'))
        p.delete(http=h)
        mox.Verify(h)

        self.assert_(p._location is None)

        h = self.http('get_deleted_post')
        not_there = typepad.Post.get(post_got._location, http=h)
        self.assertRaises(typepad.Post.NotFound, lambda: not_there.title)
        mox.Verify(h)

    def test_change_post(self):
        # Get post #1 directly from group #1?
        g = typepad.Group.get('http://127.0.0.1:8000/groups/1.json')

        h = self.http('get_mutable_post')
        e = typepad.Post.get('http://127.0.0.1:8000/assets/1.json', http=h)
        self.assertEquals(e.title, 'Fames Vivamus Placerat at Condimentum at Primis Consectetuer Nonummy Inceptos Porta dis')
        self.assertEquals(e.content, 'Posuere felis vestibulum nibh justo vitae elementum.')
        mox.Verify(h)
        old_etag = e._etag

        # Modify the existing post.
        e.title = 'Omg hai'
        e.content = 'Yay this is my post'

        # Save the modified post.
        h = self.http('put_mutated_post', credentials=('dconti@beli.com', 'password'))
        e.put(http=h)
        mox.Verify(h)
        self.assertEquals(e.title, 'Omg hai')
        self.assertNotEqual(e._etag, old_etag)

    def test_action_endpoint(self):
        asset = typepad.Asset.get('http://127.0.0.1:8000/assets/1.json')

        h = self.http('post_comment_preview')
        preview = asset.make_comment_preview(content='hi hello my comment hi')
        mox.Verify(h)


class TestUrlId(unittest.TestCase):

    def check_url_id(self, cls):
        works = (
            lambda: cls.get_by_url_id('6a00d83451ce6b69e20120a81fb3a4970c'),
            lambda: cls.get_by_id('tag:api.typepad.com,2009:6a00d83451ce6b69e20120a81fb3a4970c'),
            lambda: cls.get_by_id('6a00d83451ce6b69e20120a81fb3a4970c'),
        )

        for work in works:
            obj = work()
            self.assert_('6a00d83451ce6b69e20120a81fb3a4970c' in obj._location)
            self.assertEqual(obj.url_id, '6a00d83451ce6b69e20120a81fb3a4970c')  # doesn't deliver
            self.assertEqual(obj.xid, '6a00d83451ce6b69e20120a81fb3a4970c')
            self.assertEqual(obj.id, 'tag:api.typepad.com,2009:6a00d83451ce6b69e20120a81fb3a4970c')

        self.assertRaises(ValueError, lambda: cls.get_by_url_id(''))
        self.assertRaises(ValueError, lambda: cls.get_by_id(''))

        # See if link generation with make_self_link() works.
        obj = cls()
        obj.update_from_dict({'urlId': '6a00d83451ce6b69e20120a81fb3a4970c'})
        self.assert_(obj._location is not None)
        # UserProfile's doesn't end in /urlId.json, so just check that it's in there somewhere.
        self.assert_('6a00d83451ce6b69e20120a81fb3a4970c' in obj._location)

    def _check(cls):
        def check_for_class(self):
            self.check_url_id(cls)
        check_for_class.__name__ = 'test_%s' % cls.__name__.lower()
        return check_for_class

    test_asset = _check(typepad.Asset)
    test_blog = _check(typepad.Blog)
    test_event = _check(typepad.Event)
    test_externalfeedsubscription = _check(typepad.ExternalFeedSubscription)
    test_favorite = _check(typepad.Favorite)
    test_relationship = _check(typepad.Relationship)
    test_group = _check(typepad.Group)
    test_user = _check(typepad.User)
    test_userprofile = _check(typepad.UserProfile)


class TestAsset(unittest.TestCase):

    def check_classy_assets(self, make_asset):
        data = {
            'id':          '7',
            'urlId':       '7',
            'title':       'some asset',
            'objectType':  'internet',
        }

        # Unknown objectTypes should yield an Asset.
        a = make_asset(data)
        self.assertEquals(type(a), typepad.Asset)

        # A known objectType should yield that type.
        data['objectType'] = 'Post'
        a = make_asset(data)
        self.assertEquals(type(a), typepad.Post)

    def test_classy_assets_from_dict(self):
        self.check_classy_assets(make_asset=typepad.Asset.from_dict)

    def test_classy_asset_object_fields(self):
        class AssetKeeper(typepad.TypePadObject):
            asset = typepad.fields.Object('Asset')

        def make_asset(data):
            k = AssetKeeper.from_dict({'asset': data})
            return k.asset

        self.check_classy_assets(make_asset)

    def test_unclassy_assetrefs(self):
        data = {
            'id':          '7',
            'urlId':       '7',
            'title':       'some asset',
            'objectType':  'internet',
        }

        class AssetRefKeeper(typepad.TypePadObject):
            assetref = typepad.fields.Object('AssetRef')

        ar = typepad.AssetRef.from_dict(data)
        self.assert_(isinstance(ar, typepad.AssetRef))
        ar = AssetRefKeeper.from_dict({'assetref': data}).assetref
        self.assert_(isinstance(ar, typepad.AssetRef))

        data['objectType'] = 'Post'

        # Even with a known object type, AssetRefs stay AssetRefs.
        ar = typepad.AssetRef.from_dict(data)
        self.assert_(isinstance(ar, typepad.AssetRef))
        ar = AssetRefKeeper.from_dict({'assetref': data}).assetref
        self.assert_(isinstance(ar, typepad.AssetRef))

    def test_asset_ref(self):
        asset = typepad.Asset(
            id='tag:api.typepad.com,2009:6a00d83451ce6b69e20120a81fb3a4970c',
            url_id='6a00d83451ce6b69e20120a81fb3a4970c',
            author=typepad.User(
                url_id='6p00d83451ce6b69e2',
            ),
            object_types=['tag:api.typepad.com,2009:Post'],
            object_type='Post'
        )

        ref = asset.asset_ref

        self.assert_(isinstance(ref, typepad.AssetRef))
        self.assertEqual(ref.id, 'tag:api.typepad.com,2009:6a00d83451ce6b69e20120a81fb3a4970c')
        self.assertEqual(ref.url_id, '6a00d83451ce6b69e20120a81fb3a4970c')
        self.assert_(ref.author is not None)
        self.assert_(isinstance(ref.author, typepad.User))
        self.assertEqual(ref.author.url_id, '6p00d83451ce6b69e2')
        self.assertEqual(ref.object_type, 'Post')
        self.assertEqual(ref.object_types, ['tag:api.typepad.com,2009:Post'])

    def test_stringification(self):
        asset = typepad.Asset(
            title='this is my title',
            content='This is my content.',
        )
        self.assertEqual(str(asset), 'this is my title')
        self.assertEqual(unicode(asset), 'this is my title')

        asset = typepad.Asset(
            content='This is my content.',
        )
        self.assertEqual(str(asset), 'This is my content.')
        self.assertEqual(unicode(asset), 'This is my content.')

        asset = typepad.Asset(
            title=u'I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n',
        )
        self.assertRaises(UnicodeError, lambda: str(asset))
        self.assertEqual(unicode(asset), u'I\xc3\xb1t\xc3\xabrn\xc3\xa2ti\xc3\xb4n\xc3\xa0liz\xc3\xa6ti\xc3\xb8n')


class TestRelationship(unittest.TestCase):

    def test_group_membership_with_timestamps(self):
        data = {
            'created': {
                'tag:api.typepad.com,2009:Admin':  '2009-01-07T00:00:00Z',
                'tag:api.typepad.com,2009:Member': '2009-01-03T00:00:00Z',
            },
            'status': {
                'types': ('tag:api.typepad.com,2009:Member',
                          'tag:api.typepad.com,2009:Admin')
            }
        }

        r = typepad.Relationship.from_dict(data)
        self.assertEquals(len(r.status.types), 2)

        types = r.status.types
        self.assert_(types[0])

        created = r.created
        self.assert_(created['tag:api.typepad.com,2009:Member'])

        # Put the list in an expected order: Admin first.
        if types[0] != 'tag:api.typepad.com,2009:Admin':
            types.reverse()

        self.assertEquals(types[0], 'tag:api.typepad.com,2009:Admin')
        self.assertEquals(created[types[0]], datetime(2009, 1, 7, 0, 0, 0))
        self.assertEquals(types[1], 'tag:api.typepad.com,2009:Member')
        self.assertEquals(created[types[1]], datetime(2009, 1, 3, 0, 0, 0))

    def test_object_typing(self):
        data = {
            'source': {
                'displayName': 'Nikola',
                'objectType':  'User',
            },
            'target': {
                'displayName': 'Theophila',
                'objectType':  'User',
            },
            'status': {
                'types': ['tag:api.typepad.com,2009:Contact'],
            },
        }

        r = typepad.Relationship.from_dict(data)
        self.assert_(isinstance(r.source, typepad.User))
        self.assert_(isinstance(r.target, typepad.User))

        data['status']['types'] = ['tag:api.typepad.com,2009:Blocked']
        r = typepad.Relationship.from_dict(data)
        self.assert_(isinstance(r.source, typepad.User))
        self.assert_(isinstance(r.target, typepad.User))

        data['status']['types']       = ['tag:api.typepad.com,2009:Member']
        data['source']['objectType']  = 'Group'
        r = typepad.Relationship.from_dict(data)
        self.assert_(isinstance(r.source, typepad.Group))
        self.assert_(isinstance(r.target, typepad.User))

        data['status']['types'] = ['tag:api.typepad.com,2009:Moderator']
        r = typepad.Relationship.from_dict(data)
        self.assert_(isinstance(r.source, typepad.Group))
        self.assert_(isinstance(r.target, typepad.User))

        data['status']['types'] = ['tag:api.typepad.com,2009:Admin']
        r = typepad.Relationship.from_dict(data)
        self.assert_(isinstance(r.source, typepad.Group))
        self.assert_(isinstance(r.target, typepad.User))

        data['status']['types'] = ['tag:api.typepad.com,2009:Asfdasf']
        r = typepad.Relationship.from_dict(data)
        self.assert_(isinstance(r.source, typepad.Group))
        self.assert_(isinstance(r.target, typepad.User))

    def test_type_checking(self):
        data = {
            'source': {
                'displayName': 'Nikola',
                'objectType':  'User',
            },
            'target': {
                'displayName': 'Theophila',
                'objectType':  'User',
            },
            'status': {
                'types': ['tag:api.typepad.com,2009:Contact'],
            },
        }

        r = typepad.Relationship.from_dict(data)
        self.assert_(isinstance(r.source, typepad.User))
        self.assert_(isinstance(r.target, typepad.User))

        self.assert_(not r.is_member())
        self.assert_(not r.is_admin())
        self.assert_(not r.is_blocked())

        data['source']['objectType'] = 'Group'
        data['status']['types'] = ['tag:api.typepad.com,2009:Member']
        r = typepad.Relationship.from_dict(data)

        self.assert_(r.is_member())
        self.assert_(not r.is_admin())
        self.assert_(not r.is_blocked())

        data['status']['types'] = ['tag:api.typepad.com,2009:Member', 'tag:api.typepad.com,2009:Asfdasf',
            'tag:api.typepad.com,2009:Admin']
        r = typepad.Relationship.from_dict(data)

        self.assert_(r.is_member())
        self.assert_(r.is_admin())
        self.assert_(not r.is_blocked())

        data['status']['types'] = ['tag:api.typepad.com,2009:Blocked']
        r = typepad.Relationship.from_dict(data)

        self.assert_(not r.is_member())
        self.assert_(not r.is_admin())
        self.assert_(r.is_blocked())

    def test_block(self):
        real_typepad_client = typepad.client
        typepad.client = mox.MockObject(httplib2.Http)
        try:
            resp = httplib2.Response({
                'status':           200,
                'etag':             '7',
                'content-type':     'application/json',
                'content-location': 'http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
            })
            typepad.client.request(
                uri='http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
                headers={'accept': 'application/json'},
            ).AndReturn((resp, """{"types": ["tag:api.typepad.com,2009:Member"]}"""))
            resp = httplib2.Response({
                'status':           200,
                'etag':             '9',
                'content-type':     'application/json',
                'content-location': 'http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
            })
            typepad.client.request(
                uri='http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
                method='PUT',
                headers={'if-match': '7', 'accept': 'application/json', 'content-type': 'application/json'},
                body=mox.Func(json_equals_func({"types": ["tag:api.typepad.com,2009:Blocked"]})),
            ).AndReturn((resp, """{"types": ["tag:api.typepad.com,2009:Blocked"]}"""))
            mox.Replay(typepad.client)

            r = typepad.Relationship.get('http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c.json')
            r.block()

            mox.Verify(typepad.client)

        finally:
            typepad.client = real_typepad_client

    def test_leave(self):
        real_typepad_client = typepad.client
        typepad.client = mox.MockObject(httplib2.Http)
        try:
            resp = httplib2.Response({
                'status':           200,
                'etag':             '7',
                'content-type':     'application/json',
                'content-location': 'http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
            })
            typepad.client.request(
                uri='http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
                headers={'accept': 'application/json'},
            ).AndReturn((resp, """{"types": ["tag:api.typepad.com,2009:Member"]}"""))
            resp = httplib2.Response({
                'status':           200,
                'etag':             '9',
                'content-type':     'application/json',
                'content-location': 'http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
            })
            typepad.client.request(
                uri='http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c/status.json',
                method='PUT',
                headers={'if-match': '7', 'accept': 'application/json', 'content-type': 'application/json'},
                body=mox.Func(json_equals_func({"types": []})),
            ).AndReturn((resp, """{"types": []}"""))
            mox.Replay(typepad.client)

            r = typepad.Relationship.get('http://127.0.0.1:8000/relationships/6r00d83451ce6b69e20120a81fb3a4970c.json')
            r.leave()

            mox.Verify(typepad.client)

        finally:
            typepad.client = real_typepad_client


class TestUserAndUserProfile(unittest.TestCase):

    def test_get_self(self):
        me = typepad.User.get_self()
        self.assert_(me._location.endswith('/users/@self.json'))

    def test_related_profile(self):
        my_profile = typepad.UserProfile.get_by_url_id('6p00d83451ce6b69e2')
        me = my_profile.user
        self.assert_(isinstance(me, typepad.User))
        self.assertEqual(me.url_id, '6p00d83451ce6b69e2')

        me = typepad.User.get_by_url_id('6p00d83451ce6b69e2')
        my_profile = me.profile
        self.assert_(isinstance(my_profile, typepad.UserProfile))
        self.assertEqual(my_profile.url_id, '6p00d83451ce6b69e2')


if __name__ == '__main__':
    utils.log()
    unittest.main()
