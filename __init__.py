import httplib2
import simplejson
import logging
from urlparse import urljoin
import types

# TODO configurable?
BASE_URL = 'http://127.0.0.1:8080/'

def kwargs_dict(data):
    return dict([(k.encode('ascii', 'ignore'), v) for k, v in data.iteritems()])

class RemoteObject(object):
    fields = {}

    def __init__(self, **kwargs):
        for field_name, field_class in self.fields.iteritems():
            value = kwargs.get(field_name)
            if isinstance(value, list) or isinstance(value, tuple):
                value = []
                for item in value:
                    o = field_class(**kwargs_dict(item))
                    o.parent = self
                    obj.append(o)
            elif isinstance(value, dict):
                value = field_class(**kwargs_dict(value))
                value.parent = self # e.g. reference to blog from entry
            setattr(self, field_name, value)

    @classmethod
    def get(cls, id, http=None):
        # TODO accept atom or whatever other response format
        url = cls.url % {'id': id}
        url = urljoin(BASE_URL, url)
        logging.debug('Fetching %s' % (url,))

        if http is None:
            http = httplib2.Http()
        (response, content) = http.request(url)
        logging.debug('Got content %s' % (content,))

        # TODO make sure astropad is returning the proper content type
        #if data and resp.get('content-type') == 'application/json':
        data = simplejson.loads(content)
        return cls(**kwargs_dict(data))


class User(RemoteObject):
    """User from TypePad API.

    >>> user = User.get(1)
    >>> user.name
    u'Mike Malone'
    >>> user.email
    u'mjmalone@gmail.com'
    """

    fields = {
        'name':  basestring,
        'email': basestring,
        'uri':   basestring,
    }
    url    = r'/users/%(id)s.json'


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
    """Blog from TypePad API.
    
    >>> blog = Blog.get(1)
    >>> blog.title
    u'Fred'
    """

    fields = {
        'title':    basestring,
        'subtitle': basestring,
        'entries':  Entry,
    }
    url    = r'/blogs/%(id)s.json'

    def get_entries(self):
        pass
