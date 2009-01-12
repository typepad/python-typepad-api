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
    fields = ()
    objects = {}

    def __init__(self, **kwargs):
        # create object properties for all desired fields
        for field_name in self.__class__.fields:
            value = kwargs.get(field_name)
            setattr(self, field_name, value)
        # create children objects from a property name : RemoteObject pair
        for obj_name, obj_class in self.objects.iteritems():
            value = kwargs.get(obj_name)
            if isinstance(value, list) or isinstance(value, tuple):
                obj = []
                for item in value:
                    o = obj_class(**kwargs_dict(item))
                    o.parent = self
                    obj.append(o)
            elif isinstance(value, dict):
                obj = obj_class(**kwargs_dict(value))
                obj.parent = self # e.g. reference to blog from entry
            else:
                obj = None
            setattr(self, obj_name, obj)    

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

    fields = ('name', 'email', 'uri')
    url    = r'/users/%(id)s.json'


class Entry(RemoteObject):
    fields = ('slug', 'title', 'content', 'pub_date', 'mod_date')
    objects = {'authors': User}


class Blog(RemoteObject):
    """Blog from TypePad API.
    
    >>> blog = Blog.get(1)
    >>> blog.title
    u'Fred'
    """

    fields = ('title', 'subtitle')
    objects = {'entries': Entry}
    url    = r'/blogs/%(id)s.json'

    def get_entries(self):
        pass
