#!/usr/bin/env python

from cStringIO import StringIO
import json
import logging
import re
import sys

import argparse


PREAMBLE = '''
# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""

The `typepad.api` module contains `TypePadObject` implementations of all the
content objects provided in the TypePad API.

"""

from urlparse import urljoin

from remoteobjects.dataobject import find_by_name

from typepad.tpobject import *
from typepad import fields
import typepad


'''

POSTAMBLE = """
browser_upload = BrowserUploadEndpoint()
"""

CLASS_HAS_OBJECT_TYPE = ('User', 'Group', 'Application', 'Asset', 'Comment', 'Favorite', 'Post', 'Photo', 'Audio', 'Video', 'Link', 'Document', )

CLASS_SUPERCLASSES = {
    'ImageLink': ('_ImageResizer',),
    'VideoLink': ('_VideoResizer',),
}

LINK_PROPERTY_FIXUPS = {
    'Asset': {
        'categories': {
            'name': 'categories_obj',
            'type': 'ListObject',
        },
    },
    'Relationship': {
        'status': {'name': 'status_obj'},
    },
}

PROPERTY_FIXUPS = {
    'Asset': {
        'published': {'type': 'datetime'},
        'categories': {
            'name': 'categories',
            'type': 'set<string>',
            'docString': """A list of categories (strings) associated with the asset.""",
        },
        'crosspostAccounts': {
            'name': 'crosspostAccounts',
            'type': 'set<string>',
            'docString': """A list of elsewhere account IDs to crosspost to.""",
        },
        'summary': {
            'name': 'summary',
            'type': 'string',
            'docString': """For a media type of `Asset`, the HTML description or caption given by its author.""",
        },
    },
    'Event': {
        'actor': {
            'name': 'actor',
            'type': 'User',
        },
        'published': {
            'name': 'published',
            'type': 'datetime',
        },
    },
    'Relationship': {
        'created': {
            'name': 'created',
            'type': 'map<datetime>',
        },
    },
    'User': {
        'email': {
            'name': 'email',
            'type': 'string',
        },
        'gender': {
            'name': 'gender',
            'type': 'string',
        },
    },
    'UserProfile': {
        'email': {
            'name': 'email',
            'type': 'string',
        },
        'gender': {
            'name': 'gender',
            'type': 'string',
        },
        'id': {
            'name': 'id',
            'type': 'string',
            'docString': """A URI that uniquely identifies the `User` associated with this `UserProfile`.""",
        },
        'urlId': {
            'name': 'urlId',
            'type': 'string',
            'docString': """An identifier for this `UserProfile` that can be used in URLs.

A user's `url_id` is unique only across groups in one TypePad
environment, so you should use `id`, not `url_id`, to associate data
with a `User` (or `UserProfile`). When constructing URLs to API resources
in one particular TypePad environment, however, use `url_id`.

"""
        },
    },
    'VideoLink': {
        'permalinkUrl': {
            'name': 'permalinkUrl',
            'type': 'string',
            'docString': """A URL to the HTML permalink page of the video.

Use this field to specify the video when posting a new `Video` asset.
When requesting an existing `Video` instance from the API,
`permalink_url` will be ``None``.

""",
        }
    },
}

CLASS_DOCSTRINGS = {
    'Account': """A user account on an external website.""",
    'Asset': """An item of content generated by a user.""",
    'AssetRef': """A structure that refers to an asset without including its full
    content.""",
    'AssetSource': """Information about an `Asset` instance imported from another service.""",
    'AudioLink': """A link to an audio recording.""",
    'Event': """An action that a user or group did.

    An event has an `actor`, which is the user or group that did the action; a
    set of `verbs` that describe what kind of action occured; and an `object`
    that is the object that the action was done to. In the current TypePad API
    implementation, only assets, users and groups can be the object of an
    event.

    """,
    'Favorite': """A favorite of some other asset.

    Asserts that the user_id and asset_id parameter match ^\w+$.""",
    'ImageLink': """A link to an image.

    Images hosted by TypePad can be resized with image sizing specs. See
    the `url_template` field and `at_size` method.

    """,
    'PublicationStatus': """A container for the flags that represent an asset's publication status.

    Publication status is currently represented by two flags: published and
    spam. The published flag is false when an asset is held for moderation,
    and can be set to true to publish the asset. The spam flag is true when
    TypePad's spam filter has determined that an asset is spam, or when the
    asset has been marked as spam by a moderator.

    """,
    'Relationship': """The unidirectional relationship between a pair of entities.

    A Relationship can be between a user and a user (a contact relationship),
    or a user and a group (a membership). In either case, the relationship's
    status shows *all* the unidirectional relationships between the source and
    target entities.

    """,
    'RelationshipStatus': """A representation of just the relationship types of a relationship,
    without the associated endpoints.""",
    'UserProfile': """Additional profile information about a TypePad user.

    This additional information is useful when showing information about a
    TypePad account directly, but is generally not required when linking to
    an ancillary TypePad account, such as the author of a post.

    """,
    'VideoLink': """A link to a web video.""",
    'Application': """An application that can authenticate to the TypePad API using OAuth.

    An application is identified by its OAuth consumer key, which in the case
    of a hosted group is the same as the identifier for the group itself.

    """,
    'Audio': """An entry in a blog.""",
    'Comment': """A text comment posted in reply to some other asset.""",
    'Group': """A group that users can join, and to which users can post assets.

    TypePad API social applications are represented as groups.

    """,
    'Link': """A shared link to some URL.""",
    'Photo': """An entry in a blog.""",
    'Post': """An entry in a blog.""",
    'User': """A TypePad user.

    This includes those who own TypePad blogs, those who use TypePad Connect
    and registered commenters who have either created a TypePad account or
    signed in with OpenID.

    """,
    'Video': """An entry in a blog.""",
}

CLASS_EXTRAS = {
    'ApiKey': '''
    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/api-keys/%s.json' % self.api_key)

    @classmethod
    def get_by_api_key(cls, api_key):
        """Returns an `ApiKey` instance with the given consumer key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        return cls.get('/api-keys/%s.json' % api_key)
''',
    'Asset': '''
    @property
    def actor(self):
        """This asset's author.

        This alias lets us use `Asset` instances interchangeably with `Event`
        instances in templates.
        """
        return self.author

    @property
    def asset_ref(self):
        """An `AssetRef` instance representing this asset."""
        return AssetRef(url_id=self.url_id,
                        ref=self.id,
                        author=self.author,
                        href='/assets/%s.json' % self.url_id,
                        type='application/json',
                        object_types=self.object_types)

    def __unicode__(self):
        return self.title or self.summary or self.content

    def primary_object_type(self):
        if not self.object_types: return None
        for object_type in self.object_types:
            return object_type
        return None
''',
    'AssetRef': '''
    def reclass_for_data(self, data):
        """Returns ``False``.

        This method prevents `AssetRef` instances from being reclassed when
        updated from a data dictionary based on the dictionary's
        ``objectTypes`` member.

        """
        # AssetRefs are for any object type, so don't reclass them.
        return False
''',
    'AuthToken': '''
    def make_self_link(self):
        # TODO: We don't have the API key, so we can't build a self link.
        return

    @classmethod
    def get_by_key_and_token(cls, api_key, auth_token):
        return cls.get('/auth-tokens/%s:%s.json' % (api_key, auth_token))
''',
    'Event': '''
    def __unicode__(self):
        return unicode(self.object)
''',
    'Favorite': '''
    @classmethod
    def get_by_user_asset(cls, user_id, asset_id, **kwargs):
        assert re.match('^\w+$', user_id), "invalid user_id parameter given"
        assert re.match('^\w+$', asset_id), "invalid asset_id parameter given"
        return cls.get('/favorites/%s:%s.json' % (asset_id, user_id),
            **kwargs)

    @classmethod
    def head_by_user_asset(cls, *args, **kwargs):
        fav = cls.get_by_user_asset(*args, **kwargs)
        return fav.head()
''',
    'ImageLink': '''
    @property
    def href(self):
        import logging
        logging.getLogger("typepad.api").warn(
            '%s.href is deprecated; use %s.url instead' % (self.__class__.__name__, self.__class__.__name__))
        return self.url
''',
    'Relationship': '''
    def _rel_type_updater(uri):
        def update(self):
            rel_status = RelationshipStatus.get(self.status_obj._location, batch=False)
            if uri:
                rel_status.types = [uri]
            else:
                rel_status.types = []
            rel_status.put()
        return update

    block = _rel_type_updater("tag:api.typepad.com,2009:Blocked")
    unblock = _rel_type_updater(None)
    leave = _rel_type_updater(None)

    def _rel_type_checker(uri):
        def has_edge_with_uri(self):
            return uri in self.status.types
        return has_edge_with_uri

    is_member = _rel_type_checker("tag:api.typepad.com,2009:Member")
    is_admin = _rel_type_checker("tag:api.typepad.com,2009:Admin")
    is_blocked = _rel_type_checker("tag:api.typepad.com,2009:Blocked")
''',
    'VideoLink': '''
    @property
    def html(self):
        import logging
        logging.getLogger("typepad.api").warn(
            '%s.html is deprecated; use %s.embed_code instead' % (self.__class__.__name__, self.__class__.__name__))
        return self.embed_code
''',
    'Application': '''
    @classmethod
    def get_by_api_key(cls, api_key, **kwargs):
        """Returns an `Application` instance by the API key.

        Asserts that the api_key parameter matches ^\w+$."""
        assert re.match('^\w+$', api_key), "invalid api_key parameter given"
        import logging
        logging.getLogger("typepad.api").warn(
            '%s.get_by_api_key is deprecated' % cls.__name__)
        return cls.get('/applications/%s.json' % api_key, **kwargs)

    @property
    def browser_upload_endpoint(self):
        """The endpoint to use for uploading file assets directly to
        TypePad."""
        return urljoin(typepad.client.endpoint, '/browser-upload.json')

    @property
    def user_flyouts_script(self):
        import logging
        logging.getLogger("typepad.api").warn(
            '%s.user_flyouts_script is deprecated; use %s.user_flyouts_script_url instead' % (self.__class__.__name__, self.__class__.__name__))
        return self.user_flyouts_script_url
''',
    'User': '''
    @classmethod
    def get_self(cls, **kwargs):
        """Returns a `User` instance representing the account as whom the
        client library is authenticating."""
        return cls.get('/users/@self.json', **kwargs)
''',
    'UserProfile': '''
    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/users/%s/profile.json' % self.url_id)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        """Returns the `UserProfile` instance with the given URL identifier."""
        prof = cls.get('/users/%s/profile.json' % url_id, **kwargs)
        prof.__dict__['url_id'] = url_id
        return prof

    @property
    def user(self):
        """Returns a `User` instance for the TypePad member whose
        `UserProfile` this is."""
        return find_by_name('User').get_by_url_id(self.url_id)
''',
}


class lazy(object):

    def __init__(self, data=None):
        if data is not None:
            self.fill(data)

    def __eq__(self, fld):
        return self.__dict__ == fld.__dict__

    def fill(self, data):
        for key, val in data.iteritems():
            if isinstance(key, unicode):
                key = key.encode('utf-8')
            if isinstance(val, unicode):
                val = val.encode('utf-8')
            setattr(self, key, val)


class Field(lazy):

    def __init__(self, data=None):
        self.args = list()
        self.kwargs = dict()
        super(Field, self).__init__(data)

    @property
    def type(self):
        return self.__dict__['type']

    @type.setter
    def type(self, val):
        self.__dict__['type'] = val

        mo = re.match(r'(\w+)<([^>]+)>', val)
        if mo is not None:
            container, subtype = mo.groups((1, 2))

            if container in ('set', 'array'):
                self.field_type = 'fields.List'
            elif container == 'map':
                self.field_type = 'fields.Dict'
            else:
                raise ValueError('Unknown container type %r' % container)

            subfield = Field({'type': subtype})
            self.args.append(subfield)

            return

        if val in ('string', 'boolean', 'integer'):
            self.field_type = 'fields.Field'
        elif val == 'datetime':
            self.field_type = 'fields.Datetime'
        else:
            self.field_type = 'fields.Object'
            if val == 'Base':
                val = 'TypePadObject'
            self.args.append(val)

    def __str__(self):
        me = StringIO()
        if not hasattr(self, 'field_type'):
            raise ValueError("Uh this Field doesn't have a field type? (%r)" % self.__dict__)
        me.write(self.field_type)
        me.write("""(""")
        if self.args:
            me.write(', '.join(str(arg) if isinstance(arg, Field) else repr(arg) for arg in self.args))
        if self.kwargs:
            if self.args:
                me.write(', ')
            me.write(', '.join('%s=%r' % (k, v) for k, v in self.kwargs.items()))
        me.write(""")""")
        return me.getvalue()


class ObjectRef(Field):

    @property
    def type(self):
        return self.__dict__['type']

    @type.setter
    def type(self, val):
        self.__dict__['type'] = val

        mo = re.match(r'(\w+)<([^>]+)>', val)
        if mo is not None:
            container, subtype = mo.groups((1, 2))

            if container in ('List', 'Stream'):
                self.field_type = 'ListOf'
                self.args.append(subtype)
                return

            raise ValueError('Unknown container type %r' % container)

        self.field_type = val

    def __str__(self):
        if len(self.args):
            return super(ObjectRef, self).__str__()
        if self.field_type == 'ListObject':
            return self.field_type
        return repr(self.field_type)


class Property(lazy):

    def __init__(self, data):
        self.field = Field()
        super(Property, self).__init__(data)

    @property
    def name(self):
        return self.__dict__['name']

    @name.setter
    def name(self, name):
        py_name = name.replace('URL', 'Url')
        py_name = re.sub(r'[A-Z]', lambda mo: '_' + mo.group(0).lower(), py_name)
        py_name = py_name.replace('-', '_')
        if py_name != name:
            self.field.kwargs['api_name'] = name
        self.__dict__['name'] = py_name

    @property
    def type(self):
        return self.__dict__['type']

    @type.setter
    def type(self, val):
        self.__dict__['type'] = val
        self.field.type = val

    def __str__(self):
        me = StringIO()
        me.write(self.name)
        me.write(" = ")
        me.write(str(self.field))
        me.write("\n")
        if hasattr(self, 'docString'):
            me.write('"""%s"""\n' % self.docString)
        return me.getvalue()


class ObjectType(lazy):

    types_by_name = dict()

    @property
    def name(self):
        return self.__dict__['name']

    @name.setter
    def name(self, val):
        assert 'name' not in self.__dict__
        self.__dict__['name'] = val
        self.types_by_name[val] = self

    @property
    def properties(self):
        return self.__dict__['properties']

    @properties.setter
    def properties(self, val):
        # Keep a clean copy safe for referring to later.
        self.__dict__['property_data'] = dict((prop['name'], dict(prop)) for prop in val)
        # Now make val a dict for working with now.
        val = dict((prop['name'], prop) for prop in val)

        # Filter our inheritance out before overriding types, so we don't have to
        # override all the inherited types too.
        if self.parentType != 'TypePadObject':
            parenttype = self.types_by_name[self.parentType]
            for propname, propdata in val.items():
                if propdata == parenttype.property_data.get(propname):
                    # INHERITED
                    logging.debug("YAY %s.%s is the same as %s.%s, so we can skip it", self.name, propname, self.parentType, propname)
                    del val[propname]
                else:
                    logging.debug("Oops, %s.%s is not the same as %s.%s (%r), i guess", self.name, propname, self.parentType, propname, parenttype.property_data.get(propname))

        if self.name in PROPERTY_FIXUPS:
            fixups = PROPERTY_FIXUPS[self.name]
            for fixie_name, fixie in fixups.items():
                try:
                    val[fixie_name].update(fixie)
                except KeyError:
                    if 'name' not in fixie:
                        raise ValueError("Wanted to add fixed-up property %s.%s, but it has no 'name' (and I'm not going to assume it's %r)"
                            % (self.name, fixie_name, fixie_name))
                    val[fixie_name] = dict(fixie)

        props = [Property(data) for data in val.values()]
        props = dict((prop.name, prop) for prop in props)
        self.__dict__['properties'] = props

    @property
    def parents(self):
        parents = [self.parentType]
        if self.name in CLASS_SUPERCLASSES:
            parents.extend(CLASS_SUPERCLASSES[self.name])
        return ', '.join(parents)

    @property
    def has_get_by_url_id(self):
        if 'url_id' in self.properties:
            return True
        if self.parentType == 'TypePadObject':
            return False
        return self.types_by_name[self.parentType].has_get_by_url_id

    @property
    def endpoint(self):
        return self.__dict__['endpoint']

    @endpoint.setter
    def endpoint(self, val):
        self.__dict__['endpoint'] = val
        self.endpoint_name = val['name']

        assert 'properties' in self.__dict__
        logging.debug('Object %s has properties %r', self.name, self.__dict__['properties'].keys())

        for endp in val['propertyEndpoints']:
            name = endp['name']

            try:
                value_type = LINK_PROPERTY_FIXUPS[self.name][name]['type']
            except KeyError:
                try:
                    value_type = endp['resourceObjectType']['name']
                except KeyError:
                    logging.info('Skipping endpoint %s.%s since it has no resourceObjectType', self.endpoint_name, name)
                    continue
            else:
                logging.info("Used property override for %s.%s property", self.name, name)

            docstrings = sorted(endp['supportedMethods'].items(), key=lambda x: x[0])
            docstrings = [desc if method == 'GET' else '%s: %s' % (method, desc) for method, desc in docstrings if desc]
            docstring = '\n\n'.join(docstrings)

            prop = Property({'name': name})
            if docstring:
                prop.docString = docstring
            prop.field.field_type = 'fields.Link'
            subfield = ObjectRef({'type': value_type})
            prop.field.args.append(subfield)

            if prop.name in self.properties:
                try:
                    new_name = LINK_PROPERTY_FIXUPS[self.name][prop.name]['name']
                except KeyError:
                    raise ValueError("Oops, wanted to add a Link property called %s to %s, but there's already a property "
                        "named that (%r)" % (prop.name, self.name, str(self.properties[prop.name])))

                logging.info("Used property name override to rename %s.%s as %r", self.name, endp['name'], name)
                if 'api_name' not in prop.field.kwargs:
                    prop.field.kwargs['api_name'] = prop.name
                prop.name = new_name

            logging.debug('Adding Link property %s.%s', self.name, prop.name)
            self.properties[prop.name] = prop

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, self.name)

    def __str__(self):
        me = StringIO()

        if self.name in CLASS_DOCSTRINGS:
            me.write('    """')
            me.write(CLASS_DOCSTRINGS[self.name])
            me.write('"""\n\n')

        if self.name in CLASS_HAS_OBJECT_TYPE:
            me.write("""    _class_object_type = "%s"\n\n""" % self.name)

        for name, prop in sorted(self.properties.items(), key=lambda x: x[0]):
            prop_text = str(prop)
            prop_text = re.sub(r'(?xms)^(?=[^\n])', '    ', prop_text)
            me.write(prop_text)

        if hasattr(self, 'endpoint_name') and self.has_get_by_url_id:
            me.write("""
    def make_self_link(self):
        return urljoin(typepad.client.endpoint, '/%(endpoint_name)s/%%s.json' %% self.url_id)

    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        obj = cls.get('/%(endpoint_name)s/%%s.json' %% url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        obj.__dict__['id'] = 'tag:api.typepad.com,2009:%%s' %% url_id
        return obj
""" % {'endpoint_name': self.endpoint_name})

        if self.name in CLASS_EXTRAS:
            me.write(CLASS_EXTRAS[self.name])

        body = me.getvalue()
        if not len(body):
            body = "    pass\n"
        return """class %s(%s):\n\n%s\n\n""" % (self.name, self.parents, body)


def generate_types(types_fn, nouns_fn, out_fn):
    with open(types_fn) as f:
        types = json.load(f)
    with open(nouns_fn) as f:
        nouns = json.load(f)

    objtypes = set()
    objtypes_by_name = dict()
    typedata = dict((d['name'], d) for d in types['entries'])
    while typedata:
        for name, info in typedata.items():
            if name == 'Base':
                logging.info('Skipping Base type, since we use TypePadObject for that')
                del typedata[name]
                continue

            # Fix up Relationship to have a parentType.
            if name == 'Relationship':
                info['parentType'] = 'Base'

            if 'parentType' not in info:
                raise ValueError('Type info for %r has no parentType?' % name)
            if info['parentType'] == 'Base':
                info['parentType'] = u'TypePadObject'
            elif info['parentType'] not in objtypes_by_name:
                logging.debug("Skipping %s until the next round, since %s I haven't seen %s yet", name, info['parentType'])
                continue

            del typedata[name]
            objtype = ObjectType(info)
            objtypes.add(objtype)
            objtypes_by_name[objtype.name] = objtype

    # Annotate the types with endpoint info.
    for endpoint in nouns['entries']:
        # Fix up blogs.comments to have a resource type.
        if endpoint['name'] == 'blogs':
            for propendp in endpoint['propertyEndpoints']:
                if propendp.get('name') == 'comments':
                    propendp['resourceObjectType'] = {
                        'name': 'List<Comment>',
                    }
                    break
        # Fix up relationships to have a correct object type.
        elif endpoint['name'] == 'relationships':
            endpoint['resourceObjectType']['name'] = 'Relationship'
        # Fix up groups to have an audio-assets property endpoint.
        elif endpoint['name'] == 'groups':
            endpoint['propertyEndpoints'].append({
                'name': 'audio-assets',
                'resourceObjectType': {
                    'name': 'List<Audio>',
                },
                'supportedMethods': {
                    'GET': "",
                    'POST': "",
                },
            })

        try:
            objtype = objtypes_by_name[endpoint['resourceObjectType']['name']]
        except KeyError:
            pass
        else:
            objtype.endpoint = endpoint

    wrote = set(('TypePadObject',))
    wrote_one = True
    with open(out_fn, 'w') as outfile:
        outfile.write(PREAMBLE.replace('\n', '', 1))

        while objtypes and wrote_one:
            eligible_types = list()
            for objtype in list(objtypes):
                if objtype.parentType not in wrote:
                    logging.debug("Oops, can't write %s as I haven't written %s yet", objtype.name, objtype.parentType)
                    continue
                logging.debug("Yay, I can write out %s!", objtype.name)
                eligible_types.append(objtype)

            if not eligible_types:
                wrote_one = False
                break

            for objtype in sorted(eligible_types, key=lambda x: x.name):
                outfile.write(str(objtype))
                wrote.add(objtype.name)
                objtypes.remove(objtype)

        if not wrote_one:
            raise ValueError("Ran out of types to write (left: %s)" %
                ', '.join(('%s(%s)' % (t.name, t.parentType) for t in objtypes)))

        outfile.write(POSTAMBLE.replace('\n', '', 1))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    class Add(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            val = getattr(namespace, self.dest, self.default)
            setattr(namespace, self.dest, val + 1)

    class Subt(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            val = getattr(namespace, self.dest, self.default)
            setattr(namespace, self.dest, val - 1)

    parser = argparse.ArgumentParser(
        description='generate a TypePad client library from json endpoints')
    parser.add_argument('--types', metavar='file', help='parse file for object type info')
    parser.add_argument('--nouns', metavar='file', help='parse file for noun endpoint info')
    parser.add_argument('-v', action=Add, nargs=0, dest='verbose', default=2, help='be more verbose')
    parser.add_argument('-q', action=Subt, nargs=0, dest='verbose', help='be less verbose')
    parser.add_argument('outfile', help='file to write library to')
    ohyeah = parser.parse_args(argv)

    log_level = ohyeah.verbose
    log_level = 0 if log_level < 0 else log_level if log_level <= 4 else 4
    log_level = list(reversed([logging.DEBUG, logging.INFO, logging.WARN, logging.ERROR, logging.CRITICAL]))[log_level]
    logging.basicConfig(level=log_level)
    logging.info('Log level set to %s', logging.getLevelName(log_level))

    generate_types(ohyeah.types, ohyeah.nouns, ohyeah.outfile)

    return 0


if __name__ == '__main__':
    sys.exit(main())
