import logging

import remoteobjects.dataobject
import remoteobjects.fields
from remoteobjects.fields import *


class Link(remoteobjects.fields.Link):

    """A `TypePadObject` property representing a link from one TypePad API
    object to another.

    This `Link` works like `remoteobjects.fields.Link`, but builds links using
    the TypePad API URL scheme. That is, a `Link` on ``/asset/1.json`` called
    ``events`` links to ``/asset/1/events.json``.

    """

    def __get__(self, instance, owner):
        """Generates the `TypePadObject` representing the target of this
        `Link` object.

        This `__get__()` implementation implements the ``../x/target.json`` style
        URLs used in the TypePad API.

        """
        try:
            if instance._location is None:
                raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (type(self).__name__, owner.__name__))

            assert instance._location.endswith('.json')
            newurl = instance._location[:-5]
            newurl += '/' + self.api_name
            newurl += '.json'

            ret = self.cls.get(newurl)
            ret.of_cls = self.of_cls
            return ret
        except Exception, e:
            logging.error(str(e))
            raise


class Object(remoteobjects.fields.Object):

    """A field representing a nested `TypePadObject`.

    This `Object` field class honors a `TypePadObject` structure's
    `objectTypes` member when decoding an object, only using the specified
    class if the dictionary to decode has no ``objectTypes`` in it or the
    ``objectTypes`` specifies an unknown type.

    """

    def __init__(self, cls=None, **kwargs):
        """Configures this `Object` field.

        Optional parameter `cls` specifies the `TypePadObject` class to use if
        the value to decode has no ``objectTypes`` member.

        """
        super(Object, self).__init__(cls, **kwargs)

    def decode(self, value):
        """Decodes the given dictionary into a GTypePadObject` instance.

        If the `value` dictionary contains an ``objectTypes`` value that matches
        a known `TypePadObject` class, an instance of that class is returned.
        Otherwise, an instance of the `Object` field's default class is
        returned.

        If a class cannot be inferred and no default is specified, a
        `ValueError` is raised.

        """
        try:
            # Decide what type this should be.
            objtype = value['objectTypes'][0]

            # TODO: looking up by objectTypes constants would be nice
            # instead of assuming the URI matches the class name
            assert objtype.startswith('tag:api.typepad.com,2009:')
            objtype = objtype[25:]

            objcls = remoteobjects.dataobject.find_by_name(objtype)
            return objcls.from_dict(value)
        except (IndexError, TypeError, KeyError, AssertionError):
            # Fall back to superimplementation.
            pass

        if self.cls is None:
            raise ValueError('Object field %r cannot decode a dictionary without an objectTypes field or an explicit object class'
                % self)

        return super(Object, self).decode(value)
