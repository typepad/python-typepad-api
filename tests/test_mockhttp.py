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

    @tests.todo
    def testEntry(self):
        content = """{"id": 1, "blog_id": 1, "title": "Hi post", "content": "blah blah blah"}"""
        headers = { 'accept': 'application/json' }
        with self.mockHttp('http://127.0.0.1:8080/blogs/1/entries/1.json', content, headers) as h:
            entry = typepad.Entry.get(id=1, blog_id=1, http=h)
        self.assertEquals(entry.title,   u'Hi post')
        self.assertEquals(entry.content, u'blah blah blah')
        self.assertEquals(entry.etag, '7', 'entry got etag from http headers')

        body = """{"blog_id": 1, "title": "Hi post", "content": "blah blah blah"}"""
        content = """{"id": 2, "blog_id": 1, "title": "Hi post", "content": "blah blah blah" }"""
        entry = typepad.Entry(blog_id=1, title="Hi post", content="blah blah blah")
        with self.mockHttp('http://127.0.0.1:8080/blogs/1.json', content, method='POST', body=body) as h:
            entry.save(http=h)
        self.assertEquals(entry.id, 2, 'entry was updated with new id')
        self.assertEquals(entry.etag, '7', 'entry got etag from http headers')

        entry.title = "Second post"
        body = """{"blog_id": 1, "title": "Second post", "id": 2, "content": "blah blah blah"}"""
        content = """{"id": 2, "blog_id": 1, "title": "Second post", "content": "blah blah blah" }"""
        with self.mockHttp('http://127.0.0.1:8080/blogs/1/entries/2.json', content, method='PUT', headers={'if-match': '7'}, body=body) as h:
            entry.save(http=h)
        self.assertEquals(entry.id, 2, 'entry kept its id')
        self.assertEquals(entry.title, 'Second post', 'entry kept its new title')

if __name__ == '__main__':
    tests.log()
    unittest.main()
