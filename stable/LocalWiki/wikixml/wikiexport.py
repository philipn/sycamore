# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - XML Export

    This module exports all data stored for a wiki.

    @copyright: 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import config, wikixml
import LocalWiki.wikixml.util


#############################################################################
### XML Generator
#############################################################################

class ExportGenerator(wikixml.util.XMLGenerator):
    default_xmlns = {
        None: "http://purl.org/wiki/moin/export",
    }

    def __init__(self, out):
        wikixml.util.XMLGenerator.__init__(self, out=out)

    def startDocument(self):
        wikixml.util.XMLGenerator.startDocument(self)
        self.startElementNS((None, 'export'), 'export', {})

    def endDocument(self):
        self.endElementNS((None, 'export'), 'export')
        wikixml.util.XMLGenerator.endDocument(self)


#############################################################################
### WikiExport class
#############################################################################

class WikiExport:
    """ Create an XML document containing all information stored in a wiki.
    """

    def __init__(self, out, **kw):
        """ Write wiki data to stream `out`.

            Keywords:
                public - true when this is a public export (no userdata etc.)
        """
        self._out = out
        self._public = kw.get('public', 1)

    def run(self):
        """ Start the export process.
        """
        self.doc = ExportGenerator(self._out)
        self.doc.startDocument()
        self.doc.endDocument()

    #
    # Pages
    #

    #
    # Users
    #

    #
    # Attachments
    #

