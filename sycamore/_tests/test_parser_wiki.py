# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.parser.wiki Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest, re
from LocalWiki import _tests
from LocalWiki.Page import Page
from LocalWiki.parser.wiki import Parser

class ExpectTest(unittest.TestCase):
    BODY = None
    EXPECTED = None

    def runTest(self):
        assert self.BODY is not None
        assert self.EXPECTED is not None

        pg = Page('VirtualPage')
        pg.set_raw_body(self.BODY)

        from LocalWiki.formatter.text_html import Formatter
        pg.formatter = Formatter(_tests.request)
        _tests.request.formatter = pg.formatter
        pg.formatter.setPage(pg)
        pg.hilite_re = None

        output = []
        def write_output(text, o=output):
            o.append(text)

        saved_write = _tests.request.write
        _tests.request.write = write_output
        try:
            Parser(self.BODY, _tests.request).format(pg.formatter)
        finally:
            _tests.request.write = saved_write

        output = ''.join(output).replace('<p>', '\n<p>')
        for pattern in self.EXPECTED:
           regex = re.compile(pattern)
           self.failUnless(regex.search(output), msg='Expected %r in: %s' % (pattern, output))


class InlineMarkupTestCase(ExpectTest):
    BODY = """
''em''
'''bold'''
__underline__

'''''Mix''' at start'' 
'''''Mix'' at start''' 
'''Mix at ''end''''' 
''Mix at '''end''''' 
"""

    EXPECTED = [
        '<em>em</em>',
        '<strong>bold</strong>',
        '<u>underline</u>',

        '<em><strong>Mix</strong> at start</em>',
        '<strong><em>Mix</em> at start</strong>',
        '<strong>Mix at <em>end</em></strong>',
        '<em>Mix at <strong>end</strong></em>',
    ]

# If this fails, it is likely a problem in your python / libc, not in moin.
# See also: http://sourceforge.net/tracker/index.php?func=detail&aid=902172&group_id=5470&atid=105470
class WikiMacroTestCase(ExpectTest):
    BODY = """
1#[[DateTime(1970-01-06T00:00:00)]]#1
2#[[DateTime(259200)]]#2
3#[[DateTime(2003-03-03T03:03:03)]]#3
4#[[DateTime(2000-01-01T00:00:00Z)]]#4
5#[[Date(2002-02-02T01:02:03Z)]]#5
"""

    EXPECTED = [
        '1#1970-01-06 00:00:00#1',
        '2#1970-01-04 00:00:00#2',
        '3#2003-03-03 03:03:03#3',
        '4#2000-01-01 00:00:00#4',
        '5#2002-02-02#5',
    ]


class PageLinkTestCase(ExpectTest):
    BODY = """["../"]"""
    EXPECTED = ['">../</a>']

