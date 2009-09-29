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

"""

typepad provides connectivity to the TypePad API through remote objects.

The `typepad` package contains `RemoteObject` implementations for TypePad's
content objects and an OAuth client for making authenticated requests to the
API.

"""

__version__ = '1.0'
__date__ = '30 September 2009'
__author__ = 'Six Apart Ltd.'
__credits__ = """Brad Choate
Leah Culver
Mark Paschal"""

import httplib2

import batchhttp.client
from remoteobjects import RemoteObject, ListObject
from typepad.oauthclient import *

class TypePadClient(batchhttp.client.BatchClient, OAuthHttp):

    endpoint = 'http://api.typepad.com/'

    def __init__(self, *args, **kwargs):
        self.cookies = dict()
        super(TypePadClient, self).__init__(*args, **kwargs)

    def request(self, uri, method="GET", body=None, headers=None, redirections=httplib2.DEFAULT_MAX_REDIRECTS, connection_type=None):
        if self.cookies:
            if headers is None:
                headers = {}
            else:
                headers = dict(headers)
            cookies = ['='.join((key, value)) for key, value in self.cookies.items()]
            headers['cookie'] = '; '.join(cookies)
        return super(TypePadClient, self).request(uri, method, body, headers, redirections, connection_type)

client = TypePadClient()

from typepad.tpobject import *
from typepad import fields
from typepad.api import *
