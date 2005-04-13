"""
    LocalWiki - RenamePage action

    This action allows you to rename a page.

    Based on the DeletePage action by J?rgen Hermann <jh@web.de>

    @copyright: 2002-2004 Michael Reinsch <mr@uue.org>
    @
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import config, user, wikiutil, wikiaction
from LocalWiki.logfile import editlog
from LocalWiki.PageEditor import PageEditor
import time, os

def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)
    pagetext = page.get_raw_body()
    msg = ''

    # be extra paranoid in dangerous actions
    if actname in config.excluded_actions or \
        not request.user.may.edit(pagename) or not request.user.may.delete(pagename):
            msg = _('You are not allowed to rename pages in this wiki!')

    # check whether page exists at all
    elif not page.exists():
        msg = _('This page is already deleted or was never created!')

    # check whether the user clicked the delete button
    elif request.form.has_key('button') and \
        request.form.has_key('newpagename') and request.form.has_key('ticket'):
        # check whether this is a valid renaming request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
            msg = _('Please use the interactive user interface to rename pages!')
        else:
            renamecomment = request.form.get('comment', [''])[0]
            newpagename = request.form.get('newpagename')[0]
            newpage = PageEditor(newpagename, request)

            # check whether a page with the new name already exists
            if newpage.exists():
                msg = _('A page with the name "%s" already exists!') % (newpagename,)

            elif not wikiaction.isValidPageName(newpagename):        # pi Fri Dec 24 05:57:42 EST 2004
                msg = _('Invalid pagename: Only the characters A-Z, a-z, 0-9, "$", "&", ",", ".", "!", "\'", ":", ";", " ", "/", "-", "(", ")" are allowed in page names.')
		
            # we actually do a rename!
            else:
                if renamecomment: renamecomment = " (" + renamecomment + ")"
                replace_in_xml(pagename, newpagename)
                if newpagename.lower() != pagename.lower(): 
                    page.saveText("#redirect %s" % newpagename, '0', comment='Renamed to "%s"' % newpagename, action='RENAME')
                    os.spawnl(os.P_NOWAIT, config.app_dir + '/remove_from_index', config.app_dir + '/remove_from_index', wikiutil.quoteFilename(pagename))
                else:
                    page.deletePage('Renamed to "%s"' % newpagename)

                newpage.saveText(pagetext, '0', comment="Renamed from %s%s" % (pagename, renamecomment), action="RENAME")

                if os.path.exists(config.data_dir + '/pages/' + wikiutil.quoteFilename(pagename) + '/attachments'):
                    if os.path.exists(config.data_dir + '/pages/' + wikiutil.quoteFilename(newpagename) + '/attachments'):
                        # --reply=no flag means when there are two files with the same name we just don't move it and let the user figure that out.
                        # interesting fact:  we have to use bash here because the shell is the one that expands the '*'
                        os.spawnlp(os.P_NOWAIT, 'bash', 'bash', '-c', 'cp --reply=no ' + config.data_dir + '/pages/' + wikiutil.quoteFilename(pagename) + '/attachments/* ' + config.data_dir + '/pages/' + wikiutil.quoteFilename(newpagename) + '/attachments/')
                    else:
                        os.spawnlp(os.P_NOWAIT, 'cp', 'cp', '-r', config.data_dir + '/pages/' + wikiutil.quoteFilename(pagename) + '/attachments', config.data_dir + '/pages/' + wikiutil.quoteFilename(newpagename) + '/')

                msg = _('Page "%s" was successfully renamed to "%s"!') % (pagename,newpagename)
                request.http_redirect('%s/%s' % ( 	# added by pi Fri Dec 24 05:43:13 EST 2004
                    request.getScriptname(),		#
                    wikiutil.quoteWikiname(pagename)))	#



    else:
        # send renamepage form
        url = page.url(request)
        ticket = _createTicket()
        button = _('Rename')
        newname_label = _("New name")
        comment_label = _("Optional reason for the renaming")
        msg = """
<form method="GET" action="%(url)s">
<input type="hidden" name="action" value="%(actname)s">
<input type="hidden" name="ticket" value="%(ticket)s">
%(newname_label)s <input type="text" name="newpagename" size="20" value="%(pagename)s">
<input type="submit" name="button" value="%(button)s">
<p>
%(comment_label)s<br>
<input type="text" name="comment" size="60" maxlength="80">
</p>
</form>
<p>Note that the old page name will re-direct to the new page. This means you don't <i>have</i> to update links to the new name, but you ought to. (Find links to change by doing a search for the old page name)</p>""" % locals()

    return page.send_page(request, msg)

def replace_in_xml(old,new):
    import re,os,string

    #lock editlog
    new_file = []
    old = old.replace("&amp;", "&")
    new = new.replace("&", "&amp;") 
    l_file = open(config.web_root + config.web_dir + "/points.xml","r")
    line = l_file.readline()
    while line:
       line = line.replace('"%s"' % old, '"%s"' % new)
       new_file.append(line)
       line = l_file.readline()
    
    l_file.close()
    new_xml = open(config.web_root + config.web_dir + "/points.xml","w")
    for l in new_file:
       new_xml.write(l)
    new_xml.close()
     

def _createTicket(tm = None):
    """Create a ticket using a site-specific secret (the config)"""
    import sha, time, types
    ticket = tm or "%010x" % time.time()
    digest = sha.new()
    digest.update(ticket)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return "%s.%s" % (ticket, digest.hexdigest())


def _checkTicket(ticket):
    """Check validity of a previously created ticket"""
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return ticket == ourticket

