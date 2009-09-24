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

import logging
import random
import sys
import unittest
import traceback

import simplejson as json

import remoteobjects
import typepad
from tests import utils


class TestObjects(unittest.TestCase):

    @utils.todo
    def test_relative_urls(self):
        raise NotImplementedError()

    @utils.todo
    def test_batch_enforcement(self):
        raise NotImplementedError()

    def test_listof(self):
        x = typepad.ListOf('User')
        self.assert_(isinstance(x, type))
        self.assert_(issubclass(x, typepad.ListObject))
        self.assert_(issubclass(x, remoteobjects.PageObject))
        self.assertEquals(x.__name__, 'ListOfUser')

        y = typepad.ListOf('User')
        self.assert_(x is y, "two ListOf's the same thing are not only "
                             "equivalent but the same instance")

    def test_links(self):

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
            'width':  459,
            'height': 459
        }
        enclosure_2 = {
            'href':   'http://127.0.0.1:8000/uploads/1/2.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  460,
            'height': 460
        }
        enclosure_3 = {
            'href':   'http://127.0.0.1:8000/uploads/1/3.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  460,
            'height': 459
        }
        enclosure_4 = {
            'href':   'http://127.0.0.1:8000/uploads/1/4.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  459,
            'height': 460
        }
        enclosure_5 = {
            'href':   'http://127.0.0.1:8000/uploads/1/5.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  459,
            'height': 461
        }
        enclosure_6 = {
            'href':   'http://127.0.0.1:8000/uploads/1/6.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  460,
            'height': 461
        }
        enclosure_7 = {
            'href':   'http://127.0.0.1:8000/uploads/1/7.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  461,
            'height': 460
        }
        enclosure_8 = {
            'href':   'http://127.0.0.1:8000/uploads/1/8.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  461,
            'height': 459
        }
        enclosure_9 = {
            'href':   'http://127.0.0.1:8000/uploads/1/9.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  461,
            'height': 461
        }
        enclosure_10 = {
            'href':   'http://127.0.0.1:8000/uploads/1/10.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  465,
            'height': 480
        }
        enclosure_11 = {
            'href':   'http://127.0.0.1:8000/uploads/1/11.gif',
            'type':   'image/jpeg',
            'rel':    'enclosure',
            'width':  10000,
            'height': 10000
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
            enclosure_3, enclosure_4, enclosure_5, enclosure_6, enclosure_7,
            enclosure_8, enclosure_9, enclosure_10, enclosure_11,
            largest, smallest, medium ])
        ls1 = typepad.LinkSet.from_dict([ enclosure, enclosure_10, enclosure_11 ])

        replies      = typepad.Link.from_dict(replies)
        enclosure    = typepad.Link.from_dict(enclosure)
        enclosure_2  = typepad.Link.from_dict(enclosure_2)
        enclosure_3  = typepad.Link.from_dict(enclosure_3)
        enclosure_4  = typepad.Link.from_dict(enclosure_4)
        enclosure_5  = typepad.Link.from_dict(enclosure_5)
        enclosure_6  = typepad.Link.from_dict(enclosure_6)
        enclosure_7  = typepad.Link.from_dict(enclosure_7)
        enclosure_8  = typepad.Link.from_dict(enclosure_8)
        enclosure_9  = typepad.Link.from_dict(enclosure_9)
        enclosure_10 = typepad.Link.from_dict(enclosure_10)
        enclosure_11 = typepad.Link.from_dict(enclosure_11)
        largest      = typepad.Link.from_dict(largest)
        smallest     = typepad.Link.from_dict(smallest)
        medium       = typepad.Link.from_dict(medium)

        self.assert_(isinstance(ls, typepad.LinkSet))
        self.assertEquals(len(ls), 15)

        self.assertEquals(ls['replies'], replies)
        self.assert_(ls['enclosure'] in (enclosure, enclosure_2, enclosure_3,
            enclosure_4, enclosure_5, enclosure_6, enclosure_7, enclosure_8,
            enclosure_9, enclosure_10, enclosure_11))
        self.assertEquals(list(ls['rel__replies']), [ replies ])
        enclosures = sorted(list(ls['rel__enclosure']), key=lambda x: x.href)
        self.assertEquals(enclosures, [ enclosure, enclosure_10, enclosure_11,
            enclosure_2, enclosure_3, enclosure_4, enclosure_5, enclosure_6,
            enclosure_7, enclosure_8, enclosure_9 ])
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

        # testing enclosure selection for width of 458px
        # enclosure is the best pick here (459x459)
        self.assertEquals(ls1['rel__enclosure'].link_by_size(458), enclosure)
        self.assertEquals(ls1['rel__enclosure'].link_by_size(460), enclosure)
        self.assertEquals(ls1['rel__enclosure'].link_by_size(470), enclosure)
        self.assertEquals(ls1['rel__enclosure'].link_by_size(480), enclosure_10)
        self.assertEquals(ls1['rel__enclosure'].link_by_size(500), enclosure_10)

        # testing enclosure selection for width of 459px
        # enclosure is the best pick here (459x459)
        self.assertEquals(ls['rel__enclosure'].link_by_size(459), enclosure)

        # testing enclosure selection for width of 460px
        # enclosure_2 is the best pick here (460x460)
        self.assertEquals(ls['rel__enclosure'].link_by_size(460), enclosure_2)

        # testing enclosure selection for width of 461px
        # enclosure_9 is the best pick here (461x461)
        self.assertEquals(ls['rel__enclosure'].link_by_size(461), enclosure_9)

        # testing enclosure selection for width of 480px
        # should NOT select 10000^2 image; best choice is enclosure_10
        self.assertEquals(ls['rel__enclosure'].link_by_size(480), enclosure_10)

        links_list = list(ls)
        self.assertEquals(len(links_list), 15)
        self.assert_(replies      in links_list)
        self.assert_(enclosure    in links_list)
        self.assert_(enclosure_2  in links_list)
        self.assert_(enclosure_3  in links_list)
        self.assert_(enclosure_4  in links_list)
        self.assert_(enclosure_5  in links_list)
        self.assert_(enclosure_6  in links_list)
        self.assert_(enclosure_7  in links_list)
        self.assert_(enclosure_8  in links_list)
        self.assert_(enclosure_9  in links_list)
        self.assert_(enclosure_10 in links_list)
        self.assert_(enclosure_11 in links_list)
        self.assert_(largest      in links_list)
        self.assert_(smallest     in links_list)
        self.assert_(medium       in links_list)

        self.assertRaises(KeyError, lambda: ls['asfdasf'])

        links_json = ls.to_dict()

        self.assert_(isinstance(links_json, list))
        self.assert_(len(links_json), 6)
        self.assert_(replies.to_dict() in links_json)


if __name__ == '__main__':
    utils.log()
    unittest.main()
