#!/usr/bin/env python

from cStringIO import StringIO
import json
import logging
import re
import sys

import argparse


class lazy(object):

    def __init__(self, data):
        self.fill(data)

    def fill(self, data):
        for key, val in data.iteritems():
            setattr(self, key, val)


class Property(lazy):

    def __init__(self, data):
        self.args = list()
        self.kwargs = dict()
        super(Property, self).__init__(data)

    @property
    def name(self):
        return self.__dict__['name']

    @name.setter
    def name(self, name):
        py_name = re.sub(r'[A-Z]', lambda mo: '_' + mo.group(0).lower(), name)
        if py_name != name:
            self.kwargs['api_name'] = name
        self.__dict__['name'] = py_name

    @property
    def type(self):
        return self.__dict__['type']

    @type.setter
    def type(self, val):
        self.__dict__['type'] = val
        if val in ('string', 'boolean', 'integer'):
            self.field_type = 'fields.Field'
        else:
            self.field_type = 'fields.Object'
            self.args.append(val)

    def __str__(self):
        me = StringIO()
        me.write("""%s = %s(""" % (self.name, self.field_type))
        if self.args:
            me.write(', '.join(repr(arg) for arg in self.args))
        if self.kwargs:
            if self.args:
                me.write(', ')
            me.write(', '.join('%s=%r' % (k, v) for k, v in self.kwargs.items()))
        me.write(""")\n""")
        me.write('"""%s"""\n' % self.docString)
        return me.getvalue()


class ObjectType(lazy):

    @property
    def properties(self):
        return self.__dict__.get('properties', list())

    @properties.setter
    def properties(self, val):
        self.__dict__['properties'] = [Property(data) for data in val]

    @property
    def parentType(self):
        if self.name == 'Base':
            return 'RemoteObject'
        return self.__dict__['parentType']

    @parentType.setter
    def parentType(self, val):
        self.__dict__['parentType'] = val

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, self.name)

    def __str__(self):
        me = StringIO()
        me.write("""class %s(%s):\n""" % (self.name, self.parentType))
        if not self.properties:
            me.write("    pass\n")
        for prop in self.properties:
            prop_text = str(prop)
            prop_text = re.sub(r'(?xms)^(?=.)', '    ', prop_text)
            me.write(prop_text)
        me.write("\n\n")
        return me.getvalue()


def generate_types(fn, out_fn):
    with open(fn) as f:
        types = json.load(f)

    objtypes = set()
    for objtype in types['entries']:
        objtypes.add(ObjectType(objtype))

    wrote = set(('RemoteObject',))
    wrote_one = True
    with open(out_fn, 'w') as outfile:
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

    generate_types(ohyeah.types, ohyeah.outfile)

    return 0


if __name__ == '__main__':
    sys.exit(main())
