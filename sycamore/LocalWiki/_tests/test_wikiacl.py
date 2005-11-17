# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.wikiacl Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki import config, wikiacl, _tests

class parsingTestCase(unittest.TestCase):
    def runTest(self):
        if not config.acl_enabled:
            return

        acl = wikiacl.AccessControlList(
            ["Admin1,Admin2:read,write,admin"
             " JoeDoe:read"
             " BadBadGuy:"
             " All:read"]
        )

        nsave=_tests.request.user.name
        _tests.request.user.name='SomeBody'
        self.failIf(acl.may(_tests.request, 'JoeDoe', 'admin'))
        self.failUnless(acl.may(_tests.request, 'Admin1', 'write'))
        self.failUnless(acl.may(_tests.request, 'Admin2', 'admin'))
        self.failUnless(acl.may(_tests.request, 'BelongsToAll', 'read'))
        self.failIf(acl.may(_tests.request, 'BelongsToAll', 'write'))
        
        for right in config.acl_rights_valid:
            self.failIf(acl.may(_tests.request, 'BadBadGuy', right))
        _tests.request.user.name=nsave

