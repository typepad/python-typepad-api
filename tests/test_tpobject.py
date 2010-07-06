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

import httplib2
import mox
from oauth.oauth import OAuthConsumer, OAuthToken
import simplejson as json

import remoteobjects
import typepad
from tests import utils


class TestObjects(unittest.TestCase):

    @utils.todo
    def test_relative_urls(self):
        raise NotImplementedError()

    def test_listof(self):
        x = typepad.ListOf('User')
        self.assert_(isinstance(x, type))
        self.assert_(issubclass(x, typepad.ListObject))
        self.assert_(issubclass(x, remoteobjects.PageObject))
        self.assertEquals(x.__name__, 'ListOfUser')

        y = typepad.ListOf('User')
        self.assert_(x is y, "two ListOf's the same thing are not only "
                             "equivalent but the same instance")

    def test_videolink_by_width(self):
        v = typepad.VideoLink(embed_code="\n<object width=\"500\" height=\"395\">\n    <param name=\"movie\" value=\"http://www.youtube.com/v/deadbeef\" />\n    <param name=\"quality\" value=\"high\" />\n    <param name=\"wmode\" value=\"transparent\" />\n    <param name=\"allowscriptaccess\" value=\"never\" />\n    <param name=\"allowFullScreen\" value=\"true\" />\n    <embed type=\"application/x-shockwave-flash\"\n        width=\"500\" height=\"395\"\n        src=\"http://www.youtube.com/v/deadbeef\"\n        quality=\"high\" wmode=\"transparent\" allowscriptaccess=\"never\" allowfullscreen=\"true\"\n    />\n</object>\n")
        sv = v.by_width(400)
        self.assertEquals(sv.width, 400)
        self.assertEquals(sv.height, 316)
        self.assert_(re.search('\swidth="400"', sv.embed_code))
        self.assert_(re.search('\sheight="316"', sv.embed_code))


class TestImageLink(unittest.TestCase):

    def test_basic(self):
        l = typepad.ImageLink(url_template='http://example.com/blah-{spec}')
        self.assertEquals(l.at_size('16si'), 'http://example.com/blah-16si')
        self.assertEquals(l.at_size('pi'), 'http://example.com/blah-pi')
        self.assertEquals(l.at_size('1024wi'), 'http://example.com/blah-1024wi')
        self.assertRaises(ValueError, lambda: l.at_size('77moof'))
        self.assertRaises(ValueError, lambda: l.at_size('blah'))
        self.assertRaises(ValueError, lambda: l.at_size(''))
        self.assertRaises(ValueError, lambda: l.at_size('77'))
        self.assertRaises(ValueError, lambda: l.at_size('220wi'))

    def test_exhaustive(self):
        def prove(l):
            for size in typepad.ImageLink._WI:
                i = l.by_width(size)
                i2 = l.by_width(size-1)
                self.assertEquals(i.width, min(l.width, size), "testing by_width(%d); got %d" % (min(l.width, size), i.width))
                self.assertEquals(i2.width, min(l.width, size-1), "testing by_width(%d); got %d" % (min(l.width, size-1), i2.width))

            for size in typepad.ImageLink._HI:
                i = l.by_height(size)
                i2 = l.by_height(size-1)
                self.assertEquals(i.height, min(l.height, size), "testing by_height(%d); got %d" % (min(l.height, size), i.height))
                self.assertEquals(i2.height, min(l.height, size-1), "testing by_height(%d); got %d" % (min(l.height, size-1), i2.height))

            for size in typepad.ImageLink._PI:
                i = l.inscribe(size)
                i2 = l.inscribe(size-1)
                self.assert_(i.width == min(l.width, size) or i.height == min(l.height, size), "testing inscribe(%d); got %d, %d" % (max(min(l.width, size), min(l.height, size)), i.width, i.height))
                self.assert_(i2.width == min(l.width, size-1) or i2.height == min(l.height, size-1), "testing inscribe(%d); got %d, %d" % (max(min(l.width, size-1), min(l.height, size-1)), i2.width, i2.height))

            for size in typepad.ImageLink._SI:
                i = l.square(size)
                i2 = l.square(size-1)
                self.assertEquals(i.width, min(max(l.width, l.height), size), "testing width of square(%d)" % size)
                self.assertEquals(i.height, min(max(l.width, l.height), size), "testing height of square(%d)" % size)
                self.assertEquals(i2.width, min(max(l.width, l.height), size-1), "testing width of square(%d)" % (size-1))
                self.assertEquals(i2.height, min(max(l.width, l.height), size-1), "testing height of square(%d)" % (size-1))

        # big square image
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5000, width=5000))

        # small image, wider than tall
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=100, width=200))

        # small image, taller than wide
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=200, width=100))

        # medium image, wider than tall
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=480, width=640))

        # a teeny square image
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5, width=5))

    def test_inscribe(self):
        l = typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5000, width=5000)
        self.assertEquals(l.inscribe(320).url, 'http://example.com/blah-320pi')
        self.assertEquals(l.inscribe(76).url, 'http://example.com/blah-115pi')
        self.assertEquals(l.inscribe(1).url, 'http://example.com/blah-50pi')
        self.assertEquals(l.inscribe(4999).url, 'http://example.com/blah-1024pi')
        self.assertEquals(l.inscribe(4999).width, 1024)

    def test_by_width(self):
        l = typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5000, width=5000)

        # exact, known size
        self.assertEquals(l.by_width(250).url,
            'http://example.com/blah-250wi')

        # just a bit bigger than 75px; should return 100 wide
        self.assertEquals(l.by_width(76).url, 'http://example.com/blah-100wi')

        # selects for smallest available size, 16
        self.assertEquals(l.by_width(1).url, 'http://example.com/blah-50wi')

        # selects a big size that isn't available; should return original image
        self.assertEquals(l.by_width(4999).url, 'http://example.com/blah-1024wi')
        self.assertEquals(l.by_width(4999).width, 1024)

        # selects a size larger than the original image; returns original image
        self.assertEquals(l.by_width(5001).url, 'http://example.com/blah-1024wi')

        self.assertEquals(l.by_width(None).url, 'http://example.com/blah-1024wi')


class ClientTestCase(unittest.TestCase):

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


class TestActionEndpoint(ClientTestCase):

    def test_responseless(self):
        request = {
            'uri': mox.Func(self.saver('uri')),
            'method': 'POST',
            'headers': mox.Func(self.saver('headers')),
            'body': mox.Func(self.saver('body')),
        }
        response = {
            'status': 204,  # no content
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
        http.request(**request).AndReturn((httplib2.Response(response), ''))
        mock.ReplayAll()

        class Moose(typepad.TypePadObject):

            class Snert(typepad.TypePadObject):
                volume = typepad.fields.Field()
            snert = typepad.fields.ActionEndpoint(api_name='snert', post_type=Snert)

        moose = Moose()
        moose._location = 'https://api.typepad.com/meese/7.json'

        ret = moose.snert(volume=10)
        self.assert_(ret is None)

        mock.VerifyAll()

        self.assert_(self.uri)
        self.assertEquals(self.uri, 'https://api.typepad.com/meese/7/snert.json')
        self.assert_(self.headers)
        self.assert_(self.body)

        self.assert_(utils.json_equals({
            'volume': 10
        }, self.body))

    def test_responseful(self):
        request = {
            'uri': mox.Func(self.saver('uri')),
            'method': 'POST',
            'headers': mox.Func(self.saver('headers')),
            'body': mox.Func(self.saver('body')),
        }
        response = {
            'status': 200,
            'content-type': 'application/json',
        }
        response_content = '{"blahdeblah": true, "anotherthing": "2010-07-06T16:17:05Z"}'

        http = typepad.TypePadClient()
        typepad.client = http
        http.add_credentials(
            OAuthConsumer('consumertoken', 'consumersecret'),
            OAuthToken('tokentoken', 'tokensecret'),
            domain='api.typepad.com',
        )

        mock = mox.Mox()
        mock.StubOutWithMock(http, 'request')
        http.request(**request).AndReturn((httplib2.Response(response), response_content))
        mock.ReplayAll()

        class Moose(typepad.TypePadObject):

            class Snert(typepad.TypePadObject):
                volume = typepad.fields.Field()
                target = typepad.fields.Object('User')
            class SnertResponse(typepad.TypePadObject):
                blahdeblah = typepad.fields.Field()
                anotherthing = typepad.fields.Datetime()
            snert = typepad.fields.ActionEndpoint(api_name='snert', post_type=Snert, response_type=SnertResponse)

        moose = Moose()
        moose._location = 'https://api.typepad.com/meese/7.json'

        ret = moose.snert(volume=10, target=typepad.User(display_name='fred'))
        self.assert_(ret is not None)
        self.assert_(isinstance(ret, Moose.SnertResponse))

        mock.VerifyAll()

        self.assert_(self.uri)
        self.assertEquals(self.uri, 'https://api.typepad.com/meese/7/snert.json')
        self.assert_(self.headers)
        self.assert_(self.body)

        self.assert_(utils.json_equals({
            'volume': 10,
            'target': {
                'displayName': 'fred',
                'objectType': 'User',
            },
        }, self.body))


class TestBrowserUpload(ClientTestCase):

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
        # We added credentials, so it should be a secure URL.
        self.assert_(self.uri.startswith('https://api.typepad.com/browser-upload.json'))
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
        self.assert_(utils.json_equals({
            'title': 'Fake photo',
            'content': 'This is a made-up photo for testing automated browser style upload.',
            'objectType': 'Photo',
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
