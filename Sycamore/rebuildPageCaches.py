import sys, cStringIO
sys.path.extend(['/srv/wikis/daviswiki/trunk'])
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb
from Sycamore.Page import Page

def clearCaches(plist):
  print "Clearing page caches..."
  for pname in plist:
    key = pname
    print key
    req = request.RequestDummy()
    cache = caching.CacheEntry(key, req)
    cache.clear()
    req.db_disconnect()
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
  print "cleared page caches!"
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

def buildCaches(plist):
  print "Building page caches...It is _normal_ for this to produce errors!"
  # this is hackish, but it will work
  # the idea is to view every page to build the cache
  # we should actually refactor send_page()
  for pname in plist:
   print pname
   req = request.RequestDummy()
   Page(pname, req).getPageLinks(docache=True)
   req.db_disconnect()
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
  print "rebuilt page caches!"
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

req = request.RequestDummy()
plist = wikiutil.getPageList(req)
req.db_disconnect()

clearCaches(plist)
buildCaches(plist)
