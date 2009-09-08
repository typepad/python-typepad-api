import httplib
import httplib2
import urlparse
from oauth import oauth
import logging

import typepad


__all__ = ('OAuthAuthentication', 'OAuthClient', 'OAuthHttp', 'log')

log = logging.getLogger('typepad.oauthclient')


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
        # httplib2 only gives us the URI in parts, so rebuild it from the
        # partial uri and host.
        partial_uri = urlparse.urlsplit(request_uri)

        # Check the query to see if the URI is already signed.
        query = partial_uri[3]
        querydict = cgi.parse_qs(query)
        if 'oauth_signature' in querydict:
            # The URI is already signed. Don't do anything.
            return

        uri = urlparse.urlunsplit((self.http.default_scheme, self.host) + partial_uri[2:])

        req = self.signed_request(uri, method)
        headers.update(req.to_header())

    def signed_request(self, uri, method):
        csr, token = self.credentials
        assert token.secret is not None

        req = oauth.OAuthRequest.from_consumer_and_token(csr, token,
            http_method=method, http_url=uri)

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r for web request %s'
            % (sign_method.build_signature_base_string(req, csr, token),
               uri))
        req.sign_request(sign_method, csr, token)

        return req


httplib2.AUTH_SCHEME_CLASSES['oauth'] = OAuthAuthentication
httplib2.AUTH_SCHEME_ORDER[0:0] = ('oauth',)  # unshift onto front


class OAuthHttp(httplib2.Http):

    default_scheme = None

    def add_credentials(self, name, password, domain=""):
        super(OAuthHttp, self).add_credentials(name, password, domain)
        log.debug("Setting credentials for name %s password %s"
            % (name, password))
        if isinstance(name, oauth.OAuthConsumer) and domain:
            if self.default_scheme is None:
                self.default_scheme = urlparse.urlsplit(typepad.client.endpoint)[0]
            # Preauthorize these credentials for any request at that domain.
            cred = (name, password)
            domain = domain.lower()
            auth = OAuthAuthentication(cred, domain, "%s://%s/" % ( self.default_scheme, domain ), {}, None, None, self)
            self.authorizations.append(auth)

    def signed_request(self, uri, method=None, headers=None, body=None):
        if method is None:
            method = 'GET'

        uriparts = list(urlparse.urlparse(uri))
        host = uriparts[1]
        request_uri = urlparse.urlunparse([None, None] + uriparts[2:])

        # find OAuthAuthentication for this uri
        auths = [(auth.depth(request_uri), auth) for auth in self.authorizations if auth.inscope(host, request_uri)]
        if not auths:
            raise ValueError('No authorizations with which to sign a request to %r are available' % uri)
        auth = sorted(auths)[0][1]

        # use it to make a signed uri instead
        req = auth.signed_request(uri, method)
        uri = req.to_url()

        return self.request(uri=uri, method=method, headers=headers, body=body)


class OAuthClient(oauth.OAuthClient):

    """An httplib2 OAuth client."""

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
        h = typepad.client
        h.clear_credentials()
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            http_method = 'GET',
            http_url = self.request_token_url,
        )

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r in fetch_request_token()'
            % (sign_method.build_signature_base_string(req, self.consumer,
                                                       self.token),))
        req.sign_request(sign_method, self.consumer, self.token)

        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        if resp.status != 200:
            raise httplib.HTTPException('WHAT %d %s?!' % (resp.status, resp.reason))
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def fetch_access_token(self, request_token_str=None):
        # -> OAuthToken
        h = typepad.client
        req = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer,
            token = self.token,
            http_url = self.access_token_url,
        )

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r in fetch_access_token()'
            % (sign_method.build_signature_base_string(req, self.consumer,
                                                       self.token),))
        req.sign_request(sign_method, self.consumer, self.token)

        resp, content = h.request(req.to_url(), method=req.get_normalized_http_method())
        self.token = oauth.OAuthToken.from_string(content)
        return self.token

    def authorize_token(self, callback):
        req = oauth.OAuthRequest.from_token_and_callback(
            self.token,
            callback=callback,
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

        sign_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        req.set_parameter('oauth_signature_method', sign_method.get_name())
        log.debug('Signing base string %r in get_file_upload_url()'
            % (sign_method.build_signature_base_string(req, self.consumer,
                                                       self.token),))
        req.sign_request(sign_method, self.consumer, self.token)
        return req.to_url()
