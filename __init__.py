import httplib2
import httplib
# TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
import simplejson
import logging
from urlparse import urljoin
import types
from datetime import datetime
import time
import re

# TODO configurable?
BASE_URL = 'http://127.0.0.1:8000/'
EMAIL    = 'mjmalone@gmail.com'
PASSWORD = 'password'

class NotFound(httplib.HTTPException):
    pass

class Unauthorized(httplib.HTTPException):
    pass

class BadResponse(httplib.HTTPException):
    pass

def omit_nulls(data):
    if not isinstance(data, dict):
        if not hasattr(data, '__dict__'):
            return str(data)
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
        self.parent = None
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
            elif field_class is datetime:
                if value is not None:
                    value = datetime(*(time.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))[0:6])
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

    def serialize_value(self, value):
        if isinstance(value, RemoteObject):
            value = value.to_dict()
        elif isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, dict):
            pass
        elif isinstance(value, list):
            newlist = []
            for x in value:
                newlist.append(self.serialize_value(x))
            value = newlist
        elif not isinstance(value, basestring):
            value = str(value)
        return value

    def to_dict(self):
        data = {}
        for field_name, field_class in self.fields.iteritems():
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = self.serialize_value(value)
        return data

    def save(self, http=None):
        if http is None:
            http = httplib2.Http()
        http.add_credentials(EMAIL, PASSWORD)

        body = simplejson.dumps(self.to_dict(), default=omit_nulls)

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
            # FIXME: !
            url = urljoin(BASE_URL, '/blogs/1/posts.json')
            method = 'POST'
            # raise ValueError('nowhere to save this object to?')

        (response, content) = http.request(url, method=method, body=body, **httpextra)

        # TBD: check for errors
        # self._raise_response(response, classname=type(self).__name__, url=url)

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

    @property
    def userpic(self):
        return 'http://s3.amazonaws.com/twitter_production/profile_images/20744492/photo_avatar_bigger.jpg'

    @property
    def permalink(self):
        return self.uri

class Group(RemoteObject):
    fields = {
        'name':  basestring,
        'members': User,
    }

class Entry(RemoteObject):
    fields = {
        'slug':      basestring,
        'title':     basestring,
        'content':   basestring,
        'link':      basestring,
        'published': datetime,
        'updated':   datetime,
        'authors':   User,
    }

    @property
    def author(self):
        try:
            return self.authors[0]
        except IndexError:
            return None

    @property
    def id(self):
        try:
            return re.search('/posts/(\d+)\.\w+$', self.link).group(1)
        except:
            return None

class Blog(RemoteObject):
    fields = {
        'title':    basestring,
        'subtitle': basestring,
        'authors':  User,
        'entries':  Entry,
    }

class Client(object):
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def get_user(self, http=None):
        if http is None:
            http = httplib2.Http()
        http.add_credentials(self.email, self.password)

        return User.get(urljoin(BASE_URL, '/accounts/@self.json'), http=http)
