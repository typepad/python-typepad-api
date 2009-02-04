import logging

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
