# TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
import simplejson
import logging
from datetime import datetime
import time

__all__ = ('Something', 'List', 'Object', 'Datetime')


class Something(object):
    def decode(self, value):
        return value

    def encode(self, value):
        return value

class List(Something):
    def __init__(self, fld):
        self.fld = fld

    def decode(self, value):
        return [self.fld.decode(v) for v in value]

    def encode(self, value):
        return [self.fld.encode(v) for v in value]

class Object(Something):
    def __init__(self, cls):
        self.cls = cls

    def decode(self, value):
        if not isinstance(value, dict):
            raise TypeError('Value to decode %r is not a dict' % (value,))
        return self.cls.from_dict(value)

    def encode(self, value):
        if not isinstance(value, self.cls):
            raise TypeError('Value to encode %r is not a %s' % (value, self.cls.__name__))
        return value.to_dict()

class Datetime(Something):
    def decode(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        if value.tzinfo is not None:
            raise TypeError("Value to encode %r is a datetime, but it has timezone information and we don't want to deal with timezone information" % (value,))
        return '%sZ' % (value.isoformat(),)

