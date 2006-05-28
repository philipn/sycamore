# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Package Initialization

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""
# Imports

import sys, os.path

__directory__ = os.path.dirname(__file__)

sys.path.extend([os.path.abspath(os.path.join(__directory__, '..')),
                 os.path.abspath(os.path.join(__directory__, '..', 'share'))])

__version__ = '0.1a'
