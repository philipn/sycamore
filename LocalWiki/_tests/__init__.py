# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Unit tests

    Subpackage containing all unit tests. This is currently NOT
    installed.

    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import os, sys, unittest
from LocalWiki import config, user
from LocalWiki.util import pysupport

# List of config parameters that must be forced to defaults
# in order to make the tests work
_FORCED_DEFAULTS = [
    'date_fmt',
    'datetime_fmt',
    'page_template_regex',
    'page_form_regex',
    'page_category_regex',
]

# Request instance for tests
request = None

def makeSuite():
    """ Automatically create tests and test suites for all tests.

        For this to work, test modules must reside in LocalWiki._tests
        (i.e. right here) and have names starting with "test_", and
        contain test cases with names ending in "TestCase".
    """
    result = unittest.TestSuite()
    test_modules = pysupport.getPackageModules(__file__)

    for mod_name in test_modules:
        if not mod_name.startswith('test_'): continue

        module = __import__(__name__ + '.' + mod_name, globals(), locals(), ['__file__'])
        test_cases = [
            obj() for name, obj in module.__dict__.items()
                if name.endswith('TestCase')
        ]

        if test_cases:
            suite = unittest.TestSuite(test_cases)
            result.addTest(suite)

    return result


def run(provided_request=None):
    global request

    if provided_request:
        request = provided_request
    else:
        from LocalWiki.request import RequestCLI
        request = RequestCLI()
    
        request.form = request.args = request.setup_args()
        # {'query_string': 'action=print'}

    for cfgval in _FORCED_DEFAULTS:
        setattr(config, cfgval, config._cfg_defaults[cfgval])

    request.user = user.User(request)

    suite = makeSuite()
    unittest.TextTestRunner(stream=request, verbosity=2).run(suite)

