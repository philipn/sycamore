# -*- coding: iso-8859-1 -*-
"""
    Sycamore - revert action

    This action allows you to revert a page. Note that the standard
    config lists this action as excluded!

    @copyright: 2006 Philip Neustrom <philipn@gmail.com>, 2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import config, wikiutil, wikiaction, caching
from Sycamore.PageEditor import PageEditor
from Sycamore.Page import Page

def delete_all_newer(oldpage, request):
    version_date = oldpage.prev_date
    d = { 'pagename':oldpage.page_name, 'version_date':version_date, 'wiki_id':request.config.wiki_id }
    caching.deleteNewerPageInfo(oldpage.page_name, version_date, request)
    request.cursor.execute("DELETE from allPages where name=%(pagename)s and editTime>%(version_date)s and wiki_id=%(wiki_id)s", d, isWrite=True)

def execute(pagename, request):
    from Sycamore.PageEditor import PageEditor
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = Page(pagename, request)
    permanent = False
    if not request.user.may.edit(page):
        return page.send_page(
            msg = _('You are not allowed to revert this page!'))

        
    # check whether the user clicked the delete button
    if request.form.has_key('button') and request.form.has_key('ticket'):
        # check whether this is a valid deletion request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
            return page.send_page(
                msg = _('Please use the interactive user interface to revert pages!'))

        # revert the page
        #########
        if request.form.has_key('version'):
          version = int(request.form['version'][0])
          oldpg = Page(pagename, request, version=version)
          date = oldpg.prev_date
          if request.form.has_key('comment'):
            entered_comment = request.form['comment'][0]
          else:
            entered_comment = ''
          if len(entered_comment) > wikiaction.MAX_COMMENT_LENGTH:
            return page.send_page(msg = _('Comments must be less than %s characters long.' % wikiaction.MAX_COMMENT_LENGTH))
          else:
            comment = 'v%s' % str(version)

          comment = "%sc%s" % (comment, entered_comment)
        else:
          return

        if request.form.has_key('permanent') and request.form['permanent'][0] and request.user.may.admin(page):
            permanent = True
              
        pg = PageEditor(pagename, request)
      
        if permanent:
            delete_all_newer(oldpg, request)  
       
        try:
            pg.saveText(oldpg.get_raw_body(), '0',
                stripspaces=0, notify=1, comment=comment, action="SAVE/REVERT")
            savemsg = _("Page reverted to version %s" % version)
        except pg.Unchanged:
            savemsg = _("The current page is the same as the older page you wish to revert to!")
        except pg.SaveError:
            savemsg = _("An error occurred while reverting the page.")

        # clear req cache so user sees proper page state (exist)
        request.req_cache['pagenames'][(pagename.lower(), request.config.wiki_name)] = pagename
        return pg.send_page(msg=savemsg)

        #########


    # get version
    if request.form.has_key('version'):
       version = request.form['version'][0]
    else:
      return page.send_page(msg= _('Please use the interactive user interface to revert pages!'))

    oldpg = Page(pagename, request, version=version)
    # send revert form
    url = page.url()
    ticket = _createTicket()
    button = _('Revert')
    comment_label = _("Reason for the revert:")
    if request.user.may.admin(page):
      admin_label = """<p>Permanently remove newer versions: <input type="checkbox" name="permanent" value="1"></p>"""
    else:
      admin_label = ''

    formhtml = """
<form method="GET" action="%(url)s">
<input type="hidden" name="action" value="%(actname)s">
<input type="hidden" name="ticket" value="%(ticket)s">
<input type="hidden" name="version" value="%(version)s">
<p>
%(comment_label)s
</p>
<input type="text" name="comment" size="60" maxlength="80">
<input type="submit" name="button" value="%(button)s">
%(admin_label)s
</form>""" % {
    'url': url,
    'actname': actname,
    'ticket': ticket,
    'button': button,
    'comment_label': comment_label,
    'version': version,
    'admin_label': admin_label,
}

    return oldpg.send_page(msg=formhtml)


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

