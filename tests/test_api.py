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

import cgi
from datetime import datetime
try:
    from email.feedparser import FeedParser
    from email.header import Header
except ImportError:
    from email.Parser import FeedParser
    from email.Header import Header
import logging
import os
import random
import re
from StringIO import StringIO
import sys
import traceback
import unittest
from urlparse import urlparse

import mox
from oauth.oauth import OAuthConsumer, OAuthToken
import simplejson as json

import typepad
from tests import utils


def json_equals(data, text):
    otherdata = json.loads(text)
    return bool(data == otherdata)


def json_equals_func(data):
    def confirm_equals_data(text):
        return json_equals(data, text)
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
          'headers': {
              'accept': 'application/json',
              'content-type': 'application/json',
          },
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
            'content-type': 'application/json',
          },
          'body': mox.Func(json_equals_func({"content": "Yay this is my post", "objectTypes": ["tag:api.typepad.com,2009:Post"], "title": "Omg hai"})),
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


class TestLocally(unittest.TestCase):

    def check_classy_assets(self, make_asset):
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
            'objectTypes': ('http://example.com/internet/',),
        }

        class AssetRefKeeper(typepad.TypePadObject):
            assetref = typepad.fields.Object('AssetRef')

        ar = typepad.AssetRef.from_dict(data)
        self.assert_(isinstance(ar, typepad.AssetRef))
        ar = AssetRefKeeper.from_dict({'assetref': data}).assetref
        self.assert_(isinstance(ar, typepad.AssetRef))

        data['objectTypes'] = ('tag:api.typepad.com,2009:Post',)

        # Even with a known object type, AssetRefs stay AssetRefs.
        ar = typepad.AssetRef.from_dict(data)
        self.assert_(isinstance(ar, typepad.AssetRef))
        ar = AssetRefKeeper.from_dict({'assetref': data}).assetref
        self.assert_(isinstance(ar, typepad.AssetRef))

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

    def test_relationships(self):
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

    def test_user_url_id(self):
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


class TestBrowserUpload(unittest.TestCase):

    def setUp(self):
        self.typepad_client = typepad.client

    def tearDown(self):
        typepad.client = self.typepad_client
        del self.typepad_client

        for x in ('headers', 'body'):
            try:
                delattr(self, x)
            except AttributeError:
                pass

    def saver(self, fld):
        def save_data(data):
            setattr(self, fld, data)
            return True
        return save_data

    def message_from_response(self, headers, body):
        fp = FeedParser()
        for header, value in headers.iteritems():
            fp.feed("%s: %s\n" % (header, Header(value).encode()))
        fp.feed("\n")
        fp.feed(body)
        response = fp.close()
        return response

    def test_basic(self):
        request = {
            'uri': mox.Func(self.saver('uri')),
            'method': 'POST',
            'headers': mox.Func(self.saver('headers')),
            'body': mox.Func(self.saver('body')),
        }
        response = {
            'status': 201,  # created
        }

        http = typepad.TypePadClient()
        typepad.client = http
        http.add_credentials(
            OAuthConsumer('consumertoken', 'consumersecret'),
            OAuthToken('tokentoken', 'tokensecret'),
            domain='api.typepad.com',
        )

        mock = mox.Mox()
        mock.StubOutWithMock(http, 'request')
        http.request(**request).AndReturn((response, ''))
        mock.ReplayAll()

        asset = typepad.Photo()
        asset.title = "Fake photo"
        asset.content = "This is a made-up photo for testing automated browser style upload."

        fileobj = StringIO('hi hello pretend file')
        brupload = typepad.BrowserUploadEndpoint()
        brupload.upload(asset, fileobj, "image/png",
            post_type='photo')

        mock.VerifyAll()

        self.assert_(self.uri)
        self.assert_(self.uri.startswith('http://api.typepad.com/browser-upload.json'))
        uriparts = list(urlparse(self.uri))
        querydict = cgi.parse_qs(uriparts[4])

        # TODO: really verify the signature

        # Verify the headers and body.
        self.assert_(self.headers)
        self.assert_(self.body)
        responsemsg = self.message_from_response(self.headers, self.body)

        content_type = responsemsg.get_content_type()
        self.assert_(content_type)
        self.assert_(not responsemsg.defects)

        # Check that the unparsed body has its internal mime headers
        # separated by full CRLFs, not just LFs.
        self.assert_('\r\nContent-Type:' in self.body)
        # Check that boundaries are separated by full CRLFs too.
        boundary = responsemsg.get_param('boundary')
        self.assert_(boundary + '\r\n' in self.body)

        # Make sure we're only putting credentials in the query string, not
        # the headers.
        self.assert_('oauth_signature' in querydict)
        self.assert_('authorization' not in responsemsg)
        self.assert_('Authorization' not in responsemsg)

        bodyparts = responsemsg.get_payload()
        self.assertEquals(len(bodyparts), 3)
        bodyparts = dict((part.get_param('name', header='content-disposition'),
            part) for part in bodyparts)

        self.assertEquals(bodyparts['post_type'].get_payload(), 'photo')
        self.assert_('redirect_to' not in bodyparts)

        asset_json = bodyparts['asset'].get_payload()
        self.assert_(json_equals({
            'title': 'Fake photo',
            'content': 'This is a made-up photo for testing automated browser style upload.',
            'objectTypes': ['tag:api.typepad.com,2009:Photo'],
        }, asset_json))

        filepart = bodyparts['file']
        self.assertEquals(filepart.get_payload(decode=False), 'hi hello pretend file')
        filelength = filepart.get('content-length')
        self.assertEquals(int(filelength), len('hi hello pretend file'))
        filename = filepart.get_param('filename', header='content-disposition')
        self.assert_(filename)

    def test_redirect(self):
        request = {
            'uri': mox.Func(self.saver('uri')),
            'method': 'POST',
            'headers': mox.Func(self.saver('headers')),
            'body': mox.Func(self.saver('body')),
        }
        response = {
            'status': 302,
            'location': 'http://client.example.com/hi',
        }

        http = typepad.TypePadClient()
        typepad.client = http
        http.add_credentials(
            OAuthConsumer('consumertoken', 'consumersecret'),
            OAuthToken('tokentoken', 'tokensecret'),
            domain='api.typepad.com',
        )

        mock = mox.Mox()
        mock.StubOutWithMock(http, 'request')
        http.request(**request).AndReturn((response, ''))
        mock.ReplayAll()

        asset = typepad.Photo()
        asset.title = "Fake photo"
        asset.content = "This is a made-up photo for testing automated browser style upload."

        fileobj = StringIO('hi hello pretend file')
        brupload = typepad.BrowserUploadEndpoint()
        brupload.upload(asset, fileobj, "image/png",
            redirect_to='http://client.example.com/hi',
            post_type='photo')

        mock.VerifyAll()

        # Verify the headers and body.
        self.assert_(self.headers)
        self.assert_(self.body)
        response = self.message_from_response(self.headers, self.body)

        bodyparts = response.get_payload()
        self.assertEquals(len(bodyparts), 4)
        bodyparts = dict((part.get_param('name', header='content-disposition'),
            part) for part in bodyparts)

        # Confirm that the redirect_to was sent.
        self.assert_('redirect_to' in bodyparts)
        self.assertEquals(bodyparts['redirect_to'].get_payload(),
            'http://client.example.com/hi')

    def test_real_file(self):
        request = {
            'uri': mox.Func(self.saver('uri')),
            'method': 'POST',
            'headers': mox.Func(self.saver('headers')),
            'body': mox.Func(self.saver('body')),
        }
        response = {
            'status': 201,
        }

        http = typepad.TypePadClient()
        typepad.client = http
        http.add_credentials(
            OAuthConsumer('consumertoken', 'consumersecret'),
            OAuthToken('tokentoken', 'tokensecret'),
            domain='api.typepad.com',
        )

        mock = mox.Mox()
        mock.StubOutWithMock(http, 'request')
        http.request(**request).AndReturn((response, ''))
        mock.ReplayAll()

        asset = typepad.Photo()
        asset.title = "One-by-one png"
        asset.content = "This is a 1&times;1 transparent PNG."

        fileobj = file(os.path.join(os.path.dirname(__file__), 'onebyone.png'))
        brupload = typepad.BrowserUploadEndpoint()
        brupload.upload(asset, fileobj, "image/png",
            post_type='photo')

        mock.VerifyAll()

        response = self.message_from_response(self.headers, self.body)

        (filepart,) = [part for part in response.get_payload()
            if part.get_param('name', header='content-disposition') == 'file']

        self.assertEquals(filepart.get_content_type(), 'image/png')

        # If there's a transfer encoding, it has to be the identity encoding.
        transenc = filepart.get('content-transfer-encoding')
        self.assert_(transenc is None or transenc == 'identity')

        # Check that the file content is equivalent without decoding.
        fileobj.seek(0)
        filecontent = fileobj.read()
        fileobj.close()
        self.assertEquals(filepart.get_payload(decode=False), filecontent)

        filelength = filepart.get('content-length')
        self.assertEquals(int(filelength), len(filecontent))


if __name__ == '__main__':
    utils.log()
    unittest.main()
