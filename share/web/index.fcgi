#!/usr/bin/python -OO
# -*- coding: iso-8859-1 -*-
"""
    Sycamore - FastCGI Driver Script

    @copyright: 2006 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

import sys, logging, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))]),

from Sycamore.support.wsgi_server.fcgi import WSGIServer
#from Sycamore.support.wsgi_server import swap 
from Sycamore.request import RequestWSGI
from logging import NOTSET
import profile, time

def handle_request(env, start_response):
  if env.get('QUERY_STRING', '') == 'profile':
    profile.runctx('RequestWSGI(env,start_response).run()', globals(), locals(), 'prof.%s' % time.time())
    return ['profile ran']
  else:
    request = RequestWSGI(env, start_response)
    return request.run()
    
if __name__ == '__main__':
  #WSGIServer(handle_request, '/tmp/fcgi.sock').run()
  #swap.serve_application(handle_request, '/index.scgi', 8882)
  WSGIServer(handle_request, bindAddress=('localhost', 8882)).run()