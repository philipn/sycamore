# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Utility Functions

    Copyright (c) 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    All rights reserved, see COPYING for details.

    General helper functions that are not directly wiki related.

    $Id: __init__.py,v 1.8 2004/02/10 21:01:56 thomaswaldmann Exp $
"""

# Imports
import os, re, time


#############################################################################
### XML helper functions
#############################################################################

g_xmlIllegalCharPattern = re.compile('[\x01-\x08\x0B-\x0D\x0E-\x1F\x80-\xFF]')
g_undoUtf8Pattern       = re.compile('\xC2([^\xC2])')
g_cdataCharPattern      = re.compile('[&<\'\"]')
g_textCharPattern       = re.compile('[&<]')
g_charToEntity = {
    '&': '&amp;',
    '<': '&lt;',
    "'": '&apos;',
    '"': '&quot;'
}

def TranslateCDATA(text):
    """
        Convert a string to a CDATA-encoded one
        Copyright (c) 1999-2000 FourThought, http://4suite.com/4DOM
    """
    new_string, num_subst = re.subn(g_undoUtf8Pattern, lambda m: m.group(1), text)
    new_string, num_subst = re.subn(g_cdataCharPattern, lambda m, d=g_charToEntity: d[m.group()], new_string)
    new_string, num_subst = re.subn(g_xmlIllegalCharPattern, lambda m: '&#x%02X;'%ord(m.group()), new_string)
    return new_string

def TranslateText(text):
    """
        Convert a string to a PCDATA-encoded one (do minimal encoding)
        Copyright (c) 1999-2000 FourThought, http://4suite.com/4DOM
    """
    new_string, num_subst = re.subn(g_undoUtf8Pattern, lambda m: m.group(1), text)
    new_string, num_subst = re.subn(g_textCharPattern, lambda m, d=g_charToEntity: d[m.group()], new_string)
    new_string, num_subst = re.subn(g_xmlIllegalCharPattern, lambda m: '&#x%02X;'%ord(m.group()), new_string)
    return new_string


#############################################################################
### Exceptions
#############################################################################

class SycamoreNoFooter(Exception):
    """Raised by actions to prevent output of a page footer (with timings)."""
    pass

#############################################################################
### Misc
#############################################################################

# popen (use win32 version if available)
popen = os.popen
if os.name == "nt":
    try:
        import win32pipe
        popen = win32pipe.popen
    except ImportError:
        pass


def rangelist(numbers):
    """ Convert a list of integers to a range string in the form
        '1,2-5,7'.
    """
    numbers = numbers[:]
    numbers.sort()
    numbers.append(999999)
    pattern = ','
    for i in range(len(numbers)-1):
        if pattern[-1] == ',':
            pattern = pattern + str(numbers[i])
            if numbers[i]+1 == numbers[i+1]:
                pattern = pattern + '-'
            else:
                pattern = pattern + ','
        elif numbers[i]+1 != numbers[i+1]:
            pattern = pattern + str(numbers[i]) + ','

    if pattern[-1] in ',-':
        return pattern[1:-1]
    return pattern[1:]


def W3CDate(tm=None):
    """ Return time string according to http://www.w3.org/TR/NOTE-datetime
    """
    if not tm: tm = time.gmtime()
    return time.strftime("%Y-%m-%dT%H:%M:%S", tm) + "Z"

def dumpFormData(form):
    """ Dump the form data for debugging purposes
    """
    from Sycamore import wikiutil

    result = '<dt><strong>Form entries</strong></dt>'
    for k in form.keys():
        v = form.get(k, ["<empty>"])
        v = "|".join(v) 
        result = result + '<dd><em>%s</em>=%s</dd>' % (k, wikiutil.escape(v))

    return result

