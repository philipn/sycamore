"""This will rebuild all page caches in the wiki."""

import sys, cStringIO, threading, time
sys.path.extend(['/srv/wikis/daviswikitest/trunk'])
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb
from Sycamore.Page import Page

MAX_THREADS = 10

def clear(pname):
  key = pname
  print key
  req = request.RequestDummy()
  cache = caching.CacheEntry(key, req)
  cache.clear()
  req.db_disconnect()

def build(pname):
  print pname
  req = request.RequestDummy()
  Page(pname, req).buildCache()
  req.db_disconnect()

def clearCaches(plist):
  print "Clearing page caches..."

  i = 0 
  while True:
    if i >= len(plist):
      break
    while threading.activeCount() > MAX_THREADS + 1:
      time.sleep(.01)
    pname = plist[i]
    threading.Thread(target=clear, args=(pname,)).start()
    i += 1

  while threading.activeCount() > 1:
    time.sleep(.1)

  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
  print "cleared page caches!"
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

def buildCaches(plist):
  print "Building page caches...It is _normal_ for this to produce errors!"

  i = 0 
  while True:
    if i >= len(plist):
      break
    while threading.activeCount() > MAX_THREADS + 1:
      time.sleep(.01)
    pname = plist[i]
    threading.Thread(target=build, args=(pname,)).start()
    i += 1

  while threading.activeCount() > 1:
    time.sleep(.1)
   
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
  print "rebuilt page caches!"
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

if __name__ == "__main__":
  req = request.RequestDummy()
  plist = wikiutil.getPageList(req)
  req.db_disconnect()
  
  #clearCaches(plist)
  buildCaches(plist)
