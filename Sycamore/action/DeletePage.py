# -*- coding: utf-8 -*-
"""
    Sycamore - DeletePage action

    This action allows you to delete a page. Note that the standard
    acl lists this action as excluded!

    @copyright: 2005-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import config
from Sycamore import wikiutil
from Sycamore import wikiaction
from Sycamore.PageEditor import PageEditor

def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)
    permanent = False
    showrc = True

    msg = ''

    # be extra paranoid in dangerous actions
    if actname in config.excluded_actions \
            or not request.user.may.edit(page) \
            or not request.user.may.delete(page):
        return page.send_page(
            msg = _('You are not allowed to delete this page.'))


    # check whether page exists at all
    if not page.exists():
        return page.send_page(
            msg = _('This page is already deleted or was never created!'))

    # check whether the user clicked the delete button
    if request.form.has_key('button') and request.form.has_key('ticket'):
        # check whether this is a valid deletion request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
            return page.send_page(
                msg = _('Please use the interactive user interface '
                        'to delete pages!'))

        # Delete the page
        comment = request.form.get('comment', [''])[0]
        if len(comment) > wikiaction.MAX_COMMENT_LENGTH:
            msg = ("Comments must be less than %s characters long." %
                   wikiaction.MAX_COMMENT_LENGTH)
            return page.send_page(msg)

        if (request.form.has_key('permanent') and
            request.form['permanent'][0] and request.user.may.admin(page)):
            permanent = True
            if request.form.has_key('noshowrc') and request.form['noshowrc'][0]:
                showrc = False 

        msg = page.deletePage(comment, permanent=permanent, showrc=showrc)

        return page.send_page(
                msg = _('Page "%s" was successfully deleted!') % (pagename,))

    # send deletion form
    url = page.url()
    ticket = _createTicket()
    button = _('Delete')
    comment_label = _("Reason for deletion:")

    if request.user.may.admin(page):
        admin_label = (
            """<p>Permanently remove old versions: <input type="checkbox" """
            """id="noshowrctoggle" name="permanent" value="1">\n"""
            """<span id="noshowrc">Don't log on Recent Changes: """
            '<input type="checkbox" name="noshowrc" value="1"></span></p>\n'
            '<script type="text/javascript">\n'
            "document.getElementById('noshowrc').style.visibility = 'hidden';"
            "document.getElementById('noshowrc').style.paddingLeft = '1em';"
            "document.getElementById('noshowrctoggle').onclick = "
               "function () {"
                 "document.getElementById('noshowrc').style.visibility = "
                     "document.getElementById('noshowrctoggle').checked ? "
                         "'visible' : 'hidden';"
               "}"
            "</script>")
    else:
        admin_label = ''
    formhtml = (
        '<form method="GET" action="%(url)s">\n'
        '<input type="hidden" name="action" value="%(actname)s">\n'
        '<input type="hidden" name="ticket" value="%(ticket)s">\n'
        '<p>\n'
        '%(comment_label)s\n'
        '</p>\n'
        '<p>\n'
        '<input type="text" name="comment" size="60" maxlength="80">\n'
        '<input type="submit" name="button" value="%(button)s">\n'
        '</p>\n'
        '%(admin_label)s\n'
        '</form>' %
            {
            'url': url,
            'actname': actname,
            'ticket': ticket,
            'button': button,
            'comment_label': comment_label,
            'admin_label': admin_label,
            })

    return page.send_page(msg=formhtml)

def _createTicket(tm = None):
    """
    Create a ticket using a site-specific secret (the config)
    """
    import hashlib, time, types
    ticket = (tm or "%010x" % time.time())
    digest = hashlib.new('sha1')
    digest.update(ticket)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return ticket + '.' + digest.hexdigest()

def _checkTicket(ticket):
    """
    Check validity of a previously created ticket
    """
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return ticket == ourticket
