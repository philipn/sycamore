#!/usr/bin/env python -OO
# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - CGI Driver Script

    @copyright: 2006 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

import sys, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))]),

from LocalWiki.support.wsgi_server.cgi_base import run_with_cgi
#from LocalWiki.support.wsgi_server import swap 
from LocalWiki.request import RequestWSGI

os.environ["FCGI_FORCE_CGI"] = 'Y'

def handle_request(env, start_response):
  if env.get('QUERY_STRING', '') == 'profile':
    profile.runctx('RequestWSGI(env,start_response).run()', globals(), locals(), 'prof.%s' % time.time())
    return ['profile ran']
  else:
    request = RequestWSGI(env, start_response)
    return request.run()

run_with_cgi(handle_request)
