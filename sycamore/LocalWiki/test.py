import sys, re, os
sys.path.extend(['/usr/local/lib/python2.3/site-packages','/var/www/installhtml/dwiki'])
from LocalWiki import wikiutil, config, wikidb, caching
from LocalWiki.logfile import editlog

arena = 'Page.py'
key = 'PhilipNeustrom'
cache = caching.CacheEntry(arena, key)
cache.clear()
