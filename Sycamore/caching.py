# -*- coding: iso-8859-1 -*-
"""
    Sycamore caching module

    @copyright: 2005 by Philip Neustrom, 2001-2004 by Jürgen Hermann <jh@web.de>
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
	if not page_cache[0] or not page_cache[1]: return True

        return needsupdate

    def update(self, content, links):
        cached_time = time.time()
        self.request.cursor.execute("UPDATE curPages set cachedText=%(cached_content)s, cachedTime=%(cached_time)s where name=%(key)s", {'cached_content':wikidb.dbapi.Binary(content), 'cached_time':cached_time, 'key':self.key}, isWrite=True)
	self.request.cursor.execute("DELETE from links where source_pagename=%(key)s", {'key':self.key}, isWrite=True)
	for link in links:
	  self.request.cursor.execute("INSERT into links (source_pagename, destination_pagename, destination_pagename_propercased) values (%(key)s, %(link)s, %(link_propercased)s)", {'key':self.key, 'link':link.lower(), 'link_propercased':link}, isWrite=True)
	page_info = pageInfo(Page(self.key, self.request))
        text = wikidb.binaryToString(content)
        page_info.cached_text = (text, cached_time)
	if config.memcache:
           self.request.mc.set("page_info:%s" % wikiutil.quoteFilename(self.key), page_info)
        self.request.req_cache['page_info'][self.key] = page_info


    def content_info(self):
        page_cache = None
	page = Page(self.key, self.request)
        return pageInfo(page).cached_text

	
    def content(self):
      return self.content_info()[0]

    def clear(self, type=None):
        key = wikiutil.quoteFilename(self.key.lower())
        if self.request.req_cache['page_info'].has_key(key):
          del self.request.req_cache['page_info'][key]
        #clears the content of the cache regardless of whether or not the page needs an update
	self.request.cursor.execute("UPDATE curPages set cachedText=NULL, cachedTime=NULL where name=%(key)s", {'key':self.key}, isWrite=True)
	if config.memcache:
	  self.request.mc.delete("page_info:%s" % key)
	  self.request.mc.delete("pagename:%s" % key)
	  self.request.mc.delete("page_text:%s" % key)
	  self.request.mc.delete("links:%s" % key)
  	  if type == 'page save new':
	     pagecount = wikidb.getPageCount(self.request) + 1
             self.request.mc.set('active_page_count', pagecount)
 	  elif type == 'page save delete':
	     pagecount = wikidb.getPageCount(self.request) - 1
             self.request.mc.set('active_page_count', pagecount)
	  if self.key == config.interwikimap.lower():
	     self.request.mc.delete('interwiki')

def dependency(depend_pagename, source_pagename, request):
  # note that depend_pagename depends on source_pagename
  # this means that if source_pagename is updated we should
  # clear the depend_pagename cache
  request.cursor.execute("SELECT page_that_depends from pageDependencies where page_that_depends=%(depend_pagename)s and source_page=%(source_pagename)s", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename})
  result = request.cursor.fetchone()
  if not result:
    request.cursor.execute("INSERT into pageDependencies (page_that_depends, source_page) values (%(depend_pagename)s, %(source_pagename)s)", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename}, isWrite=True)
  # if C <- B and B <- A then C <- A
  for i in range(0, MAX_DEPENDENCY_DEPTH):
    request.cursor.execute("SELECT source_page from pageDependencies where page_that_depends=%(source_pagename)s", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename})
    results = request.cursor.fetchall()
    if results:
	 for result in results:
	    source_pagename = result[0]
            request.cursor.execute("SELECT page_that_depends from pageDependencies where page_that_depends=%(depend_pagename)s and source_page=%(source_pagename)s", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename})
            result = request.cursor.fetchone()
            if not result:
                request.cursor.execute("INSERT into pageDependencies (page_that_depends, source_page) values (%(depend_pagename)s, %(source_pagename)s)", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename}, isWrite=True)

	    
    else: break


def clear_dependencies(pagename, request):
  # clears out dependencies.  do this before parsing on a page save
  request.cursor.execute("DELETE from pageDependencies where page_that_depends=%(page_name)s", {'page_name':pagename}, isWrite=True)

def depend_on_me(pagename, request, exists, action=None):
  """
  return a list of pages (page objects) that depend on pagename
  action paramter is the edit action.  if it's SAVENEW or DELETE then we return pages that link to this page.
  """
  from Sycamore.Page import Page
  page_deps = False
  do_links = False

  request.cursor.execute("SELECT page_that_depends from pageDependencies where source_page=%(page_name)s", {'page_name':pagename})
  results = request.cursor.fetchall()
  page_deps = []
  for result in results:
    page_deps.append(result[0])
  if action == 'SAVENEW' or action == 'DELETE':
     do_links = True
  elif not exists:
     do_links = True

  if do_links:
    request.cursor.execute("SELECT source_pagename from links where destination_pagename=%(page_name)s", {'page_name':pagename})
    for result in request.cursor.fetchall():
      page_deps.append(result[0])
  return page_deps

class pageInfoObj(object):
  def __init__(self, edit_info, cached_text, meta_text, has_map=None):
    self.edit_info = edit_info
    self.cached_text = cached_text
    self.meta_text = meta_text
    self.has_map = has_map

def find_meta_text(page):
    meta_text = False
    body = page.get_raw_body()
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

def pageInfo(page):
  """
  Gets a group of related items for a page: last edited information, page cached text, meta-text (such as #redirect), and has_map.
  Returns an object with attributes edit_info, cached_text, meta_text, has_map.
  """
  pagename_key = wikiutil.quoteFilename(page.page_name.lower())
  if page.prev_date: key = u"%s,%s" % (pagename_key, page.prev_date)
  else: key = pagename_key

  # check per-request cache
  if page.request.req_cache['page_info'].has_key(key):
    return page.request.req_cache['page_info'][key]
  
  # check memcache
  if config.memcache:
    page_info = page.request.mc.get("page_info:%s" % key)
    if page_info:
      page.request.req_cache['page_info'][key] = page_info
      return page_info

  # memcache failed, this means we have to get all the information from the database

  # last edit information 
  editUserID = None
  editTimeUnix = 0
  has_map = None
  if page.exists():
    if not page.prev_date:
      page.cursor.execute("SELECT editTime, userEdited from curPages where name=%(page_name)s", {'page_name':page.page_name})
      result = page.cursor.fetchone()
      if result:
        editTimeUnix = result[0]
        editUserID = result[1]
    else:
      page.cursor.execute("SELECT userEdited from allPages where name=%(page_name)s and editTime=%(date)s", {'page_name':page.page_name, 'date':page.prev_date})
      result = page.cursor.fetchone()
      editUserID = result[0]
      editTimeUnix = page.prev_date
    edit_info = (editTimeUnix, editUserID)

    # cached text
    cached_text = ('', 0)
    if not page.prev_date:
      page.cursor.execute("SELECT cachedText, cachedTime from curPages where name=%(page)s", {'page':page.page_name})
      result = page.request.cursor.fetchone()
      if result:
        if result[0] and result[1]:
          text = wikidb.binaryToString(result[0])
          cached_time = result[1]
          cached_text = (text, cached_time)

    # meta_text
    meta_text = find_meta_text(page)
    
  else:
   # set some defaults.  These shouldn't be accessed.
   edit_info = None
   cached_text = ('', 0)
   meta_text = None
   has_map = False

  if not page.prev_date:
    page.cursor.execute("SELECT count(pagename) from mapPoints where pagename=%(page_name)s", {'page_name':page.page_name})
    result = page.cursor.fetchone()
    if result:
      if result[0]:
        has_map = True
    if not page.exists():
       page.cursor.execute("SELECT latestEdit.editTime, allPages.userEdited from (SELECT max(editTime) as editTime from allPages where name=%(page_name)s) as latestEdit, allPages where allPages.name=%(page_name)s and allPages.editTime=latestEdit.editTime", {'page_name':page.page_name})
       result = page.cursor.fetchone()
       if result:
         editUserID = result[1]
         editTimeUnix = result[0]
         edit_info = (editTimeUnix, editUserID)

  else:
     page.cursor.execute("SELECT userEdited from allPages where name=%(page_name)s and editTime=%(date)s", {'page_name':page.page_name, 'date':page.prev_date})
     result = page.cursor.fetchone()
     editUserID = result[0]
     editTimeUnix = page.prev_date
     edit_info = (editTimeUnix, editUserID)
     has_map = None

  page_info = pageInfoObj(edit_info, cached_text, meta_text, has_map)

  if config.memcache:
    page.request.mc.add("page_info:%s" % key, page_info)

  page.request.req_cache['page_info'][key] = page_info
  return page_info


def getPageLinks(pagename, request):
  """
  Caches all of the page links on page pagename. Subsequent calls to page.exists() will be much faster if they're a link.

  Returns a list of the properly cased links (pagenames).
  """
  links = None
  got_from_memcache = False
  lower_pagename = pagename.lower()
  if config.memcache:
     mc_key = 'links:%s' % wikiutil.quoteFilename(lower_pagename)
     links = request.mc.get(mc_key)
  if links is None:
     # get from database 
     request.cursor.execute("SELECT destination_pagename_propercased, curPages.name from links left join curPages on destination_pagename=curPages.name where source_pagename=%(pagename)s", {'pagename': lower_pagename})
     result = request.cursor.fetchall()
     links = {}
     for link, exists in result:
       if exists:
         links[link.lower()] = (True, link)
       else:
	 links[link.lower()] = (False, link)
  else: got_from_memcache = True

  for link in links:
    exists, proper_name = links[link]
    key = proper_name.lower()
    if exists: request.req_cache['pagenames'][key] = proper_name
    else: request.req_cache['pagenames'][key] = False

  if config.memcache and not got_from_memcache:
    request.mc.add(mc_key, links)

  return [ info[1] for link, info in links.iteritems() ]
