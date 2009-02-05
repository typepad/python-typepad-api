import httplib2
from urlparse import urljoin
from datetime import datetime
import re

from typepad.remote import RemoteObject, BASE_URL
from typepad import fields

class Link(RemoteObject):
    fields = {
        'rel':      fields.Something(),
        'href':     fields.Something(),
        'type':     fields.Something(),
        'width':    fields.Something(),
        'height':   fields.Something(),
        'duration': fields.Something(),
    }

def List(entryClass):
    class TypedList(RemoteObject):
        fields = {
            'total-results': fields.Something(),
            'start-index':   fields.Something(),
            'links':         fields.List(fields.Object(Link)),
            'entries':       fields.List(fields.Object(entryClass)),
        }
    return TypedList

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

    @property
    def members(self):
        assert self._id
        memburl = re.sub(r'\.json$', '/users.json', self._id)
        return List(entryClass=User).get(memburl)

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
