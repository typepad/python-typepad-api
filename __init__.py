from typepad.dataobject import DataObject
from typepad import fields
from typepad.remote import RemoteObject
from typepad.asset import *

import httplib2
from oauth import oauth

class OAuthConsumer(oauth.OAuthConsumer):
    # refuse to be used as a username for another auth scheme
    def __str__(self):
        return ""

class OAuthAuthentication(httplib2.Authentication):
    def request(self, method, request_uri, headers, content):
        # TODO: wtf, have to rebuild uri from partial uri and host?
        import urlparse
        partial_uri = urlparse.urlsplit(request_uri)
        uri = urlparse.urlunsplit(('http', self.host) + partial_uri[2:])
        
        csr, token = self.credentials
        orly = oauth.OAuthRequest.from_consumer_and_token(csr, token,
            http_method=method, http_url=uri)
        sm = oauth.OAuthSignatureMethod_HMAC_SHA1()
        orly.sign_request(sm, csr, token)
        headers.update(orly.to_header())

httplib2.AUTH_SCHEME_CLASSES['oauth'] = OAuthAuthentication
httplib2.AUTH_SCHEME_ORDER[0:0] = ('oauth',)  # unshift onto front
