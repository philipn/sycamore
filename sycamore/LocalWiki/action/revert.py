# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - revert action

    This action allows you to revert a page. Note that the standard
    config lists this action as excluded!

    @copyright: 2006 Philip Neustrom <philipn@gmail.com>, 2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import config, wikiutil
from LocalWiki.PageEditor import PageEditor
from LocalWiki.Page import Page


def execute(pagename, request):
    from LocalWiki.PageEditor import PageEditor
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = Page(pagename, request)
    if not request.user.may.revert(page):
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
	  entered_comment = request.form['comment'][0]
	  if len(entered_comment) > 80:
	    return page.send_page(msg = _('Please use the interfactive user interface to revert pages!'))
          if entered_comment:
	    f=open('test.txt','w')
	    comment = 'v%sc%s' % (str(version), entered_comment)
	    f.write(comment)
	    f.close()
	  else:
	    comment = 'v%s' % str(version)
        else:
          return
              
        pg = PageEditor(pagename, request)
       
        try:
            pg.saveText(oldpg.get_raw_body(), '0',
                stripspaces=0, notify=1, comment=comment, action="SAVE/REVERT")
	    savemsg = _("Page reverted to version %s" % version)
        except pg.SaveError:
            savemsg = _("An error occurred while reverting the page.")

        #request.reset()
       
        # clear req cache so user sees proper page state (exist)
        request.req_cache['pagenames'][pagename] = pagename
        return pg.send_page(msg=savemsg)

	#########


    # get version
    if request.form.has_key('version'):
       version = request.form['version'][0]
    else:
      return page.send_page(msg= _('Please use the interactive user interface to revert pages!'))

    # send revert form
    url = page.url()
    ticket = _createTicket()
    button = _('Revert')
    comment_label = _("Reason for the revert:")
    formhtml = """
<form method="GET" action="%(url)s">
<input type="hidden" name="action" value="%(actname)s">
<input type="hidden" name="ticket" value="%(ticket)s">
<input type="hidden" name="version" value="%(version)s">
<p>
%(comment_label)s<br>
<input type="text" name="comment" size="60" maxlength="80">
<input type="submit" name="button" value="%(button)s">
</form>""" % {
    'url': url,
    'actname': actname,
    'ticket': ticket,
    'button': button,
    'comment_label': comment_label,
    'version': version
}

    return page.send_page(msg=formhtml)


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

