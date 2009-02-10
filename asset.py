import httplib2
from urlparse import urljoin, urlparse, urlunparse
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

class TypedList(RemoteObject):
    @classmethod
    def get(cls, url, http=None, startIndex=None, maxResults=None, **kwargs):
        queryopts = {'start-index': startIndex, 'max-results': maxResults}
        query = '&'.join(['%s=%d' % (k, v) for k, v in queryopts.iteritems() if v is not None])
        if query:
            parts = list(urlparse(url))
            if parts[4]:
                parts[4] += '&' + query
            else:
                parts[4] = query
            url = urlunparse(parts)
        return super(TypedList, cls).get(url, http=http, **kwargs)

def List(entryClass):
    class SpecificTypedList(TypedList):
        fields = {
            'total-results': fields.Something(),
            'start-index':   fields.Something(),
            'links':         fields.List(fields.Object(Link)),
            'entries':       fields.List(fields.Object(entryClass)),
        }

    return SpecificTypedList

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

    def relationships(self, rel='followers'):
        url = '%susers/%s/relationships/@%s.json' % (BASE_URL, self.userid, rel)
        return List(entryClass=UserRelationship).get(url)

    @property
    def userid(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:user-50
        return self.id.split('-', 1)[1]

    @property
    def permalink(self):
        ## TODO link to typepad profile?
        return self.uri
        
class UserRelationship(RemoteObject):
    fields = {
        #'status': fields.Something(),
        'source': fields.Object(User),
        'target': fields.Object(User),
    }

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

class Event(RemoteObject):
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
    def users(self):
        assert self._id
        userurl = re.sub(r'\.json$', '/users.json', self._id)
        return List(entryClass=User).get(userurl)
    
    @property
    def events(self):
        assert self._id
        eventurl = re.sub(r'\.json$', '/events.json', self._id)
        return List(entryClass=Event).get(eventurl)