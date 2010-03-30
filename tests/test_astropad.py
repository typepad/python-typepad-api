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

import logging
import os
import unittest
from urllib import urlencode, unquote
from urlparse import urlsplit, urlunsplit

import httplib2
import nose
from oauth import oauth

import typepad
from tests import utils
from tests import test_api


def gimme_oauth_access_token(self, email, password):
    key, secret = 'key', 'secret'

    # get a request token
    h = httplib2.Http()
    csr = oauth.OAuthConsumer(key, secret)
    req = oauth.OAuthRequest.from_consumer_and_token(csr,
        http_method='GET', http_url='http://127.0.0.1:8000/oauth/request_token/')
    req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), csr, None)
    resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
    self.assertEquals(resp.status, 200)
    token = oauth.OAuthToken.from_string(content)
    logging.debug("Got request token")

    # authorize the request token against somebody
    h = httplib2.Http()
    h.add_credentials('cosby@arebe.com', 'password')  # regular credentials
    h.follow_redirects = False
    req = oauth.OAuthRequest.from_token_and_callback(token,
        callback='http://finefi.ne/', http_method='POST',
        http_url='http://127.0.0.1:8000/oauth/authorize/')
    req.set_parameter('oauth_callback', req.get_parameter('oauth_callback'))
    req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), csr, token)
    resp, content = h.request(req.to_url(), method='GET')     # click through
    self.assertEquals(resp.status, 302)
    self.assert_(resp['location'].startswith('http://127.0.0.1:8000/oauth/login'))

    resp, content = h.request(resp['location'])
    cookie = resp['set-cookie']

    # next url has to not be absolute or astropad will replace it
    next_url = urlunsplit((None, None) + urlsplit(req.to_url())[2:])
    loginform = {
        'email':    email,
        'password': password,
        'next':     next_url,
    }
    resp, content = h.request(resp['content-location'], method='POST',
        body=urlencode(loginform), headers={'cookie': cookie})
    # Should redirect to oauth authorization form.
    # A 200 here is probably an invalid login.
    self.assertEquals(resp.status, 302)
    self.assertEquals(resp['location'], req.to_url())
    cookie = resp['set-cookie']

    resp, content = h.request(resp['location'], method='GET',  # get form
        headers={'cookie': cookie})
    self.assertEquals(resp.status, 200)
    self.assert_('text/html' in resp['content-type'])
    self.assert_('<form' in content)
    cookie = resp['set-cookie']

    req.set_parameter('authorize', 'Confirm')
    resp, content = h.request(req.get_normalized_http_url(),  # submit form
        headers={'content-type': 'application/x-www-form-urlencoded',
                 'cookie':       cookie},
        method=req.get_normalized_http_method(), body=req.to_postdata())
    self.assertEquals(resp.status, 302)
    self.assert_(resp['location'].startswith('http://finefi.ne/'))
    logging.debug("Authorized request token!")

    # get access token
    h = httplib2.Http()
    req = oauth.OAuthRequest.from_consumer_and_token(csr, token=token,
        http_url='http://127.0.0.1:8000/oauth/access_token/')
    req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), csr, token)
    resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
    self.assertEquals(resp.status, 200)
    access_token = oauth.OAuthToken.from_string(content)
    logging.debug("Got access token!!")

    return csr, access_token


class WithableHttp(object):
    def __init__(self):
        self.http = httplib2.Http()

    def __enter__(self):
        # gimme reality
        return self.http

    def __exit__(self, *exc_info):
        pass


class TestAsset(test_api.TestAsset):

    def setUp(self):
        if not os.getenv('TEST_ASTROPAD'):
            raise nose.SkipTest('no astropad tests without TEST_ASTROPAD=1')
        super(TestRemoteObjects, self).setUp()

    def http(self, *args, **kwargs):
        wh = WithableHttp()

        if 'credentials' in kwargs:
            csr, access_token = gimme_oauth_access_token(self, *kwargs['credentials'])
            wh.http.add_credentials(csr, access_token)

        return wh


class TestAstropad(unittest.TestCase):

    def setUp(self):
        if not os.getenv('TEST_ASTROPAD'):
            raise nose.SkipTest('no astropad tests without TEST_ASTROPAD=1')

    def test_oauth_setup(self):
        self.assertEquals(httplib2.AUTH_SCHEME_ORDER[0], 'oauth')
        self.assert_('oauth' in httplib2.AUTH_SCHEME_CLASSES)
        self.assert_(issubclass(httplib2.AUTH_SCHEME_CLASSES['oauth'], typepad.OAuthAuthentication))

    def test_whole_oauth_shebang(self):
        csr, access_token = gimme_oauth_access_token(self, 'dconti@beli.com', 'password')

        # finally, test that we can actually auth with the access token
        h = httplib2.Http()  # all new client
        h.follow_redirects = False
        h.add_credentials(csr, access_token)

        resp, content = h.request('http://127.0.0.1:8000/users/@self.json')
        self.assertEquals(resp.status, 302)
        self.assert_(resp['location'].startswith('http://127.0.0.1:8000/users/'))

    def test_conditional_http(self):
        class Cache(object):
            def get(self, key):
                return self.__dict__.get(key, None)
            def set(self, key, value):
                self.__dict__[key] = value
            def delete(self, key, value):
                if key in self.__dict__:
                    del self.__dict__[key]

        c = Cache()
        h = httplib2.Http(cache=c)

        resp, cont = h.request('http://127.0.0.1:8000/groups/1.json')
        self.assertEquals(resp.status, 200)
        self.assert_('etag' in resp)
        self.assert_('last-modified' in resp)
        self.assertEquals(resp['content-type'], 'application/json')
        self.failIf(resp.fromcache)
        self.assert_(c.get('http://127.0.0.1:8000/groups/1.json') is not None)

        resp, cont = h.request('http://127.0.0.1:8000/groups/1.json')
        self.assertEquals(resp.status, 200)  # cached OK!
        self.assertEquals(resp['content-type'], 'application/json')
        self.assert_(resp.fromcache)


if __name__ == '__main__':
    utils.log()
    unittest.main()
