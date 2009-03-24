from __future__ import with_statement

try:
    import json
except ImportError:
    import simplejson as json

import logging
import random
import sys
import unittest
import traceback

from remoteobjects import tests
import typepad

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
                    'types': ('tag:api.typepad.com,2009:Admin',
                              'tag:api.typepad.com,2009:Member'),
                },
                'target': {},
                'source': {"displayName": "Mike", "email": "spatino@brilacsipon.info"},
            }] + [{
                'status': {
                    'types': ('tag:api.typepad.com,2009:Member',),
                },
                'target': {},
                'source': u,
            } for u in (
                {"displayName": "Sherry Monaco", "email": "cosby@arebe.com"},
                {"displayName": "Francesca Coppola", "email": "cfrandsen@cenge.com"},
                {"displayName": "David Rosato", "email": "skemmerer@akekim.biz"},
                {"displayName": "Edgar Bach", "email": "dconti@beli.com"},
                {"displayName": "Jarad Mccaw", "email": "jmccaw@arebe.com"},
                {"displayName": "Deanna Conti", "email": "dconti@beli.com"},
            )],
        }),
    ),
    'get_group_members_offset': (
        { 'uri': 'http://127.0.0.1:8000/groups/1/memberships.json?start-index=0',
          'headers': {'accept': 'application/json'} },
        """{ "entries": [] }"""
    ),
    'create_post': (
        { 'uri': 'http://127.0.0.1:8000/groups/1/assets.json',
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
}

class TestRemoteObjects(unittest.TestCase):

    def http(self, key, credentials=None):
        try:
            req = requests[key]
        except KeyError:
            raise Exception('No such mock request %s' % (callername,))
        return tests.MockedHttp(*req)

    def testUser(self):
        with self.http('get_user') as h:
            user = typepad.User.get('http://127.0.0.1:8000/users/1.json', http=h)
            self.assertEquals(user.display_name, 'Deanna Conti')
            self.assertEquals(user.email, 'dconti@beli.com')

    def testGroup(self):
        with self.http('get_group') as h:
            group = typepad.Group.get('http://127.0.0.1:8000/groups/1.json', http=h)
            self.assertEquals(group.display_name, 'Augue Tempor')

    def testGroupMembers(self):
        g = typepad.Group()
        g._id = 'http://127.0.0.1:8000/groups/1.json'

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
            g.assets.post(p, http=h)

        self.assert_(p._id is not None)
        self.assertEquals(p.title, "New post #47")
        self.assert_(hasattr(p, 'published'))
        self.assert_(p.published is not None)

        with self.http('get_created_post') as h:
            post_got = typepad.Post.get(p._id, http=h)
            self.assertEquals(post_got.title, 'New post #47')
            self.assertEquals(post_got._id, p._id)

        with self.http('delete_created_post', credentials=('mmalone@example.com', 'password')) as h:
            p.delete(http=h)

        self.assert_(p._id is None)

        with self.http('get_deleted_post') as h:
            not_there = typepad.Post.get(post_got._id, http=h)
            self.assertRaises(typepad.Post.NotFound, lambda: not_there.title)

    def testChangePost(self):
        # Get post #1 directly from group #1?
        g = typepad.Group.get('http://127.0.0.1:8000/groups/1.json')

        headers = { 'accept': 'application/json' }
        content = """{
            "title": "Fames Vivamus Placerat at Condimentum at Primis Consectetuer Nonummy Inceptos Porta dis",
            "content": "Posuere felis vestibulum nibh justo vitae elementum.",
            "objectTypes": ["tag:api.typepad.com,2009:Post"]
        }"""
        request = dict(uri='http://127.0.0.1:8000/assets/1.json', headers=headers)
        with self.http(request, content) as h:
            e = typepad.Post.get('http://127.0.0.1:8000/assets/1.json', http=h)
            self.assertEquals(e.title, 'Fames Vivamus Placerat at Condimentum at Primis Consectetuer Nonummy Inceptos Porta dis')
            self.assertEquals(e.content, 'Posuere felis vestibulum nibh justo vitae elementum.')
        old_etag = e._etag

        # Modify the existing post.
        e.title = 'Omg hai'
        e.content = 'Yay this is my post'

        # Save the modified post.
        headers = {
            'accept': 'application/json',
            'if-match': old_etag,  # default etag
        }
        content = """{"content": "Yay this is my post", "objectTypes": ["tag:api.typepad.com,2009:Post"], "title": "Omg hai"}"""
        request = dict(uri='http://127.0.0.1:8000/assets/1.json', method='PUT', headers=headers, body=content)
        response = dict(content=content, etag='xyz')
        with self.http(request, response, credentials=('dconti@beli.com', 'password')) as h:
            e.put(http=h)
        self.assertEquals(e.title, 'Omg hai')
        self.assertNotEqual(e._etag, old_etag)

        # Make a new post in group #1.

if __name__ == '__main__':
    tests.log()
    unittest.main()
