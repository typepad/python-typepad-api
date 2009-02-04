# TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
import simplejson
import logging
from datetime import datetime
import time

class DataObject(object):
    fields = {}

    def __init__(self, **kwargs):
        self._id = None
        self.parent = None
        self.update(**kwargs)

    def update(self, **kwargs):
        for field_name, field_class in self.fields.iteritems():
            value = kwargs.get(field_name)
            # TODO: reuse child objects as appropriate
            if isinstance(value, list) or isinstance(value, tuple):
                new_value = []
                for item in value:
                    o = field_class(**item)
                    o.parent = self
                    new_value.append(o)
                value = new_value
            elif isinstance(value, dict):
                value = field_class(**value)
                value.parent = self # e.g. reference to blog from entry
            elif field_class is datetime:
                if value is not None:
                    value = datetime(*(time.strptime(value, '%Y-%m-%dT%H:%M:%SZ'))[0:6])
            setattr(self, field_name, value)

    def serialize_value(self, value):
        if isinstance(value, DataObject):
            value = value.to_dict()
        elif isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, dict):
            pass
        elif isinstance(value, list):
            newlist = []
            for x in value:
                newlist.append(self.serialize_value(x))
            value = newlist
        elif not isinstance(value, basestring):
            value = str(value)
        return value

    def to_dict(self):
        data = {}
        for field_name, field_class in self.fields.iteritems():
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = self.serialize_value(value)
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
