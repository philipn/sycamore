#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - CGI Driver Script

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import sys
sys.path.extend(['/var/www/lib/','/var/www/html/installhtml/dwiki'])

from LocalWiki.request import RequestCGI

import os
if os.environ.get('QUERY_STRING') == 'test':
    print "Content-Type: text/plain\n\nLocalWiki CGI Diagnosis\n======================\n"

    try:
        from LocalWiki.wikitest import runTest
        print 'Package "LocalWiki" successfully imported.\n'
        request = RequestCGI()    
        runTest(request)
    except:
        import sys, traceback, string, pprint
        type, value, tb = sys.exc_info()
        if type == ImportError:
            print 'Your PYTHONPATH is:\n%s' % pprint.pformat(sys.path)
        print "\nTraceback (innermost last):\n%s" % string.join(
            traceback.format_tb(tb) + traceback.format_exception_only(type, value))
else:
    request = RequestCGI()
    request.run()
