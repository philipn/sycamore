# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.user Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki import user

class encodePasswordTestCase(unittest.TestCase):

    def runTest(self):
        self.failUnlessEqual(
            user.encodePassword("LocalWiki"), 
            "{SHA}X+lk6KR7JuJEH43YnmettCwICdU=")
