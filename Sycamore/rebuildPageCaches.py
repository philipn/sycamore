import sys, cStringIO
sys.path.extend(['/srv/wikis/rocwiki/trunk'])
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb
from Sycamore.Page import Page

def clearCaches():
  print "Clearing page caches..."
  req = request.RequestDummy()
  plist = wikiutil.getPageList(req)
  for pname in plist:
    key = pname
    cache = caching.CacheEntry(key, req)
    cache.clear()

def buildCaches():
  print "Building page caches...It is _normal_ for this to produce errors!"
  # this is hackish, but it will work
  # the idea is to view every page to build the cache
  # we should actually refactor send_page()
  req = request.RequestDummy()
  for pname in wikiutil.getPageList(req):
   Page(pname, req).getPageLinks(docache=True)

clearCaches()
buildCaches()
