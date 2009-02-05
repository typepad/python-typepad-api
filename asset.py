import httplib2
from urlparse import urljoin
from datetime import datetime
import re

from typepad.remote import RemoteObject, BASE_URL
from typepad import fields

class User(RemoteObject):
    fields = {
        # documented fields
        'id':           fields.Something(),
        'displayName':  fields.Something(),
        'aboutMe':      fields.Something(),
        'interests':    fields.List(fields.Something()),
        'urls':         fields.List(fields.Something()),
        'accounts':     fields.List(fields.Something()),
        'links':        fields.List(fields.Something()),
        'object-type':  fields.Something(),

        # astropad extras
        'email':        fields.Something(),
        'userpic':      fields.Something(),
        'uri':          fields.Something(),
    }

    @property
    def userid(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:user-50
        return self.id.split('-', 1)[1]

    @property
    def permalink(self):
        ## TODO link to typepad profile?
        return self.uri

# crappy temp stuff

class Object(RemoteObject):
    fields = {
        'id':        fields.Something(),
        #'control':   fields.Object(Control),
        'title':     fields.Something(),
        'content':   fields.Something(),
        'link':      fields.Something(),
        'published': fields.Datetime(),
        'updated':   fields.Datetime(),
        'authors':   fields.List(fields.Object(User)),
    }

    @property
    def assetid(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:asset-1794
        return self.id.split('-', 1)[1]

    @property
    def author(self):
        try:
            return self.authors[0]
        except IndexError:
            return None

class Entry(RemoteObject):
    fields = {
        #'verbs': Verb,
        'id':     fields.Something(),
        'actor':  fields.Object(User),
        'object': fields.Object(Object),
    }

class Group(RemoteObject):
    fields = {
        'displayName':  fields.Something(),
    }

class GroupUsers(RemoteObject):
    fields = {
        'title':  fields.Something(), # wtf? displayName, then title? weirdo atom
        'entries': fields.List(fields.Object(User)),
    }

class GroupEvents(RemoteObject):
    fields = {
        'updated': fields.Datetime(),
        'title': fields.Something(),
        'authors': fields.List(fields.Object(User)),
        'link': fields.Something(),
        'entries': fields.List(fields.Object(Entry)),
    }
# end crappy temp stuff
'''
class Entry(RemoteObject):
    fields = {
        'slug':      fields.Something(),
        'title':     fields.Something(),
        'content':   fields.Something(),
        'link':      fields.Something(),
        'published': fields.Datetime(),
        'updated':   fields.Datetime(),
        'authors':   fields.List(fields.Object(User)),
    }

    @property
    def author(self):
        try:
            return self.authors[0]
        except IndexError:
            return None

    @property
    def id(self):
        """
        Extracts the unique ID of the post from the 'link' property.
        """
        try:
            return re.search('/posts/(\d+)\.\w+$', self.link).group(1)
        except:
            return None

class Blog(RemoteObject):
    fields = {
        'title':    fields.Datetime(),
        'subtitle': fields.Datetime(),
        'authors':  fields.List(fields.Object(User)),
        'entries':  fields.List(fields.Object(Entry)),
    }
'''

class Client(object):
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def get_user(self, http=None):
        if http is None:
            http = httplib2.Http()
        http.add_credentials(self.email, self.password)

        return User.get(urljoin(BASE_URL, '/accounts/@self.json'), http=http)
