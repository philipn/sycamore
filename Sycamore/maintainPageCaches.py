""" This will build page caches only for pages that need the cache built. """

import sys, cStringIO, threading, time
sys.path.extend(['/srv/wikis/daviswiki/trunk'])
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb, rebuildPageCaches
from Sycamore.Page import Page

def buildCaches(plist):
  print "Building page caches...It is _normal_ for this to produce errors!"
  # this is hackish, but it will work
  # the idea is to view every page to build the cache
  # we should actually refactor send_page()
  for pname in plist:
    threading.Thread(target=rebuildPageCaches.build, args=(pname,)).start()
  while threading.activeCount() > 1:
    time.sleep(.1)
   
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
  print "rebuilt page caches!"
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

if __name__ == "__main__":
  req = request.RequestDummy()
  plist = wikiutil.getPageList(req)
  plist = [ pname for pname in plist if caching.CacheEntry(pname, req).needsUpdate() ] 
  req.db_disconnect()
  
  buildCaches(plist)
