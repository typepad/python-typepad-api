# Copyright (c) 2009-2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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

    def __get__(self, instance, type=None, **kwargs):
        """Generates the `TypePadObject` representing the target of this
        `Link` object.

        This `__get__()` implementation implements the ``../x/target.json`` style
        URLs used in the TypePad API.

        """
        if instance is None:
            return self

        try:
            if instance._location is None:
                raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (type(self).__name__, owner.__name__))

            assert instance._location.endswith('.json')
            newurl = instance._location[:-5]
            newurl += '/' + self.api_name
            newurl += '.json'

            ret = self.cls.get(newurl, **kwargs)
            return ret
        except Exception, e:
            logging.error(str(e))
            raise
