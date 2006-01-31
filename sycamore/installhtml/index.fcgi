#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - FastCGI Driver Script

    @copyright: 2004 by Oliver Graf <ograf@bitart.de>
    @license: GNU GPL, see COPYING for details.
"""

import sys
sys.path.extend(['/Library/Webserver/sycamore','/Library/Webserver/sycamore/installhtml/dwiki'])

from LocalWiki.request import RequestFastCGI
from LocalWiki.support import thfcgi

def handle_request(req, env, form, properties={}):
    #test = open('/var/www/test_memory.txt','a')
    #test.write('\n'+str(memory()))
    #test.close()
    request = RequestFastCGI(req,env,form,properties={})
    request.run()
    

if __name__ == '__main__':
    # this is a multi-threaded FastCGI
    # use thfcgi.unTHFCGI for a single-threaded instance
    # use the following line if you want to run via apache locally
    #fcg = thfcgi.THFCGI(handle_request)
    # use the following if you want to use as an external app via apche or using lighttpd
    fcg = thfcgi.THFCGI(handle_request, 0, 8888)
    fcg.run()
