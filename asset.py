import httplib2
from urlparse import urljoin, urlparse, urlunparse
from datetime import datetime
import re

from typepad.remote import RemoteObject, BASE_URL
from typepad import fields, remote

class Link(RemoteObject):
    rel      = fields.Something()
    href     = fields.Something()
    type     = fields.Something()
    width    = fields.Something()
    height   = fields.Something()
    duration = fields.Something()

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
        total_results = fields.Something(api_name='total-results')
        start_index   = fields.Something(api_name='start-index')
        links         = fields.List(fields.Object(Link))
        entries       = fields.List(fields.Object(entryClass))

    return SpecificTypedList

class User(RemoteObject):
    # documented fields
    id            = fields.Something()
    display_name  = fields.Something(api_name='displayName')
    profile_alias = fields.Something(api_name='profileAlias')
    about_me      = fields.Something(api_name='aboutMe')
    interests     = fields.List(fields.Something())
    urls          = fields.List(fields.Something())
    accounts      = fields.List(fields.Something())
    links         = fields.List(fields.Something())
    object_type   = fields.Something(api_name='object-type')

    # astropad extras
    email         = fields.Something()
    userpic       = fields.Something()
    uri           = fields.Something()

    def relationships(self, rel='followers', by_group=None, **kwargs):
        url = "%susers/%s/relationships/@%s" % (BASE_URL, self.userid, rel)
        if by_group:
            url += "/@by-group/%s" % by_group
        url += ".json"
        return List(entryClass=UserRelationship).get(url, **kwargs)

    @property
    def userid(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:user-50
        return self.id.split('-', 1)[1]

    @property
    def permalink(self):
        ## TODO link to typepad profile?
        return self.uri

    @classmethod
    def getSelf(cls, **kwargs):
        return cls.get(urljoin(BASE_URL, '/users/@self.json'), **kwargs)

class UserRelationship(RemoteObject):
    #status = fields.Something()
    source = fields.Object(User)
    target = fields.Object(User)

class PublicationStatus(RemoteObject):
    published = fields.Something()
    spam      = fields.Something()

class ObjectRef(RemoteObject):
    ref  = fields.Something()
    href = fields.Something()
    type = fields.Something()

class Object(RemoteObject):
    # documented fields
    id           = fields.Something()
    title        = fields.Something()
    published    = fields.Datetime()
    updated      = fields.Datetime()
    summary      = fields.Something()
    content      = fields.Something()
    total        = fields.Something()
    # TODO  categories should be Tags?
    categories   = fields.List(fields.Something())
    object_types = fields.List(fields.Something(), api_name='object-types')
    status       = fields.Object(PublicationStatus)
    links        = fields.List(fields.Something())
    in_reply_to  = fields.Object(ObjectRef, api_name='in-reply-to')

    # astropad extras
    #authors      = fields.List(fields.Object(User))
    author       = fields.Object(User)

    @property
    def assetid(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:asset-1794
        return self.id.split('-', 1)[1]
    
    '''
    @property
    def author(self):
        try:
            return self.authors[0]
        except IndexError:
            return None
    '''

    def comments(self, **kwargs):
        # TODO make this clever again -- self._id is None for objects out of Lists
        #assert self._id
        #url = re.sub(r'\.json$', '/comments.json', self._id)
        url = '%sassets/%s/comments.json' % (BASE_URL, self.assetid)
        return List(entryClass=Object).get(url, **kwargs)

class Event(RemoteObject):
    id     = fields.Something()
    verbs  = fields.List(fields.Something())
    # TODO: vary these based on verb content? oh boy
    actor  = fields.Object(User)
    object = fields.Object(Object)
    
    @property
    def eventid(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:event-1680
        return self.id.split('-', 1)[1]

class Group(RemoteObject):
    id           = fields.Something()
    display_name = fields.Something(api_name='displayName')
    tagline      = fields.Something()
    avatar       = fields.Something()
    urls         = fields.List(fields.Something())
    links        = fields.List(fields.Something())
    object_type  = fields.List(fields.Something(), api_name='object-type')

    users    = remote.Link(lambda o: re.sub(r'\.json$', '/users.json',  o._id), List(entryClass=User))
    assets   = remote.Link(lambda o: re.sub(r'\.json$', '/assets.json', o._id), List(entryClass=Object))
    events   = remote.Link(lambda o: re.sub(r'\.json$', '/events.json', o._id), List(entryClass=Event))
    comments = remote.Link(lambda o: re.sub(r'\.json$', '/assets.json', o._id), List(entryClass=Object))

    @property
    def groupid(self):
        return self.id.split('-', 1)[1]
