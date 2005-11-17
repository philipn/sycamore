# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Dump a LocalWiki wiki to static pages

    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

__version__ = "20031227"

# you very likely have to adapt this:
import sys
sys.path.append('/org/org.linuxwiki/cgi-bin') # moin_config
sys.path.append('/org/wiki') # Farm config
sys.path.append('/home/twaldmann/moincvs/moin--main/') # LocalWiki

url_prefix = "."
css_url = "./screen.css"
logo_html = '<img src="linuxwiki.png">'

HTML_SUFFIX = ".html"

# XXX UNICODE add encoding with config.charset
page_template = '''<html>
<head>
<title>%(pagename)s</title>
<link rel="stylesheet" type="text/css" href="%(css_url)s">
</head>
<body>
<table>
<tr>
<td>
%(logo_html)s
</td>
<td>
%(navibar_html)s
</td>
</tr>
</table>
<hr>
%(pagehtml)s
<hr>
%(timestamp)s
</body>
</html>
'''

import os, time, cStringIO
from LocalWiki.scripts import _util

class MoinDump(_util.Script):
    def __init__(self):
        _util.Script.__init__(self, __name__, "[options] <target-directory>")

        # --config=DIR            
        self.parser.add_option(
            "--config", metavar="DIR", dest="configdir",
            help="Path to moin_config.py (or its directory)"
        )

        # --page=NAME             
        self.parser.add_option(
            "--page", metavar="NAME", dest="page",
            help="Dump a single page (with possibly broken links)"
        )
        

    def mainloop(self):
        """ moin-dump's main code. """

        if len(sys.argv) == 1:
            self.parser.print_help()
            sys.exit(1)

        if len(self.args) != 1:
            self.parser.error("incorrect number of arguments")

        # Prepare output directory
        outputdir = self.args[0]
        outputdir = os.path.abspath(outputdir)
        if not os.path.isdir(outputdir):
            try:
                os.mkdir(outputdir)
                _util.log("Created output directory '%s'!" % outputdir)
            except OSError:
                _util.fatal("Cannot create output directory '%s'!" % outputdir)

        # Load the configuration
        configdir = self.options.configdir
        if configdir:
            if os.path.isfile(configdir): configdir = os.path.dirname(configdir)
            if not os.path.isdir(configdir):
                _util.fatal("Bad path given to --config parameter")
            configdir = os.path.abspath(configdir)
            sys.path[0:0] = [configdir]
            os.chdir(configdir)

        from LocalWiki import config
        if config.default_config:
            _util.fatal("You have to be in the directory containing moin_config.py, "
                "or use the --config option!")

        # fix some values so we get relative paths in output html
        config.url_prefix = url_prefix

        # XXX check this, does this still exist?
        config.css_url    = css_url
        
        # avoid spoiling the cache with url_prefix == "."
        # we do not use nor update the cache because of that
        config.caching_formats = []

        # Dump the wiki
        from LocalWiki.request import RequestCGI
        request = RequestCGI({'script_name': '.'})
        request.form = request.args = request.setup_args()

        from LocalWiki import wikiutil, Page
        if self.options.page:
            pages = [self.options.page]
        else:
            pages = list(wikiutil.getPageList(config.text_dir))
        pages.sort()

        wikiutil.quoteWikiname = lambda pagename, qfn=wikiutil.quoteWikiname: qfn(pagename) + HTML_SUFFIX

        errfile = os.path.join(outputdir, 'error.log')
        errlog = open(errfile, 'w')
        errcnt = 0

        page_front_page = wikiutil.getSysPage(request, 'FrontPage').page_name
        page_title_index = wikiutil.getSysPage(request, 'TitleIndex').page_name
        page_word_index = wikiutil.getSysPage(request, 'WordIndex').page_name
        
        navibar_html = ''
        for p in [page_front_page, page_title_index, page_word_index]:
            navibar_html += '&nbsp;[<a href="%s">%s</a>]' % (wikiutil.quoteWikiname(p), wikiutil.escape(p))

        for pagename in pages:
            file = wikiutil.quoteWikiname(pagename)
            _util.log('Writing "%s"...' % file)
            try:
                pagehtml = ''
                page = Page.Page(pagename)
                try:
                    request.reset()
                    out = cStringIO.StringIO()
                    request.redirect(out)
                    page.send_page(request, count_hit=0, content_only=1)
                    pagehtml = out.getvalue()
                    request.redirect()
                except:
                    errcnt = errcnt + 1
                    print >>sys.stderr, "*** Caught exception while writing page!"
                    print >>errlog, "~" * 78
                    import traceback
                    traceback.print_exc(None, errlog)
            finally:
                timestamp = time.strftime("%Y-%m-%d %H:%M")
                filepath = os.path.join(outputdir, file)
                fileout = open(filepath, 'w')
                fileout.write(page_template % {
                    'pagename': pagename,
                    'css_url': config.css_url,
                    'pagehtml': pagehtml,
                    'logo_html': logo_html,
                    'navibar_html': navibar_html,
                    'timestamp': timestamp,
                })
                fileout.close()

        # copy FrontPage to "index.html"
        indexpage = page_front_page
        if self.options.page:
            indexpage = self.options.page
        import shutil
        shutil.copyfile(
            os.path.join(outputdir, wikiutil.quoteFilename(indexpage) + HTML_SUFFIX),
            os.path.join(outputdir, 'index' + HTML_SUFFIX)
        )

        errlog.close()
        if errcnt:
            print >>sys.stderr, "*** %d error(s) occurred, see '%s'!" % (errcnt, errfile)

def run():
    MoinDump().run()

if __name__ == "__main__":
    run()

