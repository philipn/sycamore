# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Helper functions for WWW stuff

    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from Sycamore import config

_ua_match = None

def isIpAddress(addr):
    """
    XXX THIS ONLY SUPPORTS IPv4
    """
    try:
	s_addr = map(int, addr.split('.'))
	is_octet = True
	for o in s_addr:
	    is_octet = is_octet and 0 <= o and o <= 255

	return len(s_addr) == 4 and is_octet
    except ValueError:
	return False

def isSpiderAgent(**kw):
    """ Return True if user agent appears to be a spider.
    """
    if not config.ua_spiders:
        return 0

    request = kw.get('request', None)
    if request:
        ua = request.getUserAgent()
    else:
        ua = kw.get('ua', None)
    
    if not ua:
        return 0

    global _ua_match
    if _ua_match is None:
        import re
        _ua_match = re.compile(config.ua_spiders, re.I)

    return _ua_match.search(ua) is not None


def parseQueryString(qstr):
    """ Parse a querystring "key=value&..." into a dict.
    """
    import urllib

    values = {}
    pairs = qstr.split('&') # XXX
    for pair in pairs:
        key, val = pair.split('=')
        values[urllib.unquote(key)] = urllib.unquote(val)

    return values


def makeQueryString(qstr={}, **kw):
    """ Make a querystring from a dict. Keyword parameters are
        added as-is, too.

        If a string is passed in, it's returned verbatim and
        keyword parameters are ignored.
    """
    if isinstance(qstr, type({})):
        import urllib

        qstr = '&amp;'.join([
            urllib.quote_plus(name) + "=" + urllib.quote_plus(str(value))
                for name, value in qstr.items() + kw.items()
        ])

    return qstr


def getIntegerInput(request, fieldname, default=None, minval=None, maxval=None):
    """ Get an integer value from a request parameter. If the value
        is out of bounds, it's made to fit into those bounds.

        Returns `default` in case of errors (not a valid integer, or field
        is missing).
    """
    try:
        result = int(request.form[fieldname][0])
    except (KeyError, ValueError):
        return default
    else:
        if minval is not None:
            result = max(result, minval)
        if maxval is not None:
            result = min(result, maxval)
        return result


def getLinkIcon(request, formatter, scheme):
    """ Get icon for fancy links, or '' if user doesn't want them.
    """

    if scheme in ["mailto", "news", "telnet", "ftp", "file"]:
        icon = scheme
    else:
        icon = "www"

    return request.theme.make_icon(icon)

def makeSelection(name, values, selectedval=None):
    """ Make a HTML <select> element named `name` from a value list.
        The list can either be a list of strings, or a list of
        (value, label) tuples.

        `selectedval` is the value that should be pre-selected.
    """
    from Sycamore.widget import html

    result = html.SELECT(name=name)
    for val in values:
        if not isinstance(val, type(())):
            val = (val, val)
        result.append(html.OPTION(
            value=val[0], selected=(val[0] == selectedval))
            .append(html.Text(val[1]))
        )

    return result

