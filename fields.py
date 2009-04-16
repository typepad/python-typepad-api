import logging

import remoteobjects.dataobject
import remoteobjects.fields
from remoteobjects.fields import *
import typepad.tpobject


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
