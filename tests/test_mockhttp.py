from __future__ import with_statement

try:
    import json
except ImportError:
    import simplejson as json

import unittest
import logging
import sys

from remoteobjects import tests
import typepad

class TestRemoteObjects(unittest.TestCase):

    def mockHttp(self, *args, **kwargs):
        return tests.MockedHttp(*args, **kwargs)

    def testUser(self):
        content = """{"displayName": "Deanna Conti", "email": "dconti@beli.com"}"""
        headers = { 'accept': 'application/json' }
        with self.mockHttp('http://127.0.0.1:8000/users/1.json', content, headers=headers) as h:
            user = typepad.User.get('http://127.0.0.1:8000/users/1.json', http=h)
        self.assertEquals(user.display_name, 'Deanna Conti')
        self.assertEquals(user.email, 'dconti@beli.com')

    def testGroup(self):
        content = """{"displayName": "Augue Tempor"}"""
        headers = { 'accept': 'application/json' }
        with self.mockHttp('http://127.0.0.1:8000/groups/1.json', content, headers=headers) as h:
            group = typepad.Group.get('http://127.0.0.1:8000/groups/1.json', http=h)
        self.assertEquals(group.display_name, 'Augue Tempor')

    def testGroupMembers(self):
        g = typepad.Group()
        g._id = 'http://127.0.0.1:8000/groups/1.json'

        adminstatus  = dict(types=["tag:api.typepad.com,2009:%s" % x for x in ('Admin', 'Member')])
        memberstatus = dict(types=["tag:api.typepad.com,2009:Member"])
        users = [
            {"displayName": "Mike", "email": "spatino@brilacsipon.info"},
            {"displayName": "Sherry Monaco", "email": "cosby@arebe.com"},
            {"displayName": "Francesca Coppola", "email": "cfrandsen@cenge.com"},
            {"displayName": "David Rosato", "email": "skemmerer@akekim.biz"},
            {"displayName": "Edgar Bach", "email": "dconti@beli.com"},
            {"displayName": "Jarad Mccaw", "email": "jmccaw@arebe.com"},
            {"displayName": "Deanna Conti", "email": "dconti@beli.com"},
        ]
        group = {
            "mumble": "butter",
        }
        content = json.dumps({
            "total-results": 5,
            "start-index":   0,
            "entries": [dict(status=adminstatus, target=group, source=users[0])] +
                [dict(status=memberstatus, target=group, source=u) for u in users[1:]],
        })

        headers = { 'accept': 'application/json' }
        with self.mockHttp('http://127.0.0.1:8000/groups/1/memberships.json', content, headers=headers) as h:
            m = g.memberships(http=h)
        self.assert_(isinstance(m, typepad.ApiList))
        self.assertEquals(len(m.entries), 7)
        self.assertEquals([u.source.display_name for u in m.entries],
            ['Mike', 'Sherry Monaco', 'Francesca Coppola', 'David Rosato', 'Edgar Bach', 'Jarad Mccaw', 'Deanna Conti'])

        # Test sequence behavior of the ApiList.
        self.assertEquals(m.entries.__len__(), 7)
        self.assertEquals(m.__len__(), 7)
        self.assertEquals(len(m), 7)
        self.assert_(isinstance(m[0], typepad.RemoteObject))
        self.assertEquals(m[0].source.display_name, 'Mike')
        self.assertEquals([u.source.display_name for u in m[1:3]],
            ['Sherry Monaco', 'Francesca Coppola'])

        # Test limit/offset parameters.
        with self.mockHttp('http://127.0.0.1:8000/groups/1/memberships.json?start-index=0', content, headers=headers) as h:
            m = g.memberships(start_index=0, http=h)

    def testPost(self):
        # Get post #1 directly from group #1?
        g = typepad.Group()
        g._id = 'http://127.0.0.1:8000/groups/1.json'

        headers = { 'accept': 'application/json' }
        content = """{"title": "O hai", "content": "Yay this is my post",
            "objectTypes": ["tag:api.typepad.com,2009:Post"]}"""
        request = dict(url='http://127.0.0.1:8000/groups/1/posts/1.json', headers=headers)
        with self.mockHttp(request, content) as h:
            e = typepad.Post.get('http://127.0.0.1:8000/groups/1/posts/1.json', http=h)
        self.assertEquals(e.title, 'O hai')
        self.assertEquals(e.content, 'Yay this is my post')

        # Modify and save the existing post.
        e.title = 'Omg hai'

        headers = {
            'accept': 'application/json',
            'if-match': '7',  # default etag
        }
        content = """{"content": "Yay this is my post", "objectTypes": ["tag:api.typepad.com,2009:Post"], "title": "Omg hai"}"""
        request = dict(url='http://127.0.0.1:8000/groups/1/posts/1.json', method='PUT', headers=headers, body=content)
        response = dict(content=content, etag='xyz')
        with self.mockHttp(request, response) as h:
            e.put(http=h)
        self.assertEquals(e.title, 'Omg hai')
        self.assertEquals(e._etag, 'xyz')

        # Make a new post in group #1.

if __name__ == '__main__':
    tests.log()
    unittest.main()
