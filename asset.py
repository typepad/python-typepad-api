from urlparse import urljoin, urlparse, urlunparse
from datetime import datetime
import re

from typepad import fields, remote, RemoteObject

class Link(RemoteObject):
    rel      = fields.Something()
    href     = fields.Something()
    type     = fields.Something()
    width    = fields.Something()
    height   = fields.Something()
    duration = fields.Something()

class ApiList(RemoteObject):
    total_results = fields.Something(api_name='totalResults')
    start_index   = fields.Something(api_name='startIndex')
    links         = fields.List(fields.Object(Link))
    entries       = fields.List(fields.Something())

    @classmethod
    def from_dict(cls, value, entry_class):
        self = super(ApiList, cls).from_dict(value)
        # Post-convert all the "entries" list items to our entry class.
        self.entries = [entry_class.from_dict(d) for d in self.entries]
        return self

class ApiListField(fields.Object):
    def decode(self, value):
        if not isinstance(value, dict):
            # Let Object.decode() throw the TypeError.
            return super(ApiListField, self).decode(value)
        return ApiList.from_dict(value, entry_class=self.cls)

class ApiListLink(remote.Link):
    def __init__(self, kind, entry_class):
        def rewriteJsonEnding(obj):
            return re.sub(r'\.json$', '/%s.json' % kind, obj._id)
        super(ApiListLink, self).__init__(rewriteJsonEnding, ApiListField(entry_class))

class User(RemoteObject):
    # documented fields
    atom_id       = fields.Something(api_name='id')
    display_name  = fields.Something(api_name='displayName')
    profile_alias = fields.Something(api_name='profileAlias')
    about_me      = fields.Something(api_name='aboutMe')
    interests     = fields.List(fields.Something())
    urls          = fields.List(fields.Something())
    accounts      = fields.List(fields.Something())
    links         = fields.List(fields.Something())
    object_type   = fields.Something(api_name='objectType')

    # astropad extras
    email         = fields.Something()
    userpic       = fields.Something()
    uri           = fields.Something()

    def relationship_url(self, rel='followers', by_group=None):
        url = "%susers/%s/relationships/@%s" % (remote.BASE_URL, self.id, rel)
        if by_group:
            url += "/@by-group/%s" % by_group
        url += ".json"
        return url

    relationships = remote.Link(relationship_url, ApiListField('UserRelationship'))

    @property
    def id(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:user-50
        return self.atom_id.split('-', 1)[1]

    @property
    def permalink(self):
        ## TODO link to typepad profile?
        return self.uri

    @classmethod
    def getSelf(cls, **kwargs):
        return cls.get(urljoin(remote.BASE_URL, '/users/@self.json'), **kwargs)

class UserRelationship(RemoteObject):
    #status = fields.Something()
    source = fields.Object(User)
    target = fields.Object(User)

class PublicationStatus(RemoteObject):
    published = fields.Something()
    spam      = fields.Something()

class AssetRef(RemoteObject):
    ref  = fields.Something()
    href = fields.Something()
    type = fields.Something()

class Asset(RemoteObject):
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
    object_types = fields.List(fields.Something(), api_name='objectTypes')
    status       = fields.Object(PublicationStatus)
    links        = fields.List(fields.Something())
    in_reply_to  = fields.Object(AssetRef, api_name='inReplyTo')

    # astropad extras
    #authors      = fields.List(fields.Object(User))
    author       = fields.Object(User)

    # TODO make this clever again -- self._id is None for objects out of Lists
    #comments = ApiListLink('comments', 'Asset')
    comments = remote.Link(lambda o: '%sassets/%s/comments.json' % (remote.BASE_URL, o.assetid), ApiListField('Asset'))

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

class Event(RemoteObject):
    id     = fields.Something()
    verbs  = fields.List(fields.Something())
    # TODO: vary these based on verb content? oh boy
    actor  = fields.Object(User)
    object = fields.Object(Asset)

    @property
    def eventid(self):
        # yes, this is stupid, but damn it, I need this for urls
        # tag:typepad.com,2003:event-1680
        return self.id.split('-', 1)[1]

class Post(Asset):
    pass

class Group(RemoteObject):
    id           = fields.Something()
    display_name = fields.Something(api_name='displayName')
    tagline      = fields.Something()
    avatar       = fields.Something()
    urls         = fields.List(fields.Something())
    links        = fields.List(fields.Something())
    object_type  = fields.List(fields.Something(), api_name='objectType')

    users    = ApiListLink('users',         User)
    assets   = ApiListLink('assets',        Asset)
    events   = ApiListLink('events',        Event)
    comments = ApiListLink('comments',      Asset)
    posts    = ApiListLink('assets/@post',  Post)

    @property
    def groupid(self):
        return self.id.split('-', 1)[1]
