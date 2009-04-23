"""

typepad provides connectivity to the TypePad API through remote objects.

The `typepad` package contains `RemoteObject` implementations for TypePad's
content objects and an OAuth client for making authenticated requests to the
API.

"""

__version__ = '1.0'
__date__ = '20 April 2009'
__author__ = 'Six Apart Ltd.'
__credits__ = """Brad Choate
Leah Culver
Mark Paschal"""

import httplib2

import batchhttp.client
from remoteobjects import RemoteObject, ListObject
from typepad.oauthclient import *

class TypePadClient(batchhttp.client.BatchClient, OAuthHttp):

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
from typepad.asset import *
