# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.Page Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki import Page

class existsTestCase(unittest.TestCase):
    def runTest(self):
        pg = Page.Page('OnlyAnIdiotWouldCreateSuchaPage')
        self.failIf(pg.exists())

