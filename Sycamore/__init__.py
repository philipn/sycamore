# -*- coding: iso-8859-1 -*-
"""
    Sycamore wiki engine - Package Initialization

    @copyright: 2004-2007 Philip Neustrom <philipn@gmail.com>
    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""
# Imports
import sys, os.path

__directory__ = os.path.dirname(__file__)

sys.path.extend([os.path.abspath(os.path.join(__directory__, '..')),
                 os.path.abspath(os.path.join(__directory__, '..', 'share'))])

__author__ = 'Wiki Spot.  See CONTRIBUTORS file for complete list.'

__version__ = '0.1d_wikis'
