# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.wikiutil Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki import wikiutil

# test works only for default config
class isTemplatePageTestCase(unittest.TestCase):
    GOOD = [
        'aTemplate',
        'MyTemplate',
    ]
    BAD = [
        'Template',
        'ATemplate',
        'TemplateInFront',
        'xTemplateInFront',
        'XTemplateInFront',
    ]

    def runTest(self):
        for name in self.GOOD:
            self.failUnless(wikiutil.isTemplatePage(name))
        for name in self.BAD:
            self.failIf(wikiutil.isTemplatePage(name))

# test works only for default config
class isFormPageTestCase(unittest.TestCase):
    GOOD = [
        'aForm',
        'MyForm',
    ]
    BAD = [
        'Form',
        'AForm',
        'FormInFront',
        'xFormInFront',
        'XFormInFront',
    ]

    def runTest(self):
        for name in self.GOOD:
            self.failUnless(wikiutil.isFormPage(name))
        for name in self.BAD:
            self.failIf(wikiutil.isFormPage(name))


