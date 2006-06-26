"""This lets you perform various maintenance tasks in your wiki.  Edit the sys.path.extend line and then run this for the options."""

import sys, cStringIO, threading, time, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', 'share'))]),
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb, search
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
  print "  -->", pname
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
  print "Building page caches..."

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
  print "-------------------------------------"
  print "  1) Rebuild all page caches."
  print "  2) Rebuild only outdated page caches."
  print "  3) Rebuild the search index."
  print "-------------------------------------"
  print "         Enter 1-3 to continue"

  choice = raw_input()
  if choice[0] == '1':
    req = request.RequestDummy()
    plist = wikiutil.getPageList(req)
    req.db_disconnect()
    buildCaches(plist)
  elif choice[0] == '2':
    req = request.RequestDummy()
    plist = wikiutil.getPageList(req)
    plist = [ pname for pname in plist if caching.CacheEntry(pname, req).needsUpdate() ] 
    req.db_disconnect()
    buildCaches(plist)
  elif choice[0] == '3':
    if not config.has_xapian:
      print "You do not have xapian...skipping."
      sys.exit()

    print "Rebuilding search index..."
    req = request.RequestDummy()

    timenow = time.time()
    tmp_db_location = os.path.join(os.path.join(config.search_db_location, ".."), "search.%s" % timenow)
    os.mkdir(tmp_db_location)

    plist = wikiutil.getPageList(req, objects=True)
    for page in plist:
      search.add_to_index(page, db_location=tmp_db_location, try_remote=False)
      print "  -->", page.page_name

    req.db_disconnect()

    # make sure search directory is set up properly
    if not os.path.exists(config.search_db_location):
      os.mkdir(config.search_db_location)
    if not os.path.exists(os.path.join(config.search_db_location, "title")):
      os.mkdir(os.path.join(config.search_db_location, "title"))
    if not os.path.exists(os.path.join(config.search_db_location, "text")):
      os.mkdir(os.path.join(config.search_db_location, "text"))

    # in POSIX os.rename is atomic
    for filename in os.listdir(os.path.join(tmp_db_location, "title")):
      os.rename(os.path.join(os.path.join(tmp_db_location, "title"), filename), os.path.join(os.path.join(config.search_db_location, "title"), filename))

    for filename in os.listdir(os.path.join(tmp_db_location, "text")):
      os.rename(os.path.join(os.path.join(tmp_db_location, "text"), filename), os.path.join(os.path.join(config.search_db_location, "text"), filename))

    os.rmdir(os.path.join(tmp_db_location, "title"))
    os.rmdir(os.path.join(tmp_db_location, "text"))
    os.rmdir(os.path.join(tmp_db_location))

    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
    print "rebuilt search index!"
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
