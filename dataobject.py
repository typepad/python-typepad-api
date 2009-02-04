# TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
import simplejson
import logging
from datetime import datetime
import time

__all__ = ('Field', 'SetField', 'ObjectField', 'DatetimeField', 'DataObject')


class Field(object):
    def decode(self, value):
        return value

    def encode(self, value):
        return value

class SetField(Field):
    def __init__(self, fld):
        self.fld = fld

    def decode(self, value):
        return [self.fld.decode(v) for v in value]

    def encode(self, value):
        return [self.fld.encode(v) for v in value]

class ObjectField(Field):
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

class DatetimeField(Field):
    def decode(self, value):
        try:
            return datetime(*(time.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))[0:6])
        except ValueError:
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        return value.isoformat()


class DataObject(object):
    fields = {}

    def __init__(self, **kwargs):
        self._id = None
        self.parent = None
        self.__dict__.update(kwargs)

    def to_dict(self):
        data = {}
        for field_name, field in self.fields.iteritems():
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = field.encode(value)
        return data

    @classmethod
    def from_dict(cls, data):
        self = cls()
        for field_name, field in cls.fields.iteritems():
            value = data.get(field_name)
            if value is not None:
                value = field.decode(value)
            setattr(self, field_name, value)
        return self
