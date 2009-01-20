import httplib2
import httplib
# TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
import simplejson
import logging
from urlparse import urljoin
import types

# TODO configurable?
BASE_URL = 'http://127.0.0.1:8080/'
EMAIL    = 'mark@sixapart.com'
PASSWORD = 'password'

class NotFound(httplib.HTTPException):
    pass

class Unauthorized(httplib.HTTPException):
    pass

class BadResponse(httplib.HTTPException):
    pass

def omit_nulls(data):
    if not isinstance(data, dict):
        data = dict(data.__dict__)
    for key in data.keys():
        # TODO: don't have etag in obj data in the first place?
        if data[key] is None or key == 'etag':
            del data[key]
    return data

class RemoteObject(object):
    fields = {}

    def __init__(self, **kwargs):
        self._id = None
        self.update(**kwargs)

    def update(self, **kwargs):
        for field_name, field_class in self.fields.iteritems():
            value = kwargs.get(field_name)
            # TODO: reuse child objects as appropriate
            if isinstance(value, list) or isinstance(value, tuple):
                new_value = []
                for item in value:
                    o = field_class(**item)
                    o.parent = self
                    new_value.append(o)
                value = new_value
            elif isinstance(value, dict):
                value = field_class(**value)
                value.parent = self # e.g. reference to blog from entry
            setattr(self, field_name, value)

    @staticmethod
    def _raise_response(response, classname, url):
        if response.status == httplib.NOT_FOUND: 
            raise NotFound('No such %s %s' % (classname, url))
        if response.status == httplib.UNAUTHORIZED:
            raise Unauthorized('Not authorized to fetch %s %s' % (classname, url))
        # catch other unhandled
        if response.status != httplib.OK:
            raise BadResponse('Bad response fetching %s %s: %d %s' % (classname, url, response.status, response.reason))
        if response.get('content-type') != 'application/json':
            raise BadResponse('Bad response fetching %s %s: content-type is %s, not JSON' % (classname, url, response.get('content-type')))

    @classmethod
    def get(cls, url, http=None, **kwargs):
        logging.debug('Fetching %s' % (url,))

        if http is None:
            http = httplib2.Http()
        (response, content) = http.request(url)
        cls._raise_response(response, classname=cls.__name__, url=url)
        logging.debug('Got content %s' % (content,))

        # TODO make sure astropad is returning the proper content type
        #if data and resp.get('content-type') == 'application/json':
        data = simplejson.loads(content)
        x = cls(**data)
        x._id = response['content-location']  # follow redirects
        if 'etag' in response:
            x._etag = response['etag']
        return x

    def save(self, http=None):
        if http is None:
            http = httplib2.Http()
        http.add_credentials(EMAIL, PASSWORD)

        body = simplejson.dumps(self, default=omit_nulls)

        httpextra = {}
        if self._id is not None:
            url = self._id
            method = 'PUT'
            if hasattr(self, _etag) and self._etag is not None:
                httpextra['headers'] = {'if-match': self._etag}
        elif self.parent is not None and self.parent._id is not None:
            url = self.parent._id
            method = 'POST'
        else:
            raise ValueError('nowhere to save this object to?')

        (response, content) = http.request(url, method=method, body=body, **httpextra)
        self._raise_response(response, classname=type(self).__name__, url=url)

        # TODO: follow redirects first?
        new_body = simplejson.loads(content)
        logging.debug('Yay saved my obj, now turning %s into new content' % (content,))
        if 'etag' in response:
            new_body['etag'] = response['etag']
        self.update(**new_body)

class User(RemoteObject):
    fields = {
        'name':  basestring,
        'email': basestring,
        'uri':   basestring,
    }

class Entry(RemoteObject):
    fields = {
        'slug':     basestring,
        'title':    basestring,
        'content':  basestring,
        'pub_date': basestring,
        'mod_date': basestring,
        'authors':  User,
    }

class Blog(RemoteObject):
    fields = {
        'title':    basestring,
        'subtitle': basestring,
        'entries':  Entry,
    }
