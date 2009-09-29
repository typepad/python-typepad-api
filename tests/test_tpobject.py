# Copyright (c) 2009 Six Apart Ltd.
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

try:
    import json
except ImportError:
    import simplejson as json

import logging
import random
import sys
import unittest
import traceback

import typepad
from tests import utils


class TestObjects(unittest.TestCase):

    @utils.todo
    def testRelativeUrls(self):
        raise NotImplementedError()

    @utils.todo
    def testBatchEnforcement(self):
        raise NotImplementedError()

    def testListOf(self):
        x = typepad.ListOf('User')
        self.assert_(isinstance(x, type))
        self.assert_(issubclass(x, typepad.ListObject))
        self.assert_(issubclass(x, typepad.SequenceProxy))
        self.assertEquals(x.__name__, 'ListOfUser')

        y = typepad.ListOf('User')
        logging.critical('%r %s is %r %s?', x, id(x), y, id(y))
        self.assert_(x is y, "two ListOf's the same thing are not only "
                             "equivalent but the same instance")

    def testLinks(self):

        replies = {
            'href':  'http://127.0.0.1:8000/assets/1/comments.json',
            'type':  'application/json',
            'rel':   'replies',
            'total': 4,
        }
        enclosure = {
            'href':   'http://127.0.0.1:8000/uploads/1/1.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  480,
            'height': 320
        }
        enclosure_2 = {
            'href':   'http://127.0.0.1:8000/uploads/1/170.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  480,
            'height': 320
        }
        largest = {
            'rel':    'avatar',
            'href':   'http://127.0.0.1:8000/avatars/largest.gif',
            'type':   'image/gif',
            'width':  500,
            'height': 500
        }
        smallest = {
            'rel':   'avatar',
            'href':   'http://127.0.0.1:8000/avatars/smallest.gif',
            'type':   'image/gif',
            'width':  25,
            'height': 25,
        }
        medium = {
            'rel':    'avatar',
            'href':   'http://127.0.0.1:8000/avatars/medium.gif',
            'type':   'image/gif',
            'width':  100,
            'height': 100,
        }

        ls = typepad.LinkSet.from_dict([ replies, enclosure, enclosure_2,
            largest, smallest, medium ])

        replies     = typepad.Link.from_dict(replies)
        enclosure   = typepad.Link.from_dict(enclosure)
        enclosure_2 = typepad.Link.from_dict(enclosure_2)
        largest     = typepad.Link.from_dict(largest)
        smallest    = typepad.Link.from_dict(smallest)
        medium      = typepad.Link.from_dict(medium)

        self.assert_(isinstance(ls, typepad.LinkSet))
        self.assertEquals(len(ls), 6)

        self.assertEquals(ls['replies'], replies)
        self.assert_(ls['enclosure'] in (enclosure, enclosure_2))
        self.assertEquals(list(ls['rel__replies']), [ replies ])
        enclosures = sorted(list(ls['rel__enclosure']), key=lambda x: x.href)
        self.assertEquals(enclosures, [ enclosure, enclosure_2 ])
        avatars = sorted(list(ls['rel__avatar']), key=lambda x: x.href)
        self.assertEquals(avatars, [ largest, medium, smallest ])

        # testing link_by_width method:
        self.assertEquals(ls['rel__avatar'].link_by_width(1000).to_dict(), largest.to_dict())
        self.assertEquals(ls['rel__avatar'].link_by_width(500), largest)
        self.assertEquals(ls['rel__avatar'].link_by_width(), largest)
        self.assertEquals(ls['rel__avatar'].link_by_width(0), largest)
        self.assertEquals(ls['rel__avatar'].link_by_width(499), largest)
        self.assertEquals(ls['rel__avatar'].link_by_width(101), largest)
        self.assertEquals(ls['rel__avatar'].link_by_width(100), medium)
        self.assertEquals(ls['rel__avatar'].link_by_width(99), medium)
        self.assertEquals(ls['rel__avatar'].link_by_width(25), smallest)
        self.assertEquals(ls['rel__avatar'].link_by_width(1), smallest)
        self.assertEquals(ls['rel__avatar'].link_by_width(-1), smallest)

        # test alternate getitem technique (used in templates)
        self.assertEquals(ls['rel__avatar']['width__1000'].to_dict(), largest.to_dict())
        self.assertEquals(ls['rel__avatar']['width__500'], largest)
        self.assertEquals(ls['rel__avatar']['width__0'], largest)
        self.assertEquals(ls['rel__avatar']['width__499'], largest)
        self.assertEquals(ls['rel__avatar']['width__101'], largest)
        self.assertEquals(ls['rel__avatar']['width__100'], medium)
        self.assertEquals(ls['rel__avatar']['width__99'], medium)
        self.assertEquals(ls['rel__avatar']['width__25'], smallest)
        self.assertEquals(ls['rel__avatar']['width__1'], smallest)

        # testing maxwidth link relation
        self.assertEquals(ls['rel__avatar']['maxwidth__1000'], largest)
        self.assertEquals(ls['rel__avatar']['maxwidth__500'], largest)
        self.assertEquals(ls['rel__avatar']['maxwidth__499'], medium)
        self.assertEquals(ls['rel__avatar']['maxwidth__101'], medium)
        self.assertEquals(ls['rel__avatar']['maxwidth__100'], medium)
        self.assertEquals(ls['rel__avatar']['maxwidth__99'], smallest)
        self.assertEquals(ls['rel__avatar']['maxwidth__25'], smallest)
        self.assert_(ls['rel__avatar']['maxwidth__24'] is None)
        self.assert_(ls['rel__avatar']['maxwidth__20'] is None)
        self.assert_(ls['rel__avatar']['maxwidth__1'] is None)
        self.assert_(ls['rel__avatar']['maxwidth__0'] is None)

        links_list = list(ls)
        self.assertEquals(len(links_list), 6)
        self.assert_(replies     in links_list)
        self.assert_(enclosure   in links_list)
        self.assert_(enclosure_2 in links_list)
        self.assert_(largest     in links_list)
        self.assert_(smallest    in links_list)
        self.assert_(medium      in links_list)

        self.assertRaises(KeyError, lambda: ls['asfdasf'])

        links_json = ls.to_dict()

        self.assert_(isinstance(links_json, list))
        self.assert_(len(links_json), 6)
        self.assert_(replies.to_dict() in links_json)


if __name__ == '__main__':
    utils.log()
    unittest.main()
