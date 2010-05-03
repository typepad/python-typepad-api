#!/usr/bin/env python

from cStringIO import StringIO
import json
import logging
import re
import sys

import argparse


PREAMBLE = """
from typepad.tpobject import *
from typepad import fields
import typepad

"""

POSTAMBLE = """"""

HAS_OBJECT_TYPE = ('User', 'Group', 'Application', 'Asset', 'Comment', 'Favorite', 'Post', 'Photo', 'Audio', 'Video', 'Link', 'Document', )


class lazy(object):

    def __init__(self, data=None):
        if data is not None:
            self.fill(data)

    def fill(self, data):
        for key, val in data.iteritems():
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

            if container in ('List', 'Stream'):
                self.field_type = 'ListOf'
                self.args.append(subtype)
                return

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
        else:
            self.field_type = 'fields.Object'
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


class Property(lazy):

    def __init__(self, data):
        self.field = Field()
        super(Property, self).__init__(data)

    @property
    def name(self):
        return self.__dict__['name']

    @name.setter
    def name(self, name):
        py_name = re.sub(r'[A-Z]', lambda mo: '_' + mo.group(0).lower(), name)
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

    @property
    def properties(self):
        return self.__dict__['properties']

    @properties.setter
    def properties(self, val):
        self.__dict__['properties'] = dict((prop.name, prop) for prop in (Property(data) for data in val))

    @property
    def parentType(self):
        if self.name == 'Base':
            return 'TypePadObject'
        return self.__dict__['parentType']

    @parentType.setter
    def parentType(self, val):
        self.__dict__['parentType'] = val

    @property
    def endpoint(self):
        return self.__dict__['endpoint']

    @endpoint.setter
    def endpoint(self, val):
        self.__dict__['endpoint'] = val
        self.endpoint_name = val['name']

        assert 'properties' in self.__dict__

        for endp in val['propertyEndpoints']:
            name = endp['name']
            # TODO: handle endpoints like Blog.comments that aren't usable without filters
            try:
                value_type = endp['resourceObjectType']
            except KeyError:
                continue
            # TODO: docstring?
            prop = Property({'name': name})
            prop.field.field_type = 'fields.Link'
            if 'resourceObjectType' not in endp:
                raise ValueError("Uh %r doesn't have a resourceObjectType? (%r)" % (name, endp))
            subfield = Field({'type': value_type['name']})
            prop.field.args.append(subfield)
            self.properties[prop.name] = prop

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, self.name)

    def __str__(self):
        me = StringIO()
        me.write("""class %s(%s):\n\n""" % (self.name, self.parentType))
        if self.name in HAS_OBJECT_TYPE:
            me.write("""    object_type = "tag:api.typepad.com,2009:%s"\n\n""" % self.name)
        elif not self.properties:
            me.write("    pass\n")
        for prop in self.properties.values():
            prop_text = str(prop)
            prop_text = re.sub(r'(?xms)^(?=.)', '    ', prop_text)
            me.write(prop_text)

        if hasattr(self, 'endpoint_name') and 'url_id' in self.properties:
            me.write("""
    @classmethod
    def get_by_url_id(cls, url_id, **kwargs):
        obj = cls.get('/%s/%%s.json' %% url_id, **kwargs)
        obj.__dict__['url_id'] = url_id
        return obj
""" % self.endpoint_name)

        me.write("\n\n")
        return me.getvalue()


def generate_types(types_fn, nouns_fn, out_fn):
    with open(types_fn) as f:
        types = json.load(f)
    with open(nouns_fn) as f:
        nouns = json.load(f)

    objtypes = set()
    objtypes_by_name = dict()
    for info in types['entries']:
        objtype = ObjectType(info)
        objtypes.add(objtype)
        objtypes_by_name[objtype.name] = objtype

    for endpoint in nouns['entries']:
        try:
            objtype = objtypes_by_name[endpoint['resourceObjectType']['name']]
        except KeyError:
            pass
        else:
            objtype.endpoint = endpoint

    wrote = set(('TypePadObject',))
    wrote_one = True
    with open(out_fn, 'w') as outfile:
        outfile.write(PREAMBLE)

        while objtypes and wrote_one:
            wrote_one = False
            for objtype in list(objtypes):
                if objtype.parentType not in wrote:
                    logging.debug("Oops, can't write %s as I haven't written %s yet", objtype.name, objtype.parentType)
                    continue

                wrote_one = True
                outfile.write(str(objtype))
                wrote.add(objtype.name)
                objtypes.remove(objtype)

        if not wrote_one:
            raise ValueError("Ran out of types to write (left: %s)" %
                ', '.join(('%s(%s)' % (t.name, t.parentType) for t in objtypes)))

        outfile.write(POSTAMBLE)


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
