""" Sycamore - RenamePage action

    This action allows you to rename a page.

    Based on the DeletePage action by J?rgen Hermann <jh@web.de>

    @copyright: 2005-2007 Philip Neustrom <philipn@gmail.com>
    @copyright: 2002-2004 Michael Reinsch <mr@uue.org>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import time
import os
import urllib

from Sycamore import config, user, wikiutil, wikiaction, caching, wikidb
from Sycamore import config
from Sycamore import user
from Sycamore import wikiutil
from Sycamore import wikiaction
from Sycamore import caching
from Sycamore import wikidb

from Sycamore.PageEditor import PageEditor
from Sycamore.Page import Page, MAX_PAGENAME_LENGTH

def copy_files(oldpagename, newpagename, request):
    """
    copies files from oldpagename to newpagename.
    keeps the files on oldpagename for manual deletion.
    if there is an file on the page newpagename that has the same name as a
    file on oldpagename, then the file from newpagename superseeds the old
    file, and the old file is deleted (but kept as a deleted file as per usual
    delete file/is accessable via the info tab)
    """
    from Sycamore.action.Files import get_filelist
    old_page_files = get_filelist(request, oldpagename)
    new_page_files = get_filelist(request, newpagename)
    for filename in old_page_files:
        is_image = wikiutil.isImage(filename)
        request.cursor.execute(
            """SELECT file, uploaded_time, uploaded_by, uploaded_by_ip,
                      attached_to_pagename_propercased from files
                      where name=%(filename)s and
                            attached_to_pagename=%(oldpagename)s and
                            wiki_id=%(wiki_id)s""",
            {'filename':filename, 'oldpagename':oldpagename.lower(),
             'wiki_id':request.config.wiki_id})
        result = request.cursor.fetchone()

        if result: 
            old_page_file_dict = {
                'filename': filename,
                'uploaded_time': result[1],
                'uploaded_by': result[2],
                'attached_to_pagename_propercased': result[4],
                'oldpagename': oldpagename.lower(),
                'uploaded_by_ip': result[3],
                'newpagename': newpagename.lower(),
                'newpagename_propercased': Page(newpagename,
                                                request).proper_name(),
                'timenow': time.time(),
                'userid': request.user.id,
                'userip': request.remote_addr,
                'wiki_id': request.config.wiki_id
            }
            if is_image:
                request.cursor.execute(
                    """SELECT xsize, ysize from imageInfo
                       where name=%(filename)s and
                             attached_to_pagename=%(oldpagename)s and
                             wiki_id=%(wiki_id)s""",
                    {'filename': filename, 'oldpagename': oldpagename.lower(),
                     'wiki_id': request.config.wiki_id})
                result = request.cursor.fetchone()
                if result:
                    old_page_file_dict['xsize'] = result[0]
                    old_page_file_dict['ysize'] = result[1]
              
            if filename not in new_page_files:
                request.cursor.execute(
                    """INSERT into files
                       (name, file, uploaded_time, uploaded_by, uploaded_by_ip,
                        attached_to_pagename, attached_to_pagename_propercased,
                        wiki_id)
                       values (%(filename)s,
                               (select file from files
                                where name=%(filename)s and
                                      attached_to_pagename=%(oldpagename)s and
                                      wiki_id=%(wiki_id)s
                               ),
                               %(uploaded_time)s, %(uploaded_by)s,
                               %(uploaded_by_ip)s, %(newpagename)s,
                               %(newpagename_propercased)s, %(wiki_id)s
                              )""",
                    old_page_file_dict, isWrite=True)
                if is_image:
                    if old_page_file_dict.has_key('xsize'):
                         request.cursor.execute(
                            """INSERT into imageInfo
                               (name, attached_to_pagename, xsize, ysize,
                                wiki_id)
                               values (%(filename)s, %(newpagename)s,
                                       %(xsize)s, %(ysize)s, %(wiki_id)s) """,
                            old_page_file_dict, isWrite=True)

            else:
                request.cursor.execute(
                    """INSERT into oldFiles
                       (name, file, uploaded_time, uploaded_by, uploaded_by_ip,
                        attached_to_pagename, attached_to_pagename_propercased,
                        deleted_by, deleted_by_ip, deleted_time, wiki_id)
                       values (%(filename)s,
                               (SELECT file from files
                                where name=%(filename)s and
                                      attached_to_pagename=%(newpagename)s and
                                      wiki_id=%(wiki_id)s
                               ),
                               (SELECT uploaded_time from files
                                where name=%(filename)s and
                                      attached_to_pagename=%(newpagename)s and
                                      wiki_id=%(wiki_id)s
                               ),
                               (SELECT uploaded_by from files
                                where name=%(filename)s and
                                      attached_to_pagename=%(newpagename)s and
                                      wiki_id=%(wiki_id)s
                               ),
                               (SELECT uploaded_by_ip from files
                                where name=%(filename)s and
                                      attached_to_pagename=%(newpagename)s and
                                      wiki_id=%(wiki_id)s
                               ),
                               %(newpagename)s, %(newpagename_propercased)s,
                               %(userid)s, %(userip)s, %(timenow)s,
                               %(wiki_id)s)""",
                    old_page_file_dict, isWrite=True)

                # clear out cached version of image
                if config.memcache:
                    request.mc.delete("files:%s,%s" %
                                      (wikiutil.mc_quote(filename),
                                       wikiutil.mc_quote(newpagename.lower())))

                if is_image:
                    request.cursor.execute(
                        """INSERT into oldImageInfo
                           (name, attached_to_pagename, xsize, ysize,
                            uploaded_time, wiki_id)
                           values
                           (%(filename)s, %(newpagename)s,
                            (SELECT xsize from imageInfo
                             where name=%(filename)s and
                                   attached_to_pagename=%(newpagename)s and
                                   wiki_id=%(wiki_id)s
                            ),
                            (SELECT ysize from imageInfo
                             where name=%(filename)s and
                                   attached_to_pagename=%(newpagename)s and
                                   wiki_id=%(wiki_id)s
                            ),
                            (SELECT uploaded_time from files
                             where name=%(filename)s and
                                   attached_to_pagename=%(newpagename)s and
                                   wiki_id=%(wiki_id)s
                            ),
                            %(wiki_id)s)""",
                        old_page_file_dict, isWrite=True)
                    request.cursor.execute(
                        """DELETE from thumbnails
                           where name=%(filename)s and
                                 attached_to_pagename=%(newpagename)s and
                                 wiki_id=%(wiki_id)s""",
                        old_page_file_dict, isWrite=True)

                request.cursor.execute(
                    """SELECT name from files
                       where name=%(filename)s and
                             attached_to_pagename=%(newpagename)s and
                             wiki_id=%(wiki_id)s""", old_page_file_dict)
                result = request.cursor.fetchone()
                if result:
                    request.cursor.execute(
                        """UPDATE files set
                           file=(select file from files
                                 where name=%(filename)s and
                                       attached_to_pagename=%(oldpagename)s and
                                       wiki_id=%(wiki_id)s
                                ),
                           uploaded_time=%(timenow)s, uploaded_by=%(userid)s,
                           uploaded_by_ip=%(userip)s
                           where name=%(filename)s and
                                 attached_to_pagename=%(newpagename)s and
                                 wiki_id=%(wiki_id)s""",
                        old_page_file_dict, isWrite=True)
                    if is_image and old_page_file_dict.has_key('xsize'):
                        request.cursor.execute(
                            """UPDATE imageInfo set
                               xsize=%(xsize)s, ysize=%(ysize)s
                               where name=%(filename)s and
                                     attached_to_pagename=%(newpagename)s and
                                     wiki_id=%(wiki_id)s""",
                            old_page_file_dict, isWrite=True)
                else:
                    request.cursor.execute(
                        """INSERT into files
                           (name, file, uploaded_time, uploaded_by,
                            uploaded_by_ip, xsize, ysize, attached_to_pagename,
                            attached_to_pagename_propercased, wiki_id)
                           values
                           (%(filename)s,
                            (select file from files
                             where name=%(filename)s and
                                   attached_to_pagename=%(oldpagename)s and
                                   wiki_id=%(wiki_id)s
                            ),
                            %(uploaded_time)s, %(uploaded_by)s,
                            %(uploaded_by_ip)s, %(xsize)s, %(ysize)s,
                            %(newpagename)s, %(newpagename_propercased)s,
                            %(wiki_id)s)""", old_page_file_dict, isWrite=True)
                    if is_image and old_page_file_dict.has_key('xsize'):
                        request.cursor.execute(
                            """INSERT into imageInfo
                               (name, attached_to_pagename, xsize, ysize,
                                wiki_id) values
                               (%(filename)s, %(newpagename)s, %(xsize)s,
                                %(ysize)s, %(wiki_id)s)""",
                            old_page_file_dict, isWrite=True)

def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)
    pagetext = page.get_raw_body()
    msg = ''

    # be extra paranoid in dangerous actions
    if (actname in config.excluded_actions or not
        request.user.may.edit(page) or not request.user.may.delete(page)):
            msg = _('You are not allowed to rename pages in this wiki!')

    # check whether page exists at all
    elif not page.exists():
        msg = _('This page is already deleted or was never created!')

    # check whether the user clicked the delete button
    elif (request.form.has_key('button') and
          request.form.has_key('newpagename') and
          request.form.has_key('ticket')):
        # check whether this is a valid renaming request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
            msg = _('Please use the interactive user '
                    'interface to rename pages!')
        else:
            renamecomment = request.form.get('comment', [''])[0]
            # strip to ensure naming consistency
            newpagename = request.form.get('newpagename')[0].strip() 
            if newpagename == pagename:
                return Page(pagename, request).send_page(
                    msg="You can't rename a page to the name it already has!")
            try:
                newpage = PageEditor(newpagename, request)
            except Page.ExcessiveLength, msg:
                return Page(pagename, request).send_page(msg=msg)

            if len(renamecomment) > wikiaction.MAX_COMMENT_LENGTH:
                msg = _('Comments must be less than %s characters long.' %
                         wikiaction.MAX_COMMENT_LENGTH)
            elif len(newpagename) > MAX_PAGENAME_LENGTH:
               msg = _('Page names must be less than %s characters long.' %
                         MAX_PAGENAME_LENGTH)
            # check whether a page with the new name already exists
            elif (newpage.exists() and not
                  (newpagename.lower() == pagename.lower())):
                msg = _('A page with the name "%s" already exists!') % (
                        newpagename)

            elif not wikiaction.isValidPageName(newpagename):
                msg = _('Invalid pagename: Only the characters A-Z, a-z, 0-9, '
                        '"$", "&", ",", ".", "!", "\'", ":", ";", " ", "/", '
                        '"-", "(", ")" are allowed in page names.')
                
            # we actually do a rename!
            else:
                if renamecomment: renamecomment = " (" + renamecomment + ")"
                if newpagename.lower() != pagename.lower(): 
                    page.saveText("#redirect %s" % newpagename, '0',
                                  comment='Renamed to "%s"' % newpagename,
                                  action='RENAME', force_save=True)
                    # copy images over
                    copy_files(pagename, newpagename, request)

                newpage.saveText(pagetext, '0',
                                 comment='Renamed from "%s"%s' %
                                    (pagename, renamecomment),
                                 action="RENAME", proper_name=newpagename)

                msg = _('Page "%s" was successfully renamed to "%s"!') % (
                        pagename,newpagename)
                if newpagename.lower() != pagename.lower():
                    # check favorites because the redirect will
                    # process before the bookmarks get updated
                    if request.user.valid:
                        request.user.checkFavorites(page)

                    request.http_redirect('%s/%s?action=show&redirect=%s' % (
                        request.getScriptname(),
                        wikiutil.quoteWikiname(newpagename),
                        urllib.quote_plus(pagename.encode(config.charset), '')))

                    request.req_cache['pagenames'][
                        (newpagename.lower(),
                         request.config.wiki_name)] = newpagename
                    # we clear so the new page name appears
                    caching.CacheEntry(newpagename.lower(), request).clear()
                    return
                else:
                  request.req_cache['pagenames'][
                    (newpagename.lower(),
                     request.config.wiki_name)] = newpagename
                  # we clear so the new page name appears
                  caching.CacheEntry(newpagename.lower(), request).clear() 
                  return newpage.send_page(msg)

    else:
        # send renamepage form
        url = page.url()
        ticket = _createTicket()
        button = _('Rename')
        newname_label = _("New name")
        comment_label = _("Optional reason for the renaming")
        msg = ('<form method="GET" action="%(url)s">\n'
               '<input type="hidden" name="action" value="%(actname)s">\n'
               '<input type="hidden" name="ticket" value="%(ticket)s">\n'
               '%(newname_label)s <input type="text" name="newpagename" '
                                         'size="20" value="%(pagename)s">\n'
               '<input type="submit" name="button" value="%(button)s">\n'
               '<p>\n'
               '%(comment_label)s<br>\n'
               '<input type="text" name="comment" size="60" maxlength="80">\n'
               '</p>\n'
               '</form>\n'
               '<p>Note that the old page name will re-direct to the new '
               'page. This means you don\'t <i>have</i> to update links to '
               'the new name, but you ought to. (Find links to change by '
               'going into the Info area on the old page)</p>' % locals())

    return page.send_page(msg)

def _createTicket(tm = None):
    """
    Create a ticket using a site-specific secret (the config)
    """
    import hashlib, time, types
    ticket = tm or "%010x" % time.time()
    digest = hashlib.new('sha1')
    digest.update(ticket)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return "%s.%s" % (ticket, digest.hexdigest())

def _checkTicket(ticket):
    """
    Check validity of a previously created ticket
    """
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return ticket == ourticket
