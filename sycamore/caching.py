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
	cursor.execute("SELECT UNIX_TIMESTAMP(cachedTime) from curPages where name=%s", (self.key))
	result = cursor.fetchall()
	cursor.close()
	db.close()
	if result:
		return result[0][0]
	else: return 0

    def needsUpdate(self, pagename, attachdir=None):
        db = wikidb.connect()
        cursor = db.cursor()
        cursor.execute("SELECT UNIX_TIMESTAMP(editTime), UNIX_TIMESTAMP(cachedTime) from curPages where name=%s", (pagename))
        result = cursor.fetchall()
	cursor.close()
	db.close()
        if result:
            if result[0][0]:
		edit_time = result[0][0]
            else: return 1
            if result[0][1]:
		cached_time = result[0][1]
            else: return 1

        needsupdate = edit_time > cached_time
        
        # if a page depends on the attachment dir, we check this, too:
	# DBFIX:  attachments need to work off this once they are in the DB !! DBFIX
        if not needsupdate and attachdir:
            try:
                ftime2 = os.path.getmtime(attachdir)
            except os.error:
                ftime2 = 0
            needsupdate = ftime2 > cached_time
                
        return needsupdate

    def update(self, content, links):
	db = wikidb.connect()
        cursor = db.cursor()
	cursor.execute("start transaction")
        cursor.execute("UPDATE curPages set cachedText=%s, cachedTime=FROM_UNIXTIME(%s) where name=%s", (content, time.time(), self.key))
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
