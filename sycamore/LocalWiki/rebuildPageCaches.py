import sys, cStringIO
sys.path.extend(['/usr/local/lib/python2.4/site-packages','/var/www/installhtml/dwiki'])
from LocalWiki import wikiutil, config, request, caching
from LocalWiki.Page import Page

def clearCaches():
  print "Clearing page caches..."
  plist = wikiutil.getPageList()
  arena = 'Page.py'
  for pname in plist:
    key = pname
    cache = caching.CacheEntry(arena, key)
    cache.clear()

def buildCaches():
  print "Building page caches...It is _normal_ for this to produce errors!"
  # this is hackish, but it will work
  # the idea is to view every page to build the cache
  # we should actually refactor send_page()
  req = request.RequestCGI()
  req.redirect(cStringIO.StringIO())
  for pname in wikiutil.getPageList():
   Page(pname).getPageLinks(req, docache=True)
  req.redirect()

clearCaches()
buildCaches()
