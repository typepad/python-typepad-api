import httplib
import httplib2
import urlparse
from oauth import oauth
import logging

from django.conf import settings

import typepad

__all__ = ('OAuthAuthentication', 'OAuthClient', 'OAuthHttp')

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
        assert token.secret is not None

        orly = oauth.OAuthRequest.from_consumer_and_token(csr, token,
            http_method=method, http_url=uri)
        sm = oauth.OAuthSignatureMethod_HMAC_SHA1()
        orly.sign_request(sm, csr, token)
        headers.update(orly.to_header())

class OAuthHttp(httplib2.Http):
    def add_credentials(self, name, password, domain=""):
        super(OAuthHttp, self).add_credentials(name, password, domain)
        if isinstance(name, oauth.OAuthConsumer) and domain:
            # Preauthorize these credentials for any request at that domain.
            cred = (name, password)
            domain = domain.lower()
            auth = OAuthAuthentication(cred, domain, "http://%s/" % domain, {}, None, None, self)
            self.authorizations.append(auth)

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
        gp_token = oauth.OAuthToken(key=settings.OAUTH_GENERAL_PURPOSE_KEY,
            secret=settings.OAUTH_GENERAL_PURPOSE_SECRET)

        h = typepad.client.http
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token=gp_token,
            http_method = 'GET',
            http_url = self.request_token_url,
        )

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        logging.error('SIGNING SIG BASE STRING %s' % (sign_method.build_signature_base_string(req, self.consumer, self.token),))
        req.sign_request(sign_method, self.consumer, self.token)

        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        if resp.status != 200:
            raise httplib.HTTPException('WHAT %d %s?!' % (resp.status, resp.reason))
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def fetch_access_token(self, request_token_str=None):
        # -> OAuthToken
        h = typepad.client.http
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token = self.token,
            http_url = self.access_token_url,
        )
        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        logging.error('SIGNING SIG BASE STRING %s' % (sign_method.build_signature_base_string(req, self.consumer, self.token),))
        req.sign_request(sign_method, self.consumer, self.token)
        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def authorize_token(self):
        h = typepad.client.http
        req = oauth.OAuthRequest.from_token_and_callback(
            self.token,
            callback=self.callback_url,
            http_url=self.authorization_url,
        )
        return req.to_url()

    def get_file_upload_url(self, upload_url):
        # oauth GET params for file upload url
        # since the form is multipart/form-data
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token = self.token,
            http_method = 'POST',
            http_url = upload_url,
        )
        # TODO put in logging?
        # log.debug('file upload sig base string: %s' % oauth.OAuthSignatureMethod_HMAC_SHA1().build_signature_base_string(req, self.consumer, self.token))
        req.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), self.consumer, self.token)
        return req.to_url()