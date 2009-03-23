import httplib2
import urlparse
from oauth import oauth

from typepad import client

__all__ = ('OAuthAuthentication', 'OAuthClient')

class OAuthAuthentication(httplib2.Authentication):

    """An httplib2 Authentication module that provides OAuth authentication.

    The OAuth authentication will be tried automatically, but to use OAuth
    authentication with a particular user agent (`Http` instance), it must
    have the OAuth consumer and access token set as one of its sets of
    credentials. For instance:

    >>> csr = oauth.OAuthConsumer(key='blah', secret='moo')
    >>> token = get_access_token_for(user)
    >>> http.add_credentials(csr, token)

    """

    def request(self, method, request_uri, headers, content):
        """Add the HTTP Authorization header to the headers for this request.

        In this implementation, the Authorization header contains the OAuth
        signing information and signature.

        """
        # TODO: wtf, have to rebuild uri from partial uri and host?
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

class OAuthClient(oauth.OAuthClient):
    """
        An httplib2 OAuth client.
    """
    consumer = None
    request_token_url = None
    access_token_url = None
    authorization_url = None
    callback_url = None

    def set_consumer(self, key, secret):
        self.consumer = oauth.OAuthConsumer(
            key = key,
            secret = secret,
        )

    def set_token_from_string(self, token_str):
        self.token = oauth.OAuthToken.from_string(token_str)

    def fetch_request_token(self):
        # -> OAuthToken
        h = client.http
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            http_method = 'GET',
            http_url = self.request_token_url,
        )
        req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), self.consumer, None)
        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def fetch_access_token(self, request_token_str=None):
        # -> OAuthToken
        h = client.http
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token = self.token,
            http_url = self.access_token_url,
        )
        req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), self.consumer, self.token)
        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def authorize_token(self):
        h = client.http
        req = oauth.OAuthRequest.from_token_and_callback(
            self.token,
            callback=self.callback_url,
            http_url=self.authorization_url,
        )
        return req.to_url()
