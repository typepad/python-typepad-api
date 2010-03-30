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
import random
import sys
import unittest
import traceback
import re

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

    def test_imagelink(self):
        l = typepad.ImageLink(url_template='http://example.com/blah-{spec}')
        self.assertEquals(l.at_size('16si'), 'http://example.com/blah-16si')
        self.assertEquals(l.at_size('pi'), 'http://example.com/blah-pi')
        self.assertEquals(l.at_size('1024wi'), 'http://example.com/blah-1024wi')
        self.assertRaises(ValueError, lambda: l.at_size('77moof'))
        self.assertRaises(ValueError, lambda: l.at_size('blah'))
        self.assertRaises(ValueError, lambda: l.at_size(''))
        self.assertRaises(ValueError, lambda: l.at_size('77'))
        self.assertRaises(ValueError, lambda: l.at_size('220wi'))

    def test_imagelink_exhaustive(self):
        def prove(l):
            for size in typepad.ImageLink._WI:
                i = l.by_width(size)
                i2 = l.by_width(size-1)
                self.assertEquals(i.width, min(l.width, size), "testing by_width(%d); got %d" % (min(l.width, size), i.width))
                self.assertEquals(i2.width, min(l.width, size-1), "testing by_width(%d); got %d" % (min(l.width, size-1), i2.width))

            for size in typepad.ImageLink._HI:
                i = l.by_height(size)
                i2 = l.by_height(size-1)
                self.assertEquals(i.height, min(l.height, size), "testing by_height(%d); got %d" % (min(l.height, size), i.height))
                self.assertEquals(i2.height, min(l.height, size-1), "testing by_height(%d); got %d" % (min(l.height, size-1), i2.height))

            for size in typepad.ImageLink._PI:
                i = l.inscribe(size)
                i2 = l.inscribe(size-1)
                self.assert_(i.width == min(l.width, size) or i.height == min(l.height, size), "testing inscribe(%d); got %d, %d" % (max(min(l.width, size), min(l.height, size)), i.width, i.height))
                self.assert_(i2.width == min(l.width, size-1) or i2.height == min(l.height, size-1), "testing inscribe(%d); got %d, %d" % (max(min(l.width, size-1), min(l.height, size-1)), i2.width, i2.height))

            for size in typepad.ImageLink._SI:
                i = l.square(size)
                i2 = l.square(size-1)
                self.assertEquals(i.width, min(max(l.width, l.height), size), "testing width of square(%d)" % size)
                self.assertEquals(i.height, min(max(l.width, l.height), size), "testing height of square(%d)" % size)
                self.assertEquals(i2.width, min(max(l.width, l.height), size-1), "testing width of square(%d)" % (size-1))
                self.assertEquals(i2.height, min(max(l.width, l.height), size-1), "testing height of square(%d)" % (size-1))

        # big square image
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5000, width=5000))

        # small image, wider than tall
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=100, width=200))

        # small image, taller than wide
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=200, width=100))

        # medium image, wider than tall
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=480, width=640))

        # a teeny square image
        prove(typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5, width=5))

    def test_imagelink_inscribe(self):
        l = typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5000, width=5000)
        self.assertEquals(l.inscribe(320).url, 'http://example.com/blah-320pi')
        self.assertEquals(l.inscribe(76).url, 'http://example.com/blah-115pi')
        self.assertEquals(l.inscribe(1).url, 'http://example.com/blah-50pi')
        self.assertEquals(l.inscribe(4999).url, 'http://example.com/blah-1024pi')
        self.assertEquals(l.inscribe(4999).width, 1024)

    def test_imagelink_by_width(self):
        l = typepad.ImageLink(url='http://example.com/blah',
            url_template='http://example.com/blah-{spec}',
            height=5000, width=5000)

        # exact, known size
        self.assertEquals(l.by_width(250).url,
            'http://example.com/blah-250wi')

        # just a bit bigger than 75px; should return 100 wide
        self.assertEquals(l.by_width(76).url, 'http://example.com/blah-100wi')

        # selects for smallest available size, 16
        self.assertEquals(l.by_width(1).url, 'http://example.com/blah-50wi')

        # selects a big size that isn't available; should return original image
        self.assertEquals(l.by_width(4999).url, 'http://example.com/blah-1024wi')
        self.assertEquals(l.by_width(4999).width, 1024)

        # selects a size larger than the original image; returns original image
        self.assertEquals(l.by_width(5001).url, 'http://example.com/blah-1024wi')

        self.assertEquals(l.by_width(None).url, 'http://example.com/blah-1024wi')

    def test_videolink_by_width(self):
        v = typepad.VideoLink(embed_code="\n<object width=\"500\" height=\"395\">\n    <param name=\"movie\" value=\"http://www.youtube.com/v/deadbeef\" />\n    <param name=\"quality\" value=\"high\" />\n    <param name=\"wmode\" value=\"transparent\" />\n    <param name=\"allowscriptaccess\" value=\"never\" />\n    <param name=\"allowFullScreen\" value=\"true\" />\n    <embed type=\"application/x-shockwave-flash\"\n        width=\"500\" height=\"395\"\n        src=\"http://www.youtube.com/v/deadbeef\"\n        quality=\"high\" wmode=\"transparent\" allowscriptaccess=\"never\" allowfullscreen=\"true\"\n    />\n</object>\n")
        sv = v.by_width(400)
        self.assertEquals(sv.width, 400)
        self.assertEquals(sv.height, 316)
        self.assert_(re.search('\swidth="400"', sv.embed_code))
        self.assert_(re.search('\sheight="316"', sv.embed_code))

if __name__ == '__main__':
    utils.log()
    unittest.main()
