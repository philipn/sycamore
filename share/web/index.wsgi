#!/usr/bin/python -OO
# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Raw WSGI Script

    Suitable for use with apache's mod_wsgi

    @copyright: 2008 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

import sys
import os
from Sycamore.request import basic_handle_request

__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))]),
# you may need to put something like this here if you don't have
# the required python modules in your path:
#sys.path.extend(['/home/philip/lib/python/'])

# you probably have to change this
os.environ['PYTHON_EGG_CACHE'] = '/var/egg_cache' 

application = basic_handle_request
