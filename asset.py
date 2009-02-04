import httplib2
from urlparse import urljoin
from datetime import datetime
import re

from typepad.remote import RemoteObject, BASE_URL

class User(RemoteObject):
    fields = {
        'id':           basestring,
        'displayName':  basestring,
        'email':        basestring,
        'userpic':      basestring,
        'uri':          basestring,
        'interests':    basestring, 
        'object-type':  basestring,
        'aboutMe':      basestring, 
    }

    @property
    def permalink(self):
        ## TODO link to typepad profile?
        return self.uri

# crappy temp stuff

class Object(RemoteObject):
    fields = {
        'id':        basestring,
        #'control': Control,
        'title':     basestring,
        'content':   basestring,
        'link':      basestring,
        'published': datetime,
        'updated':   datetime,
        'authors':   User,
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
        'id':     basestring,
        'actor':  User,
        'object': Object,
    }

class Group(RemoteObject):
    fields = {
        'displayName':  basestring,
    }

class GroupUsers(RemoteObject):
    fields = {
        'title':  basestring, # wtf? displayName, then title? weirdo atom
        'entries': User,
    }

class GroupEvents(RemoteObject):
    fields = {
        'updated': datetime,
        'title': basestring,
        'authors': User,
        'link': basestring, 
        'entries': Entry,
    }
# end crappy temp stuff
'''
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
        """
        Extracts the unique ID of the post from the 'link' property.
        """
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
'''

class Client(object):
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def get_user(self, http=None):
        if http is None:
            http = httplib2.Http()
        http.add_credentials(self.email, self.password)

        return User.get(urljoin(BASE_URL, '/accounts/@self.json'), http=http)
