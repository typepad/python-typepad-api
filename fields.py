import logging

import remoteobjects.fields
from remoteobjects.fields import *

class Link(remoteobjects.fields.Link):
    def __get__(self, instance, owner):
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
