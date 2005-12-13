#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - FastCGI Driver Script

    @copyright: 2004 by Oliver Graf <ograf@bitart.de>
    @license: GNU GPL, see COPYING for details.
"""

import sys
sys.path[0:0]=['/usr/local/lib/python2.3/site-packages', '/var/www/dwiki']

from LocalWiki.request import RequestFastCGI
from LocalWiki.support import thfcgi

def handle_request(req, env, form):
    request = RequestFastCGI(req,env,form)
    request.run()

if __name__ == '__main__':
    # this is a multi-threaded FastCGI
    # use thfcgi.unTHFCGI for a single-threaded instance
    fcg = thfcgi.THFCGI(handle_request)
    fcg.run()
