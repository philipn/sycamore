# -*- coding: utf-8 -*-
"""
    Sycamore - revert action

    This action allows you to revert a page. Note that the standard
    config lists this action as excluded!

    @copyright: 2006-2007 Philip Neustrom <philipn@gmail.com>,
                2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import hashlib
import time
import types

from Sycamore import config
from Sycamore import wikiutil
from Sycamore import wikiaction
from Sycamore import caching
from Sycamore import search

from Sycamore.PageEditor import PageEditor
from Sycamore.Page import Page

def delete_all_newer(oldpage, request, showrc):
    version_date = oldpage.prev_date
    d = {'pagename':oldpage.page_name, 'version_date':version_date,
         'wiki_id':oldpage.wiki_id}
    caching.deleteNewerPageInfo(oldpage.page_name, version_date, request)
    request.cursor.execute("""DELETE from allPages
                              where name=%(pagename)s and
                                    editTime>%(version_date)s and
                                    wiki_id=%(wiki_id)s""", d, isWrite=True)

    # clear out map points set in this time period.
    # move old map point into current map points.
    request.cursor.execute("""DELETE from oldMapPoints
                              where pagename=%(pagename)s and
                                    created_time>%(version_date)s and
                                    wiki_id=%(wiki_id)s""", d, isWrite=True)

    if not showrc:
        # Check to see if there's actually a map on this page version.
        # If there is, we move the map point over from oldMapPoints to
        # mapPoints, accordingly.
        request.cursor.execute(
            """SELECT pagename, x, y, created_time, created_by, created_by_ip,
                      pagename_propercased, address, wiki_id, deleted_time
               from oldMapPoints
               where wiki_id=%(wiki_id)s and pagename=%(pagename)s and
                     created_time <= %(version_date)s and
                     deleted_time >= %(version_date)s""", d)
        mapdata = request.cursor.fetchall()
        cleared_out_already = False
        for (pagename, x, y, created_time, created_by, created_by_ip,
             pagename_propercased, address, wiki_id, deleted_time) in mapdata:
            this_version_has_map = version_date <= deleted_time
            if this_version_has_map:
                if not cleared_out_already:
                    request.cursor.execute(
                        """DELETE from mapPoints
                           where pagename=%(pagename)s and
                                 wiki_id=%(wiki_id)s""", d, isWrite=True)
                    cleared_out_already = True
                # add this map point version into the current map points table
                d['pagename'] = pagename
                d['x'] = x
                d['y'] = y
                d['created_time'] = created_time
                d['created_by'] = created_by
                d['created_by_ip'] = created_by_ip
                d['pagename_propercased'] = pagename_propercased
                d['address'] = address
                d['wiki_id'] = wiki_id
                request.cursor.execute(
                    """INSERT into mapPoints
                       (pagename, x, y, created_time, created_by,
                        created_by_ip, pagename_propercased, address, wiki_id)
                       values (%(pagename)s, %(x)s, %(y)s, %(created_time)s,
                               %(created_by)s, %(created_by_ip)s,
                               %(pagename_propercased)s, %(address)s,
                               %(wiki_id)s)""", d, isWrite=True)
        # these are now in mapPoints, so it's safe to clear them out
        # of the archive table
        request.cursor.execute("""DELETE from oldMapPoints
                                  where wiki_id=%(wiki_id)s and
                                        pagename=%(pagename)s and
                                        created_time <= %(version_date)s and
                                        deleted_time >= %(version_date)s""", d)

def set_current_pagetext(oldpage, request):
    version_date = oldpage.prev_date
    d = {'pagename':oldpage.page_name, 'version_date':version_date,
         'wiki_id':oldpage.wiki_id, 'oldtext': oldpage.get_raw_body()}
    if oldpage.exists(fresh=True):
        request.cursor.execute(
            """UPDATE curPages set
               text=%(oldtext)s, cachedText=NULL, editTime=%(version_date)s,
               cachedTime=NULL,
               userEdited=(select userEdited from allPages
                           where name=%(pagename)s and wiki_id=%(wiki_id)s and
                                 editTime=%(version_date)s),
               propercased_name=(select propercased_name from allPages
                                 where name=%(pagename)s and
                                       wiki_id=%(wiki_id)s and
                                       editTime=%(version_date)s)
               where name=%(pagename)s and wiki_id=%(wiki_id)s""",
            d, isWrite=True)
    else:
        request.cursor.execute("""SELECT editType from allPages
                                  where name=%(pagename)s and
                                        wiki_id=%(wiki_id)s and
                                        editTime=%(version_date)s""", d)
        result = request.cursor.fetchone()
        if not result or result[0] != 'DELETE':
            # page wasn't most recently deleted, so we restore it
            request.cursor.execute(
                """INSERT into curPages
                   (name, text, cachedText, editTime, cachedTime, userEdited,
                    propercased_name, wiki_id)
                   values
                   (%(pagename)s, %(oldtext)s, NULL, %(version_date)s, NULL,
                    (select userEdited from allPages
                     where name=%(pagename)s and wiki_id=%(wiki_id)s and
                           editTime=%(version_date)s),
                    (select propercased_name from allPages
                     where name=%(pagename)s and wiki_id=%(wiki_id)s and
                           editTime=%(version_date)s),
                    %(wiki_id)s)""", d, isWrite=True)

def _set_proper_pagename(request, page):
    d = {'pagename': page.page_name, 'wiki_id': page.wiki_id,
         'version_date': page.prev_date}
    request.cursor.execute("""SELECT propercased_name from allPages
                              where name=%(pagename)s and
                                    wiki_id=%(wiki_id)s and
                                    editTime=%(version_date)s""", d)
    proper_pagename = request.cursor.fetchone()[0]
    request.req_cache['pagenames'][(
        page.page_name, request.config.wiki_name)] = proper_pagename
    return proper_pagename

def revert_to_page(oldpg, request, pg, comment=None, permanent=False,
                   showrc=True):
    _ = request.getText
    if permanent:
        delete_all_newer(oldpg, request, showrc)  
        if not showrc:
            set_current_pagetext(oldpg, request)
    
    try:
        # don't log on RC if admin doesn't want it
        if not (permanent and not showrc):
            pg.saveText(oldpg.get_raw_body(), '0', stripspaces=0, notify=1,
                        comment=comment, action="SAVE/REVERT")
            pagename = pg.proper_name()
        else:
            #doing hard work ourselves..
            # should be abstracted into the page object.
            pg.set_raw_body(oldpg.get_raw_body()) 
            # deal with the case of macros / other items that change state
            # by /not/ being in the page
            search.add_to_index(pg)
            pg.buildCache()
            caching.CacheEntry(pg.page_name, request).clear()
            caching.updateRecentChanges(pg)
            # if we revert to a version with a differently-cased pagename
            pagename = _set_proper_pagename(request, oldpg)
        savemsg = _("Page reverted to version %s" % oldpg.version)
    except pg.Unchanged:
        savemsg = _("The current page is the same as the older page you wish "
                    "to revert to!")
    except pg.SaveError:
        savemsg = _("An error occurred while reverting the page.")
    
    # clear req cache so user sees proper page state (exist)
    request.req_cache['pagenames'][(
        pagename.lower(), request.config.wiki_name)] = pagename

    return savemsg

def execute(pagename, request):
    from Sycamore.PageEditor import PageEditor
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = Page(pagename, request)
    permanent = False
    showrc = True
    if not request.user.may.edit(page):
        return page.send_page(
            msg = _('You are not allowed to revert this page!'))

    # check whether the user clicked the delete button
    if request.form.has_key('button') and request.form.has_key('ticket'):
        # check whether this is a valid deletion request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
            return page.send_page(
                msg = _('Please use the interactive user interface to '
                        'revert pages!'))
        # revert the page
        if request.form.has_key('version'):
            version = int(request.form['version'][0])
            oldpg = Page(pagename, request, version=version)
            date = oldpg.prev_date
            if request.form.has_key('comment'):
                entered_comment = request.form['comment'][0]
            else:
                entered_comment = ''
            if len(entered_comment) > wikiaction.MAX_COMMENT_LENGTH:
                return page.send_page(msg = _(
                    'Comments must be less than %s characters long.' %
                    wikiaction.MAX_COMMENT_LENGTH))
            else:
                comment = 'v%s' % str(version)

            comment = "%sc%s" % (comment, entered_comment)
        else:
            return

        if (request.form.has_key('permanent') and
            request.form['permanent'][0] and request.user.may.admin(page)):
            permanent = True
            if (request.form.has_key('noshowrc') and
                request.form['noshowrc'][0]):
                showrc = False

        pg = PageEditor(pagename, request)
        savemsg = revert_to_page(oldpg, request, pg, comment=comment,
                                 permanent=permanent, showrc=showrc)
        return pg.send_page(msg=savemsg,
                            force_regenerate_content=(permanent and not
                                                      showrc))

    # get version
    if request.form.has_key('version'):
        version = request.form['version'][0]
    else:
        return page.send_page(msg= _(
            'Please use the interactive user interface to revert pages!'))

    oldpg = Page(pagename, request, version=version)
    # send revert form
    url = page.url()
    ticket = _createTicket()
    button = _('Revert')
    comment_label = _("Reason for the revert:")
    if request.user.may.admin(page):
        admin_label = (
            '<p>Permanently remove newer versions: '
            '<input id="noshowrctoggle" type="checkbox" name="permanent" '
                   'value="1"><span id="noshowrc">'
            "Don't log on Recent Changes: "
            '<input type="checkbox" name="noshowrc" value="1"></span></p>\n'
            '<script type="text/javascript">\n'
            "document.getElementById('noshowrc').style.visibility = "
                "'hidden';\n"
            "document.getElementById('noshowrc').style.paddingLeft = "
                "'1em';\n"
            "document.getElementById('noshowrctoggle').onclick = "
                "function () {\n"
            "document.getElementById('noshowrc').style.visibility = "
                "document.getElementById('noshowrctoggle').checked ? "
                    "'visible' : 'hidden'; \n"
            "}\n"
            "</script>\n"
        )
    else:
        admin_label = ''

    formhtml = (
        '<form method="GET" action="%(url)s">'
        '<input type="hidden" name="action" value="%(actname)s">'
        '<input type="hidden" name="ticket" value="%(ticket)s">'
        '<input type="hidden" name="version" value="%(version)s">'
        '<p>'
        '%(comment_label)s'
        '</p>'
        '<input type="text" name="comment" size="60" maxlength="80">'
        '<input type="submit" name="button" value="%(button)s">'
        '%(admin_label)s'
        '</form>' % {
            'url': url,
            'actname': actname,
            'ticket': ticket,
            'button': button,
            'comment_label': comment_label,
            'version': version,
            'admin_label': admin_label,
    })

    return oldpg.send_page(msg=formhtml)


def _createTicket(tm = None):
    """
    Create a ticket using a site-specific secret (the config)
    """
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
