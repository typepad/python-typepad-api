from __future__ import with_statement

import unittest
import logging
import httplib2
import re
import mox
import email
import email.message

from remoteobjects import tests, fields
import typepad
import typepad.batch

class TestBatchRequests(unittest.TestCase):

    def setUp(self):
        typepad.batch.BATCH_REQUESTS = True
        typepad.client = typepad.batch.BatchClient()

    def mocksetter(self, key):
        def mockset(x):
            setattr(self, key, x)
            return True
        return mox.Func(mockset)

    def testLeast(self):

        class Tiny(typepad.TypePadObject):
            name = fields.Something()

        response = {
            'status': '207',
            'content-type': 'multipart/parallel; boundary="=={{[[ ASFDASF ]]}}=="',
        }
        content  = """OMG HAI

--=={{[[ ASFDASF ]]}}==
Content-Type: message/http-response
Multipart-Request-ID: 1

200 OK
Content-Type: application/json

{"name": "Potatoshop"}
--=={{[[ ASFDASF ]]}}==--"""

        self.body, self.headers = None, None

        http = mox.MockObject(httplib2.Http)
        http.request(
            'http://127.0.0.1:5001/batch-processor',
            method='POST',
            headers=self.mocksetter('headers'),
            body=self.mocksetter('body'),
        ).AndReturn((response, content))
        http.cache = None

        mox.Replay(http)

        typepad.client.http = http
        typepad.client.batch_request()
        t = Tiny.get('http://example.com/moose', http=http)  # meh injection
        typepad.client.complete_request()

        mox.Verify(http)

        self.assert_(self.headers is not None)
        self.assertEquals(sorted(self.headers.keys()), ['Content-Type', 'MIME-Version'])
        self.assertEquals(self.headers['MIME-Version'], '1.0')

        # Parse the headers through email.message to test the Content-Type value.
        mess = email.message.Message()
        for header, value in self.headers.iteritems():
            mess[header] = value
        self.assertEquals(mess.get_content_type(), 'multipart/parallel')
        boundary = mess.get_param('boundary')
        self.assert_(boundary)

        # Check that the multipart request we sent was composed correctly.
        preamble, subresponse, postamble = self.body.split('--%s' % (boundary,))
        self.assert_(None not in (preamble, subresponse, postamble))
        # Trim leading \n left over from the boundary.
        self.assert_(subresponse.startswith('\n'))
        subresponse = subresponse[1:]
        subresp_msg = email.message_from_string(subresponse)
        self.assertEquals(subresp_msg.get_content_type(), 'message/http-request')
        self.assert_('Multipart-Request-ID' in subresp_msg)

        self.assertEquals(t.name, 'Potatoshop')

    def testMulti(self):

        class Tiny(typepad.TypePadObject):
            name = fields.Something()

        response = {
            'status': '207',
            'content-type': 'multipart/parallel; boundary="foomfoomfoom"',
        }
        content = """wah-ho, wah-hay

--foomfoomfoom
Content-Type: message/http-response
Multipart-Request-ID: 2

200 OK
Content-Type: application/json

{"name": "drang"}
--foomfoomfoom
Content-Type: message/http-response
Multipart-Request-ID: 1

200 OK
Content-Type: application/json

{"name": "sturm"}
--foomfoomfoom--"""

        self.headers, self.body = None, None

        http = mox.MockObject(httplib2.Http)
        http.request(
            'http://127.0.0.1:5001/batch-processor',
            method='POST',
            headers=self.mocksetter('headers'),
            body=self.mocksetter('body'),
        ).AndReturn((response, content))
        http.cache = None

        mox.Replay(http)

        typepad.client.http = http
        typepad.client.batch_request()
        t = Tiny.get('http://example.com/moose', http=http)
        j = Tiny.get('http://example.com/fred',  http=http)
        typepad.client.complete_request()

        self.assertEquals(t.name, 'sturm')
        self.assertEquals(j.name, 'drang')

        mox.Verify(http)

    def testNotFound(self):

        class Tiny(typepad.TypePadObject):
            name = fields.Something()

        response = {
            'status': '207',
            'content-type': 'multipart/parallel; boundary="foomfoomfoom"',
        }
        content = """wah-ho, wah-hay

--foomfoomfoom
Content-Type: message/http-response
Multipart-Request-ID: 2

200 OK
Content-Type: application/json

{"name": "drang"}
--foomfoomfoom
Content-Type: message/http-response
Multipart-Request-ID: 1

404 Not Found
Content-Type: application/json

{"oops": null}
--foomfoomfoom--"""

        self.headers, self.body = None, None

        http = mox.MockObject(httplib2.Http)
        http.request(
            'http://127.0.0.1:5001/batch-processor',
            method='POST',
            headers=self.mocksetter('headers'),
            body=self.mocksetter('body'),
        ).AndReturn((response, content))
        http.cache = None

        mox.Replay(http)

        typepad.client.http = http
        typepad.client.batch_request()
        t = Tiny.get('http://example.com/moose', http=http)
        j = Tiny.get('http://example.com/fred',  http=http)

        self.assertRaises(Tiny.NotFound, lambda: typepad.client.complete_request() )

        # Does j still exist? Should it?
        self.assertEquals(j.name, 'drang')

        mox.Verify(http)

    def testCacheful(self):

        class Tiny(typepad.TypePadObject):
            name = fields.Something()

        response = {
            'status': '207',
            'content-type': 'multipart/parallel; boundary="=={{[[ ASFDASF ]]}}=="',
        }
        content  = """OMG HAI

--=={{[[ ASFDASF ]]}}==
Content-Type: message/http-response
Multipart-Request-ID: 1

304 Not Modified
Content-Type: application/json
Etag: 7

--=={{[[ ASFDASF ]]}}==--"""

        self.body, self.headers = None, None

        http = mox.MockObject(httplib2.Http)
        http.request(
            'http://127.0.0.1:5001/batch-processor',
            method='POST',
            headers=self.mocksetter('headers'),
            body=self.mocksetter('body'),
        ).AndReturn((response, content))

        http.cache = mox.MockObject(httplib2.FileCache)
        http.cache.get('http://example.com/moose').AndReturn("""status: 200\r
content-type: application/json\r
etag: 7\r
\r
{"name": "Potatoshop"}""")
        http.cache.get('http://example.com/moose').AndReturn("""status: 200\r
content-type: application/json\r
etag: 7\r
\r
{"name": "Potatoshop"}""")
        http.cache.set('http://example.com/moose', """status: 304\r
etag: 7\r
content-type: application/json\r
\r
{"name": "Potatoshop"}""")

        mox.Replay(http, http.cache)

        typepad.client.http = http
        self.assert_(http.cache)
        typepad.client.batch_request()
        t = Tiny.get('http://example.com/moose', http=http)
        typepad.client.complete_request()

        mox.Verify(http, http.cache)

        self.assertEquals(sorted(self.headers.keys()), ['Content-Type', 'MIME-Version'])
        self.assertEquals(self.headers['MIME-Version'], '1.0')

        self.assertEquals(t.name, 'Potatoshop')

    def testBatchClientErrors(self):

        self.assertRaises(typepad.batch.BatchError, lambda: typepad.client.complete_request() )

        class Tiny(typepad.TypePadObject):
            pass

        self.assertRaises(typepad.batch.BatchError, lambda: Tiny.get('http://example.com/tinytiny') )

        typepad.client.batch_request()
        self.assertRaises(typepad.batch.BatchError, lambda: typepad.client.batch_request() )


if __name__ == '__main__':
    tests.log()
    unittest.main()
