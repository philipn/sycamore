# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - DeletePage action

    This action allows you to delete a page. Note that the standard
    config lists this action as excluded!

    @copyright: 2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import config, wikiutil
from LocalWiki.PageEditor import PageEditor


def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)

    # be extra paranoid in dangerous actions
    if actname in config.excluded_actions \
            or not request.user.may.edit(pagename) \
            or not request.user.may.delete(pagename):
        return page.send_page(request,
            msg = _('You are not allowed to delete this page.'))


    # check whether page exists at all
    if not page.exists():
        return page.send_page(request,
            msg = _('This page is already deleted or was never created!'))

    # check whether the user clicked the delete button
    if request.form.has_key('button') and request.form.has_key('ticket'):
        # check whether this is a valid deletion request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
            return page.send_page(request,
                msg = _('Please use the interactive user interface to delete pages!'))

        # Delete the page
        page.deletePage(request.form.get('comment', [''])[0])

        return page.send_page(request,
                msg = _('Page "%s" was successfully deleted!') % (pagename,))

    # send deletion form
    url = page.url(request)
    ticket = _createTicket()
    querytext = _('Really delete this page?')
    button = _('Delete')
    comment_label = _("Optional reason for the deletion")
    formhtml = """
<form method="GET" action="%(url)s">
<strong>%(querytext)s</strong>
<input type="hidden" name="action" value="%(actname)s">
<input type="hidden" name="ticket" value="%(ticket)s">
<input type="submit" name="button" value="%(button)s">
<p>
%(comment_label)s<br>
<input type="text" name="comment" size="60" maxlength="80">
</form>""" % {
    'url': url,
    'querytext': querytext,
    'actname': actname,
    'ticket': ticket,
    'button': button,
    'comment_label': comment_label,
}

    return page.send_page(request, msg=formhtml)


def _createTicket(tm = None):
    """Create a ticket using a site-specific secret (the config)"""
    import sha, time, types
    ticket = (tm or "%010x" % time.time())
    digest = sha.new()
    digest.update(ticket)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return ticket + '.' + digest.hexdigest()


def _checkTicket(ticket):
    """Check validity of a previously created ticket"""
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return ticket == ourticket

