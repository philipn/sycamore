"""
    Sycamore - RenamePage action

    This action allows you to rename a page.

    Based on the DeletePage action by J?rgen Hermann <jh@web.de>

    @copyright: 2002-2004 Michael Reinsch <mr@uue.org>
    @
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import config, user, wikiutil, wikiaction, caching
from Sycamore.PageEditor import PageEditor
from Sycamore.Page import Page
import time, os, urllib

def copy_images(oldpagename, newpagename, request):
  # copies images from oldpagename to newpagename
  # keeps the images on oldpagename for manual deletion
  # if there is an image on the page newpagename that has the same name as an image on oldpagename,
  # then the image from newpagename superseeds the old image, and the old image is deleted (but kept
  # as a deleted image as per usual delete images/is accessable via the info tab)
  from Sycamore.action.Files import get_filelist
  old_page_files = get_filelist(request, oldpagename)
  new_page_files = get_filelist(request, newpagename)
  for filename in old_page_files:
    request.cursor.execute("SELECT image, uploaded_time, uploaded_by, uploaded_by_ip, xsize, ysize, attached_to_pagename_propercased from images where name=%(filename)s and attached_to_pagename=%(oldpagename)s", {'filename':filename, 'oldpagename':oldpagename.lower()})
    result = request.cursor.fetchone()
    if result: 
       old_page_file_dict = {'filename': filename, 'image': result[0], 'uploaded_time': result[1], 'uploaded_by': result[2], 'attached_to_pagename_propercased': result[6], 'uploaded_by_ip': result[3], 'xsize': result[4], 'ysize': result[5], 'newpagename': newpagename.lower(), 'newpagename_propercased': Page(newpagename, request).proper_name(), 'timenow': time.time(), 'userid': request.user.id, 'userip': request.remote_addr}
       if filename not in new_page_files:
               request.cursor.execute("INSERT into images (name, image, uploaded_time, uploaded_by, uploaded_by_ip, xsize, ysize, attached_to_pagename, attached_to_pagename_propercased) values (%(filename)s, %(image)s, %(uploaded_time)s, %(uploaded_by)s, %(uploaded_by_ip)s, %(xsize)s, %(ysize)s, %(newpagename)s, %(newpagename_propercased)s)", old_page_file_dict, isWrite=True)
       else:
         request.cursor.execute("INSERT into oldImages (name, image, uploaded_time, uploaded_by, uploaded_by_ip, xsize, ysize, attached_to_pagename, attached_to_pagename_propercased, deleted_by, deleted_by_ip, deleted_time) values (name=%(filename)s, (SELECT image from images where name=%(filename)s and attached_to_pagename=%(newpagename)s), (SELECT uploaded_time from images where name=%(filename)s and attached_to_pagename=%(newpagename)s), (SELECT uploaded_by from images where name=%(filename)s and attached_to_pagename=%(newpagename)s), (SELECT uploaded_by_ip from images where name=%(filename)s and attached_to_pagename=%(newpagename)s), (SELECT xsize from images where name=%(filename)s and attached_to_pagename=%(newpagename)s), (SELECT ysize from images where name=%(filename)s and attached_to_pagename=%(pagename)s), %(newpagename)s, %(newpagename_propercased)s, deleted_by=%(userid)s, deleted_by_ip=%(userip)s, deleted_time=%(timenow)s)", old_page_file_dict, isWrite=True)
         request.cursor.execute("SELECT name from images where name=%(filename)s and attached_to_pagename=%(newpagename)s", old_page_file_dict)
         result = request.cursor.fetchone()
         if result:
           request.cursor.execute("UPDATE images set image=%(image)s, uploaded_time=%(uploaded_time)s, uploaded_by=%(uploaded_by)s, uploaded_by_ip=%(uploaded_by_ip)s, xsize=%(xsize)s, ysize=%(ysize)s where name=%(filename) and attached_to_pagename=%(newpagename)", old_page_file_dict, isWrite=True)
         else:
           request.cursor.execute("INSERT into images (name, image, uploaded_time, uploaded_by, uploaded_by_ip, xsize, ysize, attached_to_pagename, attached_to_pagename_propercased) values (%(filename)s, %(image)s, %(uploaded_time)s, %(uploaded_by)s, %(uploaded_by_ip)s, %(xsize)s, %(ysize)s, %(newpagename)s, %(newpagename_propercased)s)", old_page_file_dict, isWrite=True)

 
def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)
    pagetext = page.get_raw_body()
    msg = ''

    # be extra paranoid in dangerous actions
    if actname in config.excluded_actions or \
        not request.user.may.edit(page) or not request.user.may.delete(page):
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
            try:
              newpage = PageEditor(newpagename, request)
            except Page.ExcessiveLength, msg:
              return Page(pagename, request).send_page(msg=msg)

            if len(renamecomment) > wikiaction.MAX_COMMENT_LENGTH:
               msg = _('Comments must be less than %s characters long.' % wikiaction.MAX_COMMENT_LENGTH)
            elif len(newpagename) > Page.MAX_PAGENAME_LENGTH:
               msg = _('Page names must be less than %s characters long.' % Page.MAX_PAGENAME_LENGTH)

            # check whether a page with the new name already exists
            elif newpage.exists() and not (newpagename.lower() == pagename.lower()):
                msg = _('A page with the name "%s" already exists!') % (newpagename,)

            elif not wikiaction.isValidPageName(newpagename):        # pi Fri Dec 24 05:57:42 EST 2004
                msg = _('Invalid pagename: Only the characters A-Z, a-z, 0-9, "$", "&", ",", ".", "!", "\'", ":", ";", " ", "/", "-", "(", ")" are allowed in page names.')
		
            # we actually do a rename!
            else:
                if renamecomment: renamecomment = " (" + renamecomment + ")"
                #replace_in_xml(pagename, newpagename)
                if newpagename.lower() != pagename.lower(): 
                    page.saveText("#redirect %s" % newpagename, '0', comment='Renamed to "%s"' % newpagename, action='RENAME')
		    # copy images over
		    copy_images(pagename, newpagename, request)

                newpage.saveText(pagetext, '0', comment='Renamed from "%s"%s' % (pagename, renamecomment), action="RENAME", proper_name=newpagename)

		# clear cache so images show up
		key = newpagename
		cache = caching.CacheEntry(key, request)
		cache.clear()

                msg = _('Page "%s" was successfully renamed to "%s"!') % (pagename,newpagename)
		if newpagename.lower() != pagename.lower():
		  # check favorites because the redirect will process before the bookmarks get updated
                  if request.user.valid: request.user.checkFavorites(pagename.lower())

		  request.http_redirect('%s/%s?action=show&redirect=%s' % (
                    request.getScriptname(),
                    wikiutil.quoteWikiname(newpagename),
                    urllib.quote_plus(pagename, ''),))
		
		  return
                else:
		  return newpage.send_page(msg)


    else:
        # send renamepage form
        url = page.url()
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

    return page.send_page(msg)

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

