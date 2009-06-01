from __future__ import with_statement

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

import typepad
from tests import utils

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
          'body': """{"content": "Hi this post has some content is it not nifty", "objectTypes": ["tag:api.typepad.com,2009:Post"], "title": "New post #47"}""",
          'method': 'POST' },
        { 'status': 201,
          'location': 'http://127.0.0.1:8000/assets/307.json',
          'content': """{
              "title": "New post #47",
              "content": "Hi this post has some content is it not nifty",
              "objectTypes": ["tag:api.typepad.com,2009:Post"],
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
          'body': """{"content": "Yay this is my post", "objectTypes": ["tag:api.typepad.com,2009:Post"], "title": "Omg hai"}""",
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

        mockhttp = utils.MockedHttp(*req)
        typepad.client = mockhttp.mock

        return mockhttp

    def setUp(self):
        typepad.TypePadObject.batch_requests = False

    def testUser(self):
        with self.http('get_user') as h:
            user = typepad.User.get('http://127.0.0.1:8000/users/1.json', http=h)
            self.assertEquals(user.display_name, 'Deanna Conti')

    def testGroup(self):
        with self.http('get_group') as h:
            group = typepad.Group.get('http://127.0.0.1:8000/groups/1.json', http=h)
            self.assertEquals(group.display_name, 'Augue Tempor')

    def testGroupMembers(self):
        g = typepad.Group()
        g._location = 'http://127.0.0.1:8000/groups/1.json'

        with self.http('get_group_members') as h:
            m = g.memberships
            m._http = h
            self.assertEquals(len(m.entries), 7)
            self.assertEquals([u.source.display_name for u in m.entries],
                ['Mike', 'Sherry Monaco', 'Francesca Coppola', 'David Rosato', 'Edgar Bach', 'Jarad Mccaw', 'Deanna Conti'])

        # Test sequence behavior of the API list.
        self.assertEquals(m.entries.__len__(), 7)
        self.assertEquals(m.__len__(), 7)
        self.assertEquals(len(m), 7)
        self.assert_(isinstance(m[0], typepad.RemoteObject))
        self.assertEquals(m[0].source.display_name, 'Mike')
        self.assertEquals([u.source.display_name for u in m[1:3]],
            ['Sherry Monaco', 'Francesca Coppola'])

        # Test limit/offset parameters.
        with self.http('get_group_members_offset') as h:
            m = g.memberships.filter(start_index=0)
            m._http = h
            m.deliver()

    def testCreateDeletePost(self):
        g = typepad.Group.get('http://127.0.0.1:8000/groups/1.json')

        p = typepad.Post(
            title="New post #47",
            content="Hi this post has some content is it not nifty"
        )

        with self.http('create_post', credentials=('mmalone@example.com', 'password')) as h:
            g.post_assets.post(p, http=h)

        self.assert_(p._location is not None)
        self.assertEquals(p.title, "New post #47")
        self.assert_(hasattr(p, 'published'))
        self.assert_(p.published is not None)

        with self.http('get_created_post') as h:
            post_got = typepad.Post.get(p._location, http=h)
            self.assertEquals(post_got.title, 'New post #47')
            self.assertEquals(post_got._location, p._location)

        with self.http('delete_created_post', credentials=('mmalone@example.com', 'password')) as h:
            p.delete(http=h)

        self.assert_(p._location is None)

        with self.http('get_deleted_post') as h:
            not_there = typepad.Post.get(post_got._location, http=h)
            self.assertRaises(typepad.Post.NotFound, lambda: not_there.title)

    def testChangePost(self):
        # Get post #1 directly from group #1?
        g = typepad.Group.get('http://127.0.0.1:8000/groups/1.json')

        with self.http('get_mutable_post') as h:
            e = typepad.Post.get('http://127.0.0.1:8000/assets/1.json', http=h)
            self.assertEquals(e.title, 'Fames Vivamus Placerat at Condimentum at Primis Consectetuer Nonummy Inceptos Porta dis')
            self.assertEquals(e.content, 'Posuere felis vestibulum nibh justo vitae elementum.')
        old_etag = e._etag

        # Modify the existing post.
        e.title = 'Omg hai'
        e.content = 'Yay this is my post'

        # Save the modified post.
        with self.http('put_mutated_post', credentials=('dconti@beli.com', 'password')) as h:
            e.put(http=h)
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


if __name__ == '__main__':
    utils.log()
    unittest.main()
