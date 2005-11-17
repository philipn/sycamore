# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.util.web Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki.util import web
from LocalWiki.widget import html

class makeQueryStringTestCase(unittest.TestCase):
    def runTest(self):
        # keep string as string
        val = 'a=b&amp;c=d'
        self.failUnlessEqual(web.makeQueryString(val), val)

        # single value
        val = {'a': 'b'}
        self.failUnlessEqual(web.makeQueryString(val), 'a=b')

        # single integer value
        val = {'a': 1}
        self.failUnlessEqual(web.makeQueryString(val), 'a=1')

        # multiple values
        val = {'a': 'b', 'c': 'd'}
        qstr = web.makeQueryString(val)
        self.failUnless(qstr == 'a=b&amp;c=d' or qstr == 'c=d&amp;a=b')

        # keyword variant
        self.failUnlessEqual(web.makeQueryString(a=1), 'a=1')


class makeSelectionTestCase(unittest.TestCase):
    def runTest(self):
        html._SORT_ATTRS = 1

        expected = (
            '<select name="test">'
            '<option value="one">one</option>'
            '<option value="two">two</option>'
            '<option value="simple">simple</option>'
            '<option value="complex">A tuple &amp; &lt;escaped text&gt;</option>'
            '</select>'
        )
        values = ['one', 'two', 'simple', ('complex', 'A tuple & <escaped text>')]

        sel = web.makeSelection('test', values)
        self.failUnlessEqual(str(sel), expected)

        sel = web.makeSelection('test', values, 'three')
        self.failUnlessEqual(str(sel), expected)

        expected = expected.replace('value="two"', 'selected value="two"')
        sel = web.makeSelection('test', values, 'two')
        self.failUnlessEqual(str(sel), expected)

