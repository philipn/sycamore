# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Python Source Parser

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import cStringIO
import keyword, token, tokenize
from LocalWiki import wikiutil

#############################################################################
### Python Source Parser (does Hilighting)
#############################################################################

_KEYWORD = token.NT_OFFSET + 1
_TEXT    = token.NT_OFFSET + 2

_colors = {
    token.NUMBER:       '#0080C0',
    token.OP:           '#0000C0',
    token.STRING:       '#004080',
    tokenize.COMMENT:   '#008000',
    token.NAME:         '#000000',
    token.ERRORTOKEN:   '#FF8080',
    _KEYWORD:           '#C00000',
    _TEXT:              '#000000',
}


class Parser:
    """ Send colored python source.
    """

    def __init__(self, raw, request, **kw):
        """ Store the source text.
        """
        self.raw = raw.expandtabs().rstrip()
        self.request = request
        self.form = request.form
        self._ = request.getText

        self.out = kw.get('out', request)

    def format(self, formatter):
        """ Parse and send the colored source.
        """
        # store line offsets in self.lines
        self.lines = [0, 0]
        pos = 0
        while 1:
            pos = self.raw.find('\n', pos) + 1
            if not pos: break
            self.lines.append(pos)
        self.lines.append(len(self.raw))

        # write line numbers
        self.out.write('<table border="0"><tr><td align="right" valign="top">')
        self.out.write('<td align="right" valign="top"><pre><font face="Lucida,Courier New" color="%s">' % _colors[_TEXT])
        for idx in range(1, len(self.lines)-1):
            self.out.write('%3d \n' % idx)
        self.out.write('</font></pre></td><td valign="top">')

        # parse the source and write it
        self.pos = 0
        text = cStringIO.StringIO(self.raw)
        self.out.write('<pre><font face="Lucida,Courier New">')
        try:
            tokenize.tokenize(text.readline, self)
        except tokenize.TokenError, ex:
            msg = ex[0]
            line = ex[1][0]
            self.out.write("<h3>ERROR: %s</h3>%s\n" % (
                msg, self.raw[self.lines[line]:]))
        self.out.write('</font></pre>')

        # close table
        self.out.write('</td></tr></table>')

    def __call__(self, toktype, toktext, (srow,scol), (erow,ecol), line):
        """ Token handler.
        """
        if 0: print "type", toktype, token.tok_name[toktype], "text", toktext, \
                    "start", srow,scol, "end", erow,ecol, "<br>"

        # calculate new positions
        oldpos = self.pos
        newpos = self.lines[srow] + scol
        self.pos = newpos + len(toktext)

        # handle newlines
        if toktype in [token.NEWLINE, tokenize.NL]:
            self.out.write('\n')
            return

        # send the original whitespace, if needed
        if newpos > oldpos:
            self.out.write(self.raw[oldpos:newpos])

        # skip indenting tokens
        if toktype in [token.INDENT, token.DEDENT]:
            self.pos = newpos
            return

        # map token type to a color group
        if token.LPAR <= toktype and toktype <= token.OP:
            toktype = token.OP
        elif toktype == token.NAME and keyword.iskeyword(toktext):
            toktype = _KEYWORD
        color = _colors.get(toktype, _colors[_TEXT])

        style = ''
        if toktype == token.ERRORTOKEN:
            style = ' style="border: solid 1.5pt #FF0000;"'

        # send text
        self.out.write('<font color="%s"%s>' % (color, style))
        self.out.write(wikiutil.escape(toktext))
        self.out.write('</font>')


if __name__ == "__main__":
    import os
    print "Formatting..."

    # open own source
    source = open('python.py').read()

    # write colorized version to "python.html"
    Parser(source, None, out = open('python.html', 'wt')).format(None)

    # load HTML page into browser
    if os.name == "nt":
        os.system("explorer python.html")
    else:
        os.system("netscape python.html &")

