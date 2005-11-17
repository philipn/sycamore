# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.wikimacro Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest, os
from LocalWiki import _tests
from LocalWiki import wikimacro, wikiutil
from LocalWiki.parser.plain import Parser
from LocalWiki.formatter.text_html import Formatter

def execute(macro, args):
    """ Test helper.
    """
    assert hasattr(macro, "request")
    assert hasattr(macro.request, "user")
    return args


def _make_macro():
    p = Parser("##\n", _tests.request)
    p.formatter = Formatter(_tests.request)
    _tests.request.formatter = p.formatter
    p.form = _tests.request.form
    m = wikimacro.Macro(p)
    return m


class NormalMacroTestCase(unittest.TestCase):
    def runTest(self):
        m = _make_macro()
        self.failUnlessEqual(
            m.execute("BR", ""),
            m.formatter.linebreak(0))

