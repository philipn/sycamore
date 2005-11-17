# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.wikixml.marshal Tests

    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki.wikixml import marshal

class MarshalTestCase(unittest.TestCase):
    def _canonize(self, xml):
        xml = xml.replace('\n', '')
        return xml

    def _checkData(self, data, xml):
        xml1 = self._canonize(data.toXML())
        xml2 = self._canonize(xml)
        self.failUnlessEqual(xml1, xml2)

    def runTest(self):
        obj = marshal.Marshal()
        self._checkData(obj, '<data></data>')
        obj.prop = None
        self._checkData(obj, '<data><prop><none/></prop></data>')
        obj.prop = "abc"
        self._checkData(obj, '<data><prop>abc</prop></data>')
        obj.prop = [1, "abc"]
        self._checkData(obj, '<data><prop><item>1</item><item>abc</item></prop></data>')
        obj.prop = (1, "abc")
        self._checkData(obj, '<data><prop><item>1</item><item>abc</item></prop></data>')
        obj.prop = {"abc": 1}
        self._checkData(obj, '<data><prop><abc>1</abc></prop></data>')
        obj.prop = 1
        self._checkData(obj, '<data><prop>1</prop></data>')

        class TestData:
            x = 1
            def __init__(self):
                self.y = 2
        obj.prop = TestData()
        self._checkData(obj, '<data><prop><data><y>2</y></data></prop></data>')

        import array
        obj.prop = array.array("i", [42])
        self._checkData(obj, "<data><prop>array('i', [42])</prop></data>")

        obj.prop = buffer("0123456789", 2, 3)
        self._checkData(obj, "<data><prop>234</prop></data>")

