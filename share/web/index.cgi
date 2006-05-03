#!/usr/bin/python -OO
# -*- coding: iso-8859-1 -*-
"""
    Sycamore - CGI Driver Script

    @copyright: 2006 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

import sys, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))]),
# you may need to put something like this here if you don't have the required python modules in your path:
#sys.path.extend(['/home/philip/lib/python/'])

from Sycamore.support.wsgi_server.cgi_base import run_with_cgi
from Sycamore.request import RequestWSGI
from Sycamore.request import basic_handle_request

os.environ["FCGI_FORCE_CGI"] = 'Y'

run_with_cgi(basic_handle_request)
