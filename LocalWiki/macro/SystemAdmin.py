# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - System Administration

    Web interface to do LocalWiki system administration tasks.

    @copyright: 2001, 2003 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from LocalWiki import wikiutil
from LocalWiki.util import pysupport
from LocalWiki.userform import do_user_browser
from LocalWiki.action.AttachFile import do_admin_browser

Dependencies = ["time"]

def execute(macro, args):
    _ = macro.request.getText

    # do not show system admin to not admin users
    # !!! add ACL stuff here - meanwhile do this ugly hack:
    try: 
        if not macro.request.user.may.admin(macro.formatter.page.page_name):
            return ''
    except AttributeError: # we do not have _admin in SecurityPolicy, so we give up
        return ''

    result = []
    _MENU = {
        'attachments': (("File attachment browser"), do_admin_browser),
        'users': (("User account browser"), do_user_browser),
    }
    choice = macro.request.form.get('sysadm', [None])[0]

    # XXX !! unfinished!
    if 0:
        result = wikiutil.link_tag(macro.request,
            "?action=export", _("Download XML export of this wiki"))
        if pysupport.isImportable('gzip'):
            result += " [%s]" % wikiutil.link_tag(macro.request,
            "?action=export&compression=gzip", "gzip")

    # create menu
    menuitems = [(label, id) for id, (label, handler) in _MENU.items()]
    menuitems.sort()
    for label, id in menuitems:
        if id == choice:
            result.append(macro.formatter.strong(1))
            result.append(macro.formatter.text(label))
            result.append(macro.formatter.strong(0))
        else:
            result.append(wikiutil.link_tag(macro.request,
                "%s?sysadm=%s" % (macro.formatter.page.page_name, id), label))
        result.append('<br>')
    result.append('<br>')

    # add chosen content
    if _MENU.has_key(choice):
        result.append(_MENU[choice][1](macro.request))

    return macro.formatter.rawHTML(''.join(result))

