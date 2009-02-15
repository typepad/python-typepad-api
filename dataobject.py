import logging
import typepad.fields

class DataObjectMetaclass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}
        for name, field in attrs.iteritems():
            if isinstance(field, typepad.fields.Something):
                fields[name] = field
        for name in fields:
            del attrs[name]
        attrs['fields'] = fields
        return super(DataObjectMetaclass, cls).__new__(cls, name, bases, attrs)

class DataObject(object):
    __metaclass__ = DataObjectMetaclass

    def __init__(self, **kwargs):
        self._id = None
        self.parent = None
        self.__dict__.update(kwargs)

    def to_dict(self):
        data = {}
        for field_name, field in self.fields.iteritems():
            field.encode_into(self, data, field_name=field_name)
        return data

    @classmethod
    def from_dict(cls, data):
        self = cls()
        for field_name, field in cls.fields.iteritems():
            field.decode_into(data, self, field_name=field_name)
        return self
