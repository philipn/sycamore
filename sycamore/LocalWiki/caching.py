# -*- coding: iso-8859-1 -*-
"""
    LocalWiki caching module

    @copyright: 2005 by Philip Neustrom, 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, shutil, time
from LocalWiki import config, wikiutil, wikidb
from LocalWiki.Page import Page

class CacheEntry:
    def __init__(self, key, request):
        self.key = key
	self.request = request

    def mtime(self):
      return self.content_info()[1]

    def needsUpdate(self):
        needsupdate = False
	page_cache = self.content_info()
	if not page_cache[0] or not page_cache[1]: return True

	#edit_time = Page(self.key, self.request).mtime()
	#cached_time = self.mtime()

        #needsupdate = edit_time > cached_time
        
        # if a page has attachments (images) we check if this needs changing, too
	# also check included pages
        #if not needsupdate:
	#    for page in dependencies(self.key, self.request):
	#      if (page.mtime() > cached_time) or (page.ctime(self.request) > cached_time):
	#        return True

        return needsupdate

    def update(self, content, links):
        cached_time = time.time()
        self.request.cursor.execute("UPDATE curPages set cachedText=%(cached_content)s, cachedTime=%(cached_time)s where name=%(key)s", {'cached_content':wikidb.dbapi.Binary(content), 'cached_time':cached_time, 'key':self.key}, isWrite=True)
	if config.memcache:
	  page_cache = (content, cached_time)
	  self.request.mc.set("page_cache:%s" % wikiutil.quoteFilename(self.key.lower()), page_cache)
	self.request.cursor.execute("DELETE from links where source_pagename=%(key)s", {'key':self.key}, isWrite=True)
	for link in links:
	  self.request.cursor.execute("INSERT into links values (%(key)s, %(link)s)", {'key':self.key, 'link':link}, isWrite=True)

    def content_info(self):
        page_cache = None
	if self.request.req_cache['page_cache'].has_key(self.key):
	  return self.request.req_cache['page_cache'][self.key]
    	if config.memcache:
	  page_cache = self.request.mc.get("page_cache:%s" % wikiutil.quoteFilename(self.key.lower()))
	if not page_cache:
          self.request.cursor.execute("SELECT cachedText, cachedTime from curPages where name=%(key)s", {'key':self.key})
          result = self.request.cursor.fetchone()
	  if result:
	    if result[0] and result[1]:
	      text = wikidb.binaryToString(result[0])
	      cached_time = result[1]
	      page_cache = (text, cached_time)
	    else:
	      page_cache = ('', 0)
	  else:
	    page_cache = ('', 0)
	  if config.memcache:
	    self.request.mc.add("page_cache:%s" % wikiutil.quoteFilename(self.key.lower()), page_cache)
	self.request.req_cache['page_cache'][self.key] = page_cache

	return page_cache

    def content(self):
      return self.content_info()[0]

    def clear(self):
        #clears the content of the cache regardless of whether or not the page needs an update
	self.request.cursor.execute("UPDATE curPages set cachedText=NULL, cachedTime=NULL where name=%(key)s", {'key':self.key}, isWrite=True)
	if config.memcache:
	  self.request.mc.delete("page_cache:%s" % wikiutil.quoteFilename(self.key.lower()))
	  self.request.mc.delete("last_edit_info:%s" % wikiutil.quoteFilename(self.key.lower()))
	  self.request.mc.delete("pagename:%s" % wikiutil.quoteFilename(self.key.lower()))
	  self.request.mc.delete("page_text:%s" % wikiutil.quoteFilename(self.key.lower()))
	  #self.request.mc.delete("page_deps:%s" % wikiutil.quoteFilename(self.key))

def dependency(depend_pagename, source_pagename, request):
  # note that depend_pagename depends on source_pagename
  # this means that if source_pagename is updated we should
  # clear the depend_pagename cache
  request.cursor.execute("SELECT page_that_depends from pageDependencies where page_that_depends=%(depend_pagename)s and source_page=%(source_pagename)s", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename})
  result = request.cursor.fetchone()
  if result:
    request.cursor.execute("UPDATE pageDependencies set page_that_depends=%(depend_pagename)s, source_page=%(source_pagename)s", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename}, isWrite=True)
  else:
    request.cursor.execute("INSERT into pageDependencies (page_that_depends, source_page) values (%(depend_pagename)s, %(source_pagename)s)", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename}, isWrite=True)

def clear_dependencies(pagename, request):
  # clears out dependencies.  do this before parsing on a page save
  request.cursor.execute("DELETE from pageDependencies where page_that_depends=%(page_name)s", {'page_name':pagename}, isWrite=True)
  #if config.memcache:
  #  request.mc.delete("page_deps:%s" % wikiutil.quoteFilename(pagename))

def depend_on_me(pagename, request):
  from LocalWiki.Page import Page
  # return a list of pages (page objects) that depend on pagename
  page_deps = False
  #if config.memcache:
  #  page_deps = request.mc.get("page_deps:%s" % wikiutil.quoteFilename(pagename))
  #  if page_deps is not None:
  #    return page_deps
  #  else:
  #    page_deps = False

  request.cursor.execute("SELECT page_that_depends from pageDependencies where source_page=%(page_name)s", {'page_name':pagename})
  results = request.cursor.fetchall()
  page_deps = []
  for result in results:
    page_deps.append(result[0])
  #if config.memcache:
  #  request.mc.add("page_deps:%s" % wikiutil.quoteFilename(pagename), page_deps)
  return page_deps
