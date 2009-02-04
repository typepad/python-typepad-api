# TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
import simplejson
import logging
from datetime import datetime
import time

__all__ = ('Field', 'SetField', 'ObjectField', 'StringField', 'IntField', 'DatetimeField', 'DataObject')


class Field(object):
    def decode(self, value):
        raise NotImplementedError('Decoding is not generically implemented')

    def encode(self, value):
        raise NotImplementedError('Encoding is not generically implemented')

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
            raise ValueError('HMM THIS VALUE IS A %s (%r)' % (type(value), value))
        return self.cls.from_dict(value)

    def encode(self, value):
        assert isinstance(value, self.cls)
        return value.to_dict()

class StringField(Field):
    def decode(self, value):
        assert isinstance(value, basestring)
        return value

    def encode(self, value):
        assert isinstance(value, basestring)
        return value

class IntField(Field):
    def decode(self, value):
        assert isinstance(value, int)
        return value

    def encode(self, value):
        assert isinstance(value, int)
        return value

class DatetimeField(Field):
    def decode(self, value):
        return datetime(*(time.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))[0:6])

    def encode(self, value):
        assert isinstance(value, datetime)
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
