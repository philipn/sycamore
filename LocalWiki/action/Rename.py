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
import time

def _add_to_index(page_n, pagetext, id):
   """
   more specific version of add_to_index.
   this version is designed to over-ride an existing entry, just for our little rename action.
   """
   from popen2 import popen2

   output, input = popen2(config.app_dir + "/index_page" + " " + config.app_dir + "/search_db %s %s" % (id, page_n))
   input.write(pagetext + '\n')
   input.close()
   output.close()
   # write to the title index as well
   output, input = popen2(config.app_dir + "/index_page" + " " + config.app_dir + "/title_search_db %s %s" % (id, page_n))
   input.write(wikiutil.unquoteWikiname(page_n) + '\n')
   input.close()
   output.close()


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
            comment = request.form.get('comment', [''])[0]
            newpagename = request.form.get('newpagename')[0]
            newpage = PageEditor(newpagename, request)

            # check whether a page with the new name already exists
            if newpage.exists():
                msg = _('A page with the name "%s" already exists!') % (newpagename,)

	    elif not wikiaction.isValidPageName(newpagename):        # pi Fri Dec 24 05:57:42 EST 2004
                msg = _('Invalid pagename: Only the characters A-Z, a-z, 0-9, "$", "&", ",", ".", "!", "\'", ":", ";", " ", "/", "-", "(", ")" are allowed in page names.')
		
            else:
                import os,re
                # Because we're doing file-system stuff, we need to covert the special characters to the lame _20 b.s.
                written_pagename = wikiutil.quoteFilename(pagename)
                written_newpagename = wikiutil.quoteFilename(newpagename)
 
                # move the backups (revision history)
                page_list = os.listdir(config.data_dir + "/backup/")
                for p in page_list:
                   m = re.match(written_pagename + "\.(?P<backup_id>[0-9]+)", p)
                   if m:
                      os.rename(config.data_dir + "/backup/" + written_pagename + "." + m.group("backup_id"), config.data_dir + "/backup/" + written_newpagename + "." + m.group("backup_id"))

                # move the rest
                # check to see if the directory for the new name already exists and if so lets preserve the existing attachments and history
                if os.path.exists(config.data_dir + "/pages/" + written_newpagename):
		   os.spawnl(os.P_WAIT, 'mv', 'mv', config.data_dir + "/pages/" + written_pagename + "/*", config.data_dir + "/pages/" + written_newpagename + "/" )
		else:
		   #os.mkdir(config.data_dir + "/pages/" + written_newpagename)
                   os.rename(config.data_dir + "/pages/" + written_pagename, config.data_dir + "/pages/" + written_newpagename)
                os.rename(config.data_dir + "/text/" + written_pagename, config.data_dir + "/text/" + written_newpagename)

                # Now we have to update the editlog with the new name.  This is a really terrible way to do this, but for some reason LocalWiki parses the entire eventlog whenever it wants to get information on the revision history of a particular page.  So it goes.  Eventually we'd like to make this more robust, obviously.
                # We need to make sure when we open the editlog it's not already open by moin someplace else -- so lets do some simple locking in agreement with the editlog object.
#               import time
#               while editlog_is_locked():
#                  time.sleep(0.3)

                editlog_replace_pagename(written_pagename, written_newpagename)
                replace_in_xml(pagename, newpagename)

                # Note the rename in the editlog (for Recent Changes)
                log = editlog.EditLog()

		if newpagename.lower() != pagename.lower(): 
                	log.add(request, pagename, request.remote_addr, time.time(),
    				('Renamed to "%s"' % newpagename), 'RENAME')
                if comment:
                   log.add(request, newpagename, request.remote_addr, time.time(),
    ('Renamed from "%s" (%s)' % (pagename, comment)), 'RENAME')
                else:
                   log.add(request, newpagename, request.remote_addr, time.time(),
    ('Renamed from "%s"' % pagename), 'RENAME')

		"""
                # For search indexing -- change the old pagename to the new pagename in the index_id_file
                id_file = open(config.app_dir + "/index_id_file","r")
                id_table = []
                page_field = (id_file.readline()).strip('\n')
                while page_field:
                        id_field = (id_file.readline()).strip('\n')
                        id_table.append((page_field, id_field))
                        page_field = (id_file.readline()).strip('\n')
                id_file.close()
                id_file = open(config.app_dir + "/index_id_file","w")
                id = 0
                for i in id_table:
                        if i[0] == wikiutil.quoteWikiname(pagename):
                                id_file.write(wikiutil.quoteWikiname(newpagename) + '\n')
                                id_file.write((i[1]).strip('\n') + '\n')
                                id = i[1]
                                continue
                        id_file.write(i[0] + '\n')
                        id_file.write(i[1] + '\n')

                # Add the (now new) page to the index
                _add_to_index(wikiutil.quoteWikiname(newpagename), pagetext, id)
		"""
		# have to remove the old page from the index otherwise it might appear twice (also removes from our id dict)
	        os.spawnl(os.P_WAIT, config.app_dir + '/remove_from_index', config.app_dir + '/remove_from_index', wikiutil.quoteWikiname(pagename))
		# refresh cache so the user sees the right version of the page
		from LocalWiki import caching
        	cache = caching.CacheEntry("Page.py", written_pagename + ".text_html")
        	cache.remove()
                cache = caching.CacheEntry("Page.py", written_newpagename + ".text_html")
                cache.remove()

		os.spawnl(os.P_WAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index', '%s' % wikiutil.quoteWikiname(newpage.page_name), '%s' % wikiutil.quoteFilename(newpage.get_raw_body()))

                # Make the old page redirect to the new page
                #oldpage_redirect = PageEditor(pagename, request)
                #oldpage_redirect.saveText("#redirect %s" % newpagename, '0', stripspaces=0, notify=1, comment=comment)

		if newpagename.lower() != pagename.lower():
                	redirecting_page = open(config.data_dir + "/text/" + written_pagename, "w")
                	redirecting_page.write("#redirect %s" % newpagename)
                	redirecting_page.close()

		import cPickle
		pdfile = open(config.data_dir + '/pagedict.pickle', 'r')
                pagedict = cPickle.load(pdfile)
                pdfile.close()
                pdfile= open(config.data_dir +'/pagedict.pickle' , 'w') # pickled pagedict
                if pagename.lower() == newpagename.lower():  del pagedict[pagename.lower()]
                pagedict[newpagename.lower()] = newpagename
                cPickle.dump(pagedict, pdfile, 2)
                pdfile.close()

                request.http_redirect('%s/%s' % ( 	# added by pi Fri Dec 24 05:43:13 EST 2004
                    request.getScriptname(),		#
                    wikiutil.quoteWikiname(pagename)))	#
                
                  

                msg = _('Page "%s" was successfully renamed to "%s"!') % (pagename,newpagename)


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

def editlog_is_locked():
    import os
    return os.path.exists(config.app_dir + "/tmp.editlog_is_locked")

def editlog_replace_pagename(old,new):
    import re,os

    #lock editlog
    #lock_file = open(config.app_dir + "/tmp.editlog_is_locked","w")

    new_file = []
    l_file = open(config.data_dir + "/editlog","r")
    line = l_file.readline()
    while line:
       line = re.sub("%s\t" % old, new + "\t", line)
       new_file.append(line)
       line = l_file.readline()
    
    l_file.close()
    new_log = open(config.data_dir + "/editlog","w")
    for l in new_file:
       new_log.write(l)
    new_log.close()

    #unlock editlog
    #lock_file.close()
    #os.remove(config.app_dir + "/tmp.editlog_is_locked") 

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

