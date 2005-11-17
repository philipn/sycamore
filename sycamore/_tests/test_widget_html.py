# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.widget.html Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki.widget import html
from LocalWiki import wikiutil

class TextTestCase(unittest.TestCase):
    def runTest(self):
        markup = '<br> &'
        self.failUnlessEqual(str(html.Text(markup)), wikiutil.escape(markup))


class RawTestCase(unittest.TestCase):
    def runTest(self):
        markup = '<br> &amp;'
        self.failUnlessEqual(str(html.Raw(markup)), markup)


class AttrTestCase(unittest.TestCase):
    def runTest(self):
        self.failUnlessRaises(AttributeError, html.BR, name='foo')


class EmptyElementTestCase(unittest.TestCase):
    def runTest(self):
        html._SORT_ATTRS = 1

        self.failUnlessEqual(str(html.BR()), '<br>')
        self.failUnlessEqual(str(html.HR()), '<hr>')


class CompositeElementTestCase(unittest.TestCase):
    def runTest(self):
        html._SORT_ATTRS = 1

        tag = html.P().append('simple & unescaped text')
        self.failUnlessEqual(str(tag), '<p>simple &amp; unescaped text</p>')

        tag = html.P().extend(['simple', ' & ', html.Text('unescaped text')])
        self.failUnlessEqual(str(tag), '<p>simple &amp; unescaped text</p>')

