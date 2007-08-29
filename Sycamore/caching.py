# -*- coding: utf-8 -*-
"""
    Sycamore caching module

    @copyright: 2005-2007 by Philip Neustrom,
    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, shutil, time
from Sycamore import config, wikiutil, wikidb
from Sycamore.Page import Page

MAX_DEPENDENCY_DEPTH = 5

class CacheEntry:
    def __init__(self, key, request):
        self.key = key.lower()
        self.request = request

    def mtime(self):
        return self.content_info()[1]

    def needsUpdate(self):
        needsupdate = False
        page_cache = self.content_info()
        if not page_cache[0] or not page_cache[1]:
            return True
        if self.request.set_cache:
            return True

        return needsupdate

    def _consider_talk_link(self, links):
        if not self.request.config.talk_pages:
            return links
        lower_links = [ link.lower() for link in links ]
        from Sycamore.Page import Page
        pagename = self.key
        page = Page(pagename, self.request)
        linkto_name = None
        if page.isTalkPage():
            article_page = Page(wikiutil.talk_to_article_pagename(pagename),
                                self.request)
            article_pagename = article_page.proper_name()
            if article_pagename.lower() not in lower_links:
                links.append(article_pagename)
        else:
            talk_pagename = wikiutil.article_to_talk_pagename(pagename)
            talk_page = Page(talk_pagename, self.request)

            # add dependency so that editing/creating the talk page
            # has an affect on the article page's links
            dependency(pagename, talk_pagename.lower(), self.request)

            if talk_page.exists():
                talk_pagename = talk_page.proper_name()
                if talk_pagename.lower() not in lower_links:
                    links.append(talk_pagename)

        return links

    def update(self, content, links):
        links = self._consider_talk_link(links)
        cached_time = time.time()
        self.request.cursor.execute("""UPDATE curPages set
            cachedText=%(cached_content)s, cachedTime=%(cached_time)s
            where name=%(key)s and wiki_id=%(wiki_id)s""",
            {'cached_content':wikidb.dbapi.Binary(content),
             'cached_time':cached_time, 'key':self.key,
             'wiki_id':self.request.config.wiki_id},
            isWrite=True)
        self.request.cursor.execute("""DELETE from links where
            source_pagename=%(key)s and wiki_id=%(wiki_id)s""",
            {'key':self.key, 'wiki_id':self.request.config.wiki_id},
            isWrite=True)
        for link in links:
          self.request.cursor.execute("""INSERT into links
            (source_pagename, destination_pagename,
             destination_pagename_propercased, wiki_id)
            values (%(key)s, %(link)s, %(link_propercased)s, %(wiki_id)s)""",
            {'key':self.key, 'link':link.lower(), 'link_propercased':link,
             'wiki_id':self.request.config.wiki_id}, isWrite=True)
        page_info = pageInfo(Page(self.key, self.request),
                             get_from_cache=False, cached_content=content,
                             cached_time=cached_time)

        text = wikidb.binaryToString(content)
        page_info.cached_text = (text, cached_time)
        if config.memcache:
           if self.request.set_cache:
             self.request.mc.set("page_info:%s" % wikiutil.mc_quote(self.key),
                                 page_info)
           else:
             self.request.mc.add("page_info:%s" % wikiutil.mc_quote(self.key),
                                 page_info)

        self.request.req_cache['page_info'][(wikiutil.quoteFilename(self.key),
            self.request.config.wiki_id)] = page_info

    def content_info(self):
        page_cache = None
        page = Page(self.key, self.request)
        return pageInfo(page).cached_text

        
    def content(self):
        return self.content_info()[0]

    def clear(self, type=None):
        key = wikiutil.mc_quote(self.key)
        
        #clears the content of the cache regardless of whether or not the page
        # needs an update
        self.request.cursor.execute("""UPDATE curPages set
            cachedText=NULL, cachedTime=NULL
            where name=%(key)s and wiki_id=%(wiki_id)s""",
            {'key':self.key, 'wiki_id':self.request.config.wiki_id},
            isWrite=True)
        if type == 'page save delete':
            if config.memcache:
                page_info = pageInfo(Page(self.key, self.request),
                                     get_from_cache=False)
                self.request.mc.set("page_info:%s" % key, page_info)
                self.request.mc.set("pagename:%s" % key, False)
                self.request.mc.set("page_text:%s" % key, False)
                self.request.mc.delete("links:%s" % key)
        else:
            if config.memcache:
                self.request.mc.delete("page_info:%s" % key)
                self.request.mc.delete("pagename:%s" % key)
                self.request.mc.delete("page_text:%s" % key)
                self.request.mc.delete("links:%s" % key)

        if self.request.req_cache['page_info'].has_key((
                key,self.request.config.wiki_id)):
            del self.request.req_cache['page_info'][
                (key, self.request.config.wiki_id)]
        if self.request.req_cache['pagenames'].has_key(
            (self.key, self.request.config.wiki_id)):
            del self.request.req_cache['pagenames'][
                (self.key, self.request.config.wiki_id)]
        if (config.memcache and
            self.key == self.request.config.interwikimap.lower()):
            self.request.mc.delete('interwiki')

def dependency(depend_pagename, source_pagename, request):
    # note that depend_pagename depends on source_pagename
    # this means that if source_pagename is updated we should
    # clear the depend_pagename cache
    request.cursor.execute("""SELECT page_that_depends from pageDependencies
      where page_that_depends=%(depend_pagename)s and
            source_page=%(source_pagename)s and wiki_id=%(wiki_id)s""",
      {'depend_pagename':depend_pagename, 'source_pagename':source_pagename,
       'wiki_id':request.config.wiki_id})
    result = request.cursor.fetchone()
    if not result:
      request.cursor.execute("""INSERT into pageDependencies
          (page_that_depends, source_page, wiki_id)
          values (%(depend_pagename)s, %(source_pagename)s, %(wiki_id)s)""",
          {'depend_pagename':depend_pagename, 'source_pagename':source_pagename,
           'wiki_id':request.config.wiki_id}, isWrite=True)
    # if C <- B and B <- A then C <- A
    for i in range(0, MAX_DEPENDENCY_DEPTH):
        request.cursor.execute("""SELECT source_page from pageDependencies where
            page_that_depends=%(source_pagename)s and wiki_id=%(wiki_id)s""",
            {'depend_pagename':depend_pagename, 'source_pagename':source_pagename,
             'wiki_id':request.config.wiki_id})
        results = request.cursor.fetchall()
        if results:
             for result in results:
                 source_pagename = result[0]
                 request.cursor.execute("""SELECT page_that_depends from
                     pageDependencies where
                        page_that_depends=%(depend_pagename)s and
                        source_page=%(source_pagename)s and
                        wiki_id=%(wiki_id)s""",
                     {'depend_pagename':depend_pagename,
                      'source_pagename':source_pagename,
                      'wiki_id':request.config.wiki_id})
                 result = request.cursor.fetchone()
                 if not result:
                     request.cursor.execute("""INSERT into pageDependencies
                         (page_that_depends, source_page, wiki_id)
                         values (%(depend_pagename)s, %(source_pagename)s,
                                 %(wiki_id)s)""",
                         {'depend_pagename':depend_pagename,
                          'source_pagename':source_pagename,
                          'wiki_id':request.config.wiki_id}, isWrite=True)
        else:
            break

def clear_dependencies(pagename, request):
    """
    clears out dependencies.  do this before parsing on a page save
    """
    request.cursor.execute("""DELETE from pageDependencies
        where page_that_depends=%(page_name)s and wiki_id=%(wiki_id)s""",
        {'page_name':pagename, 'wiki_id':request.config.wiki_id}, isWrite=True)

def depend_on_me(pagename, request, exists, action=None):
    """
    return a list of pages (page objects) that depend on pagename
    action paramter is the edit action.  if it's SAVENEW or DELETE
    then we return pages that link to this page.
    """
    from Sycamore.Page import Page
    page_deps = False
    do_links = False

    request.cursor.execute("""SELECT page_that_depends from pageDependencies
        where source_page=%(page_name)s and wiki_id=%(wiki_id)s""",
        {'page_name':pagename, 'wiki_id':request.config.wiki_id})
    results = request.cursor.fetchall()
    page_deps = []
    for result in results:
        page_deps.append(result[0])
    if action == 'SAVENEW' or action == 'DELETE':
        do_links = True
    elif not exists:
        do_links = True

    if do_links:
        request.cursor.execute("""SELECT source_pagename from links where
            destination_pagename=%(page_name)s and wiki_id=%(wiki_id)s""",
            {'page_name':pagename, 'wiki_id':request.config.wiki_id})
        for result in request.cursor.fetchall():
            page_deps.append(result[0])
    return page_deps


class pageInfoObj(object):
    def __init__(self, edit_info, cached_text, meta_text, has_acl,
                 has_map=None):
        self.edit_info = edit_info
        self.cached_text = cached_text
        self.meta_text = meta_text
        self.has_map = has_map
        self.has_acl = has_acl


def find_meta_text(page, fresh=False):
    meta_text = False
    body = page.get_raw_body(fresh=fresh)
    body = body.split('\n')
    meta_text = []
    for line in body:
        if line:
            if line[0] == '#':
                meta_text.append(line)
            else:
                break
        else:
            break
    meta_text = '\n'.join(meta_text)
    return meta_text

def pageInfo(page, get_from_cache=True, cached_content=None,
             cached_time=None):
    """
    Gets a group of related items for a page: last edited information,
    page cached text, meta-text (such as #redirect), and has_map.
    Returns an object with attributes edit_info, cached_text, meta_text,
    has_map.
    """

    pagename_key = wikiutil.mc_quote(page.page_name.lower())
    if page.prev_date:
        key = "%s,%s" % (pagename_key, repr(page.prev_date))
    else:
        key = pagename_key

    if get_from_cache:
        # check per-request cache
        if page.request.req_cache['page_info'].has_key(
            (key, page.request.config.wiki_id)):
          return page.request.req_cache['page_info'][
            (key, page.request.config.wiki_id)]
        
        # check memcache
        if config.memcache:
            page_info = page.request.mc.get("page_info:%s" % key)
            if page_info:
                page.request.req_cache['page_info'][
                    (key, page.request.config.wiki_id)] = page_info
                return page_info

    # memcache failed, this means we have to get all the information
    # from the database

    # last edit information 
    editUserID = None
    editTimeUnix = 0
    has_map = None
    if page.exists():
        if not page.prev_date:
            page.cursor.execute("""SELECT editTime, userEdited from curPages
                where name=%(page_name)s and wiki_id=%(wiki_id)s""",
                {'page_name':page.page_name,
                 'wiki_id':page.request.config.wiki_id})
            result = page.cursor.fetchone()
            if result:
                editTimeUnix = result[0]
                if result[1]:
                    editUserID = result[1].strip()
                else:
                    editUserID = result[1]
        else:
            page.cursor.execute("""SELECT userEdited from allPages
                where name=%(page_name)s and editTime=%(date)s and
                      wiki_id=%(wiki_id)s""",
                {'page_name':page.page_name, 'date':page.prev_date,
                 'wiki_id':page.request.config.wiki_id})
            result = page.cursor.fetchone()
            editUserID = result[0]
            editTimeUnix = page.prev_date
        edit_info = (editTimeUnix, editUserID)

        # cached text
        cached_text = ('', 0)
        if not page.prev_date:
              if not cached_content or not cached_time:
                  page.cursor.execute("""SELECT cachedText, cachedTime from
                      curPages where name=%(page)s and wiki_id=%(wiki_id)s""",
                      {'page':page.page_name,
                       'wiki_id':page.request.config.wiki_id})
                  result = page.cursor.fetchone()
                  if result:
                      if result[0] and result[1]:
                          text = wikidb.binaryToString(result[0])
                          cached_time = result[1]
                          cached_text = (text, cached_time)
              else:
                  cached_text = cached_content

        # meta_text
        meta_text = find_meta_text(page, fresh=True)
      
    else:
     # set some defaults.  These shouldn't be accessed.
     edit_info = (None, None)
     cached_text = ('', 0)
     meta_text = None
     has_map = False
     has_acl = True

    if not page.prev_date:
        if not config.has_old_wiki_map:
            currently_has_map = False
            page.cursor.execute("""SELECT count(pagename) from mapPoints
                where pagename=%(page_name)s and wiki_id=%(wiki_id)s""",
                {'page_name':page.page_name,
                 'wiki_id':page.request.config.wiki_id})
            result = page.cursor.fetchone()
            if result:
                if result[0]:
                    currently_has_map = True
            if page.request.save_time: # we are in a 'saving' request
                if page.request.addresses:
                    has_map = True
                else:
                    has_map = False
            else:
                has_map = currently_has_map 

        else:
            page.cursor.execute("""SELECT count(pagename) from mapPoints where
                pagename=%(page_name)s and wiki_id=%(wiki_id)s""",
                {'page_name':page.page_name,
                 'wiki_id':page.request.config.wiki_id})
            result = page.cursor.fetchone()
            if result:
                if result[0]:
                    has_map = True
        if not page.exists():
           page.cursor.execute("""SELECT latestEdit.editTime,
            allPages.userEdited from (
                SELECT max(editTime) as editTime from allPages
                    where name=%(page_name)s and wiki_id=%(wiki_id)s)
            as latestEdit, allPages
            where allPages.name=%(page_name)s and
            allPages.editTime=latestEdit.editTime and
            allPages.wiki_id=%(wiki_id)s""",
           {'page_name':page.page_name, 'wiki_id':page.request.config.wiki_id})
           result = page.cursor.fetchone()
           if result:
                editUserID = result[1]
                editTimeUnix = result[0]
                edit_info = (editTimeUnix, editUserID)

    else:
        page.cursor.execute("""SELECT userEdited from allPages
         where name=%(page_name)s and editTime=%(date)s and
               wiki_id=%(wiki_id)s""",
         {'page_name':page.page_name, 'date':page.prev_date,
          'wiki_id':page.request.config.wiki_id})
        result = page.cursor.fetchone()
        editUserID = result[0]
        editTimeUnix = page.prev_date
        edit_info = (editTimeUnix, editUserID)
        has_map = None

    page.cursor.execute("""SELECT groupname, may_read, may_edit, may_delete,
                                  may_admin from pageAcls
                                  where pagename=%(pagename)s and
                                  wiki_id=%(wiki_id)s""",
                        {'pagename':page.page_name,
                         'wiki_id':page.request.config.wiki_id})
    if page.cursor.fetchone():
        has_acl = True
    else:
        has_acl = False

    page_info = pageInfoObj(edit_info, cached_text, meta_text, has_acl,
                            has_map)

    if config.memcache and not page.request.set_cache:
        page.request.mc.add("page_info:%s" % key, page_info)
    elif config.memcache and page.request.set_cache:
        page.request.mc.set("page_info:%s" % key, page_info)

    page.request.req_cache['page_info'][
        (key, page.request.config.wiki_id)] = page_info
    return page_info

def getPageLinks(pagename, request, update=False):
    """
    Caches all of the page links on page pagename. Subsequent calls to page.exists() will be much faster if they're a link.

    Returns a list of the properly cased links (pagenames).
    """
    links = None
    got_from_memcache = False
    lower_pagename = pagename.lower()
    if config.memcache:
        mc_key = 'links:%s' % wikiutil.mc_quote(lower_pagename)
        links = request.mc.get(mc_key)
    if links is None:
        # get from database 
        request.cursor.execute("""SELECT destination_pagename_propercased,
            curPages.name from links left join curPages on
                (destination_pagename=curPages.name and
                 links.wiki_id=%(wiki_id)s and
                 curPages.wiki_id=%(wiki_id)s)
            where source_pagename=%(pagename)s and
                  links.wiki_id=%(wiki_id)s""",
            {'pagename': lower_pagename, 'wiki_id': request.config.wiki_id})
        result = request.cursor.fetchall()
        links = {}
        for link, exists in result:
            if exists:
                links[link.lower()] = (True, link)
            else:
                links[link.lower()] = (False, link)
    else:
        got_from_memcache = True

    for link in links:
        exists, proper_name = links[link]
        key = proper_name.lower()
        if exists:
            request.req_cache['pagenames'][
                (key, request.config.wiki_name)] = proper_name
        else:
            request.req_cache['pagenames'][
                (key, request.config.wiki_name)] = False

    if config.memcache and not got_from_memcache:
        if update:
            request.mc.set(mc_key, links)
        else:
            request.mc.add(mc_key, links)

    return [info[1] for link, info in links.iteritems()]

def deleteAllPageInfo(pagename, request):
    """
    Delete all of the cached information associated with the page / it's past versions.
    """
    if config.memcache:
        d = {'pagename':pagename, 'wiki_id':request.config.wiki_id}
        request.cursor.execute("""SELECT editTime from allPages
            where name=%(pagename)s and wiki_id=%(wiki_id)s""", d) 
        results = request.cursor.fetchall()
        for result in results:
            version = result[0] 
            # we do set() rather than delete() to avoid possible race conditions
            request.mc.set("page_text:%s,%s" % (wikiutil.mc_quote(pagename),
                                                repr(version)), False)

def deleteNewerPageInfo(pagename, version, request):
    """
    Delete all of the cached information associated with the page that is newer than version.
    """
    if config.memcache:
        d = {'pagename':pagename, 'version':version,
             'wiki_id':request.config.wiki_id}    
        request.cursor.execute("""SELECT editTime from allPages where
            name=%(pagename)s and wiki_id=%(wiki_id)s and
            editTime>%(version)s""", d)
        results = request.cursor.fetchall()
        for result in results:
            newer_version = result[0]
            # we do set() rather than delete() to avoid possible
            # race conditions
            request.mc.set("page_text:%s,%s" % (wikiutil.mc_quote(pagename),
                                                repr(newer_version)), False)

def deleteAllFileInfo(filename, pagename, request):
    """
    Delete all of the cached versions of the file.
    """ 
    if config.memcache:
        d = {'filename':filename, 'pagename':pagename,
             'wiki_id':request.config.wiki_id}
        # we do set() rather than delete() to avoid possible race conditions
        request.mc.set("oldfiles:%s,%s" % (wikiutil.mc_quote(filename),
                                           wikiutil.mc_quote(pagename)), False)
        request.cursor.execute("""SELECT uploaded_time from oldFiles where
            name=%(filename)s and attached_to_pagename=%(pagename)s and
            wiki_id=%(wiki_id)s""", d)
        results = request.cursor.fetchall()
        for result in results:
            version = result[0]
            # we do set() rather than delete() to avoid possible
            # race conditions
            request.mc.set("oldfiles:%s,%s,%s" % (wikiutil.mc_quote(filename),
                                                  wikiutil.mc_quote(pagename),
                                                  repr(version)), False)

def deleteNewerFileInfo(filename, pagename, version, request):
    """
    Delete newer version of the cached file.
    """ 
    if config.memcache:
        d = {'filename':filename, 'pagename':pagename, 'version': version,
             'wiki_id':request.config.wiki_id}
        # we do set() rather than delete() to avoid possible race conditions
        request.cursor.execute("""SELECT uploaded_time from oldFiles where
            name=%(filename)s and attached_to_pagename=%(pagename)s and
            wiki_id=%(wiki_id)s and uploaded_time>%(version)s""", d)
        results = request.cursor.fetchall()
        for result in results:
            newer_version = result[0]
            # we do set() rather than delete() to avoid possible
            # race conditions
            request.mc.set("oldfiles:%s,%s,%s" % (wikiutil.mc_quote(filename),
                                                  wikiutil.mc_quote(pagename),
                                                  repr(newer_version)), False)

def updateRecentChanges(page):
    request = page.request
    # set global recent changes (per-wiki)
    wikidb.setRecentChanges(request)
    # set page specific recent changes
    wikidb.setRecentChanges(request, page=page.page_name)
