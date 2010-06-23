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


import unittest
from urlparse import urlsplit

from oauth.oauth import OAuthConsumer, OAuthToken

import typepad.tpclient


class TestTypePadClient(unittest.TestCase):

    def assertScheme(self, url, *args):
        scheme = urlsplit(url)[0]
        return self.assertEquals(scheme, *args)

    def test_adjust_scheme(self):
        c = typepad.tpclient.TypePadClient()
        c.endpoint = 'http://api.typepad.com'

        c.clear_credentials()
        self.assertScheme(c.endpoint, 'http')

        c.clear_credentials()
        c.add_credentials('a', 'b')
        self.assertScheme(c.endpoint, 'http')

        c.clear_credentials()
        c.add_credentials('a', 'b', domain='api.typepad.com')
        self.assertScheme(c.endpoint, 'http')

        c.clear_credentials()
        c.add_credentials(OAuthConsumer('a', 'b'), OAuthToken('c', 'd'))
        self.assertScheme(c.endpoint, 'https')

        c.clear_credentials()
        c.add_credentials(OAuthConsumer('a', 'b'), OAuthToken('c', 'd'), domain='api.example.com')
        self.assertScheme(c.endpoint, 'http')

        c.clear_credentials()
        c.add_credentials(OAuthConsumer('a', 'b'), OAuthToken('c', 'd'), domain='typepad.com')
        self.assertScheme(c.endpoint, 'http')

        # This time for sure!!
        c.clear_credentials()
        c.add_credentials(OAuthConsumer('a', 'b'), OAuthToken('c', 'd'), domain='api.typepad.com')
        self.assertScheme(c.endpoint, 'https')

        # Try it again.
        c.clear_credentials()
        c.add_credentials(OAuthConsumer('a', 'b'), OAuthToken('c', 'd'), domain='api.typepad.com')
        self.assertScheme(c.endpoint, 'https')

        # Check that clearing works.
        c.clear_credentials()
        self.assertScheme(c.endpoint, 'http')

    def test_consumer_property(self):
        c = typepad.tpclient.TypePadClient()
        c.endpoint = 'http://api.typepad.com'

        # make sure initial credentials are clear
        self.assert_(len(c.authorizations) == 0)
        self.assert_(len(c.credentials.credentials) == 0)

        # we can specify consumer and token as OAuth objects
        c.consumer = OAuthConsumer('x', 'y')
        c.token = OAuthToken('z', 'q')
        self.assert_(len(c.credentials.credentials) == 1)
        self.assertScheme(c.endpoint, 'https')

        # we can specify consumer and token as tuples of key/secrets
        c.consumer = ('a', 'b')
        c.token = ('a', 'b')
        self.assert_(len(c.credentials.credentials) == 1)
        self.assertScheme(c.endpoint, 'https')

        # assigning "None" to either token or consumer will
        # effectively clear credentials also
        c.token = None
        self.assert_(len(c.credentials.credentials) == 0)
        self.assertScheme(c.endpoint, 'http')

        c.clear_credentials()
        self.assertScheme(c.endpoint, 'http')
