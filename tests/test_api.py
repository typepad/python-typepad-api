# Copyright (c) 2009 Six Apart Ltd.
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

try:
    import json
except ImportError:
    import simplejson as json

from datetime import datetime
import logging
import random
import sys
import traceback
import unittest

import mox

import typepad
from tests import utils


def json_equals(data):
    def confirm_equals_data(text):
        otherdata = json.loads(text)
        if data == otherdata:
            return True
        return False
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
                'target': {"objectTypes": ["tag:api.typepad.com,2009:Group"]},
                'source': {"displayName": "Mike", "objectTypes": ["tag:api.typepad.com,2009:User"]},
            }] + [{
                'status': {
                    'created': {
                        'tag:api.typepad.com,2009:Member': '2009-01-03T00:00:00Z',
                    },
                    'types': ('tag:api.typepad.com,2009:Member',),
                },
                'target': {"objectTypes": ["tag:api.typepad.com,2009:Group"]},
                'source': u,
            } for u in (
                {"displayName": "Sherry Monaco", "objectTypes": ["tag:api.typepad.com,2009:User"]},
                {"displayName": "Francesca Coppola", "objectTypes": ["tag:api.typepad.com,2009:User"]},
                {"displayName": "David Rosato", "objectTypes": ["tag:api.typepad.com,2009:User"]},
                {"displayName": "Edgar Bach", "objectTypes": ["tag:api.typepad.com,2009:User"]},
                {"displayName": "Jarad Mccaw", "objectTypes": ["tag:api.typepad.com,2009:User"]},
                {"displayName": "Deanna Conti", "objectTypes": ["tag:api.typepad.com,2009:User"]},
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
          'headers': {'accept': 'application/json'},
          'body': """{"content": "Hi this post has some content is it not nifty", "objectTypes": ["tag:api.typepad.com,2009:Post"], "categories": [{"term": "fred"}, {"term": "wilma"}], "title": "New post #47"}""",
          'method': 'POST' },
        { 'status': 201,
          'location': 'http://127.0.0.1:8000/assets/307.json',
          'content': """{
              "title": "New post #47",
              "content": "Hi this post has some content is it not nifty",
              "objectTypes": ["tag:api.typepad.com,2009:Post"],
              "categories": [{"term": "fred"}, {"term": "wilma"}],
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
            "objectTypes": ["tag:api.typepad.com,2009:Post"],
            "categories": [{"term": "fred"}, {"term": "wilma"}],
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
            "objectTypes": ["tag:api.typepad.com,2009:Post"]
        }""",
    ),
    'put_mutated_post': (
        { 'uri': 'http://127.0.0.1:8000/assets/1.json',
          'headers': {
            'if-match': '7',
            'accept': 'application/json',
          },
          'body': mox.Func(json_equals({"content": "Yay this is my post", "objectTypes": ["tag:api.typepad.com,2009:Post"], "title": "Omg hai"})),
          'method': 'PUT' },
        { 'content': """{"content": "Yay this is my post", "objectTypes": ["tag:api.typepad.com,2009:Post"], "title": "Omg hai"}""",
          'etag': 'xyz' },
    ),
}


class TestAsset(unittest.TestCase):

    def http(self, key, credentials=None):
        try:
            req = requests[key]
        except KeyError:
            raise Exception('No such mock request %s' % (callername,))

        mock = utils.mock_http(*req)
        typepad.client = mock

        return mock

    def setUp(self):
        self.typepad_client = typepad.client
        typepad.TypePadObject.batch_requests = False

    def tearDown(self):
        typepad.client = self.typepad_client
        del self.typepad_client

    def testUser(self):
        h = self.http('get_user')
        user = typepad.User.get('http://127.0.0.1:8000/users/1.json', http=h)
        self.assertEquals(user.display_name, 'Deanna Conti')
        mox.Verify(h)

    def testGroup(self):
        h = self.http('get_group')
        group = typepad.Group.get('http://127.0.0.1:8000/groups/1.json', http=h)
        self.assertEquals(group.display_name, 'Augue Tempor')
        mox.Verify(h)

    def testGroupMembers(self):
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

    def testCreateDeletePost(self):
        g = typepad.Group.get('http://127.0.0.1:8000/groups/1.json')

        p = typepad.Post(
            title="New post #47",
            content="Hi this post has some content is it not nifty",
            categories=[typepad.Tag(term="fred", count=None), typepad.Tag(term="wilma", count=None)],
        )

        h = self.http('create_post', credentials=('mmalone@example.com', 'password'))
        g.post_assets.post(p, http=h)
        mox.Verify(h)

        self.assert_(p._location is not None)
        self.assertEquals(p.title, "New post #47")
        self.assert_(hasattr(p, 'published'))
        self.assert_(p.published is not None)

        self.assert_(len(p.categories), 2)
        tags = sorted(p.categories, key=lambda x: x.term)
        self.assertEquals(tags, [typepad.Tag(term="fred", count=None), typepad.Tag(term="wilma", count=None)])

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

    def testChangePost(self):
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


class TestLocally(unittest.TestCase):

    def checkClassyAssets(self, make_asset):
        data = {
            'id':          '7',
            'urlId':       '7',
            'title':       'some asset',
            'objectTypes': ('http://example.com/internet/',),
        }

        # Unknown objectTypes should yield an Asset.
        a = make_asset(data)
        self.assertEquals(type(a), typepad.Asset)

        # Known objectTypes should yield that type.
        data['objectTypes'] = ('tag:api.typepad.com,2009:Post',)
        a = make_asset(data)
        self.assertEquals(type(a), typepad.Post)

        # Type name needn't match the word in objectTypes.
        data['objectTypes'] = ('tag:api.typepad.com,2009:Link',)
        a = make_asset(data)
        self.assertEquals(type(a), typepad.LinkAsset)

        # Ignore extra objectTypes.
        data['objectTypes'] = ('http://example.com/internet/', 'tag:api.typepad.com,2009:Post')
        a = make_asset(data)
        self.assertEquals(type(a), typepad.Post)


    def testClassyAssetsFromDict(self):
        self.checkClassyAssets(make_asset=typepad.Asset.from_dict)


    def testClassyAssetObjectFields(self):
        class AssetKeeper(typepad.TypePadObject):
            asset = typepad.fields.Object('Asset')

        def make_asset(data):
            k = AssetKeeper.from_dict({'asset': data})
            return k.asset

        self.checkClassyAssets(make_asset)


    def testGroupMembershipWithTimestamps(self):
        data = {
            'created': {
                'tag:api.typepad.com,2009:Admin':  '2009-01-07T00:00:00Z',
                'tag:api.typepad.com,2009:Member': '2009-01-03T00:00:00Z',
            },
            'types': ('tag:api.typepad.com,2009:Member',
                      'tag:api.typepad.com,2009:Admin'),
        }

        r = typepad.RelationshipStatus.from_dict(data)
        self.assertEquals(len(r.types), 2)

        types = r.types
        self.assert_(types[0].uri)

        # Put the list in an expected order: Admin first.
        if types[0].uri != 'tag:api.typepad.com,2009:Admin':
            types.reverse()

        self.assertEquals(types[0].uri, 'tag:api.typepad.com,2009:Admin')
        self.assertEquals(types[0].created, datetime(2009, 1, 7, 0, 0, 0))
        self.assertEquals(types[1].uri, 'tag:api.typepad.com,2009:Member')
        self.assertEquals(types[1].created, datetime(2009, 1, 3, 0, 0, 0))


    def testRelationships(self):
        data = {
            'source': {
                'displayName': 'Nikola',
                'objectTypes': ['tag:api.typepad.com,2009:User'],
            },
            'target': {
                'displayName': 'Theophila',
                'objectTypes': ['tag:api.typepad.com,2009:User'],
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
        data['source']['objectTypes'] = ['tag:api.typepad.com,2009:Group']
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

    def testUserUrlId(self):
        def valid(v):
            self.assert_(typepad.User.get_by_url_id(v))

        def invalid(i):
            self.assertRaises(ValueError,
                              lambda: typepad.User.get_by_url_id(i))

        valid('asfdasf')
        valid('OHHAI')
        valid('thx1138')
        valid('url_id')
        valid('1138')
        valid('____')
        valid('_')
        valid('7')

        invalid('url id')
        invalid('url-id')
        invalid('')
        invalid('Why?')
        invalid('^hat^hat^')


if __name__ == '__main__':
    utils.log()
    unittest.main()
