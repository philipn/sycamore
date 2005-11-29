# -*- coding: iso-8859-1 -*-
"""
    LocalWiki caching module

    @copyright: 2005 by Philip Neustrom, 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, shutil, time
from LocalWiki import config, wikiutil, wikidb


class CacheEntry:
    def __init__(self, arena, key):
        self.arena = arena
        self.key = key

    def exists(self):
	db = wikidb.connect()
	cursor = db.cursor()
	cursor.execute("SELECT cachedTime from curPages where name=%s", (self.key))
	result = cursor.fetchall()
	cursor.close()
	db.close()
	return result

    def mtime(self):
	db = wikidb.connect()
	cursor = db.cursor()
	cursor.execute("SELECT cachedTime from curPages where name=%s", (self.key))
	result = cursor.fetchall()
	cursor.close()
	db.close()
	if result:
		return result[0][0]
	else: return 0

    def needsUpdate(self):
        db = wikidb.connect()
        cursor = db.cursor()
        cursor.execute("SELECT editTime, cachedTime from curPages where name=%s", (self.key))
        result = cursor.fetchall()
	
        if result:
            if result[0][0]:
		edit_time = result[0][0]
            else: return 1
            if result[0][1]:
		cached_time = result[0][1]
            else: return 1

        needsupdate = edit_time > cached_time
        
        # if a page has attachments (images) we check if this needs changing, too
        if not needsupdate:
	    cursor.execute("SELECT max(uploaded_time) from images where attached_to_pagename=%s", (self.key))
	    result = cursor.fetchone()
	    if result:
	      ftime2 = result[0]
              needsupdate = ftime2 > cached_time

        cursor.close()
	db.close()        
        return needsupdate

    def update(self, content, links):
	db = wikidb.connect()
        cursor = db.cursor()
	cursor.execute("start transaction")
        cursor.execute("UPDATE curPages set cachedText=%s, cachedTime=%s where name=%s", (content, time.time(), self.key))
	for link in links:
	  cursor.execute("SELECT destination_pagename from links where source_pagename=%s and destination_pagename=%s", (self.key, link))
	  result = cursor.fetchone() 
	  if not result: cursor.execute("INSERT into links values (%s, %s)", (self.key, link))
	cursor.execute("commit")
	cursor.close()
	db.close()

    def content(self):
	db = wikidb.connect()
       	cursor = db.cursor()
        cursor.execute("SELECT cachedText from curPages where name=%s", self.key)
        result = cursor.fetchone()
	cursor.close()
	db.close()
	return result[0]

    def clear(self):
        #clears the content of the cache regardless of whether or not the page needs an update
	from LocalWiki.Page import Page
	p = Page(self.key)
	content = p.get_raw_body()
	links = []
	db = wikidb.connect()
        cursor = db.cursor()
	cursor.execute("SELECT destination_pagename from links where source_pagename=%s", (self.key))
	result = cursor.fetchall()
	for entry in result:
	  links.append(entry[0])
	self.update(content, links)
