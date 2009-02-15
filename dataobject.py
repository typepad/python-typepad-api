import logging
import typepad.fields

all_classes = {}
def find_by_name(name):
    return all_classes[name]

class DataObjectMetaclass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}

        # Inherit all the parent DataObject classes' fields.
        for base in bases:
            if isinstance(base, DataObjectMetaclass):
                fields.update(base.fields)

        # Move all the class's attributes that are Fields to the fields set.
        for attrname, field in attrs.items():
            if isinstance(field, typepad.fields.Something):
                fields[attrname] = field
                del attrs[attrname]

        attrs['fields'] = fields
        obj_cls = super(DataObjectMetaclass, cls).__new__(cls, name, bases, attrs)

        # Register the class so Object fields can have forward-referenced it.
        all_classes['.'.join((obj_cls.__module__, name))] = obj_cls
        # Tell the fields this class so they can find their forward references.
        for field in fields.values():
            field.of_cls = obj_cls

        return obj_cls

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
