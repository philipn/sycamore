# -*- coding: iso-8859-1 -*-
"""
    LocalWiki caching module

    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, shutil

from LocalWiki import config

class CacheEntry:
    def __init__(self, arena, key):
        self.arena = arena
        self.key = key

        # create cache if necessary
        if not os.path.isdir(config.cache_dir):
            os.mkdir(config.cache_dir, 0777 & config.umask)
            os.chmod(config.cache_dir, 0777 & config.umask)

        # create arena if necessary
        arena_dir = os.path.join(config.cache_dir, arena)
        if not os.path.isdir(arena_dir):
            os.mkdir(arena_dir, 0777 & config.umask)
            os.chmod(arena_dir, 0777 & config.umask)

    def _filename(self):
        return os.path.join(config.cache_dir, self.arena, self.key)

    def exists(self):
        return os.path.exists(self._filename())

    def mtime(self):
        try:
            return os.path.getmtime(self._filename())
        except IOError:
            return 0

    def needsUpdate(self, filename, attachdir=None):
        if not self.exists() or not os.path.exists(filename): return 1

        try:
            ctime = os.path.getmtime(self._filename())
            ftime = os.path.getmtime(filename)
        except os.error:
            return 1

        needsupdate = ftime > ctime
        
        # if a page depends on the attachment dir, we check this, too:
        if not needsupdate and attachdir:
            try:
                ftime2 = os.path.getmtime(attachdir)
            except os.error:
                ftime2 = 0
            needsupdate = ftime2 > ctime
                
        return needsupdate

    def copyto(self, filename):
        shutil.copyfile(filename, self._filename())

        try:
            os.chmod(self._filename(), 0666 & config.umask)
        except OSError:
            pass

    def update(self, content):
        open(self._filename(), 'wb').write(content)

        try:
            os.chmod(self._filename(), 0666 & config.umask)
        except OSError:
            pass

    def remove(self):
        try:
            os.remove(self._filename())
        except OSError:
            pass

    def content(self):
	if os.path.exists(self._filename()):
        	return open(self._filename(), 'rb').read()

