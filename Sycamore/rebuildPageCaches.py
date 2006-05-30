import sys, cStringIO
sys.path.extend(['/srv/wikis/rocwiki/trunk'])
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb
from Sycamore.Page import Page

def clearCaches(req):
  print "Clearing page caches..."
  plist = wikiutil.getPageList(req)
  for pname in plist:
    key = pname
    print key
    cache = caching.CacheEntry(key, req)
    cache.clear()
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
  print "cleared page caches!"
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

def buildCaches(req):
  print "Building page caches...It is _normal_ for this to produce errors!"
  # this is hackish, but it will work
  # the idea is to view every page to build the cache
  # we should actually refactor send_page()
  for pname in wikiutil.getPageList(req):
   print pname
   Page(pname, req).getPageLinks(docache=True)
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
  print "rebuilt page caches!"
  print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"


req = request.RequestDummy()
clearCaches(req)
buildCaches(req)
req.db_disconnect()
