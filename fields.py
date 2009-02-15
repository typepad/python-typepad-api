# TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
import simplejson
import logging
from datetime import datetime
import time

__all__ = ('Something', 'List', 'Object', 'Datetime')


class Something(object):
    def __init__(self, api_name=None, default=None):
        self.api_name = api_name
        self.default  = default

    def decode(self, value):
        return value

    def encode(self, value):
        return value

    def encode_into(self, obj, data, field_name=None):
        value = getattr(obj, field_name)
        if value is not None:
            value = self.encode(value)
            # only put in data if defined
            data[self.api_name or field_name] = value

    def decode_into(self, data, obj, field_name=None):
        value = data.get(self.api_name or field_name)
        if value is not None:
            value = self.decode(value)
        if value is None and self.default is not None:
            if callable(self.default):
                value = self.default(obj, data)
            else:
                value = self.default
        # always set the attribute, even if it's still None
        setattr(obj, field_name, value)

class List(Something):
    def __init__(self, fld, **kwargs):
        super(List, self).__init__(**kwargs)
        self.fld = fld

    def decode(self, value):
        return [self.fld.decode(v) for v in value]

    def encode(self, value):
        return [self.fld.encode(v) for v in value]

class Object(Something):
    def __init__(self, cls, **kwargs):
        super(Object, self).__init__(**kwargs)
        self.cls = cls

    def decode(self, value):
        if not isinstance(value, dict):
            raise TypeError('Value to decode into a %s %r is not a dict' % (self.cls.__name__, value))
        return self.cls.from_dict(value)

    def encode(self, value):
        if not isinstance(value, self.cls):
            raise TypeError('Value to encode %r is not a %s' % (value, self.cls.__name__))
        return value.to_dict()

class Datetime(Something):
    def decode(self, value):
        try:
            return datetime(*(time.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))[0:6])
        except ValueError:
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        if value.tzinfo is not None:
            raise TypeError("Value to encode %r is a datetime, but it has timezone information and we don't want to deal with timezone information" % (value,))
        return '%sZ' % (value.isoformat(),)

