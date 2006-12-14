"""This lets you perform various maintenance tasks in your wiki.  Edit the sys.path.extend line and then run this for the options."""

import sys, cStringIO, threading, time, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', 'share'))]),
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb, search
from Sycamore.Page import Page

MAX_THREADS = 5

def clear(wiki_name, pname, doprint=False):
  key = pname
  if doprint:
    print key
  req = request.RequestDummy(wiki_name=wiki_name)
  cache = caching.CacheEntry(key, req)
  cache.clear()
  req.db_disconnect()

def build(wiki_name, pname, doprint=False):
  if doprint: print "  -->", pname
  req = request.RequestDummy()
  Page(pname, req).buildCache()
  req.db_disconnect()

def clearCaches(wiki_name, plist, doprint=False):
  if doprint:
    print "Clearing page caches..."

  if config.db_type != 'mysql':
      i = 0 
      while True:
        if i >= len(plist):
          break
        threads = []
        for num in xrange(0, MAX_THREADS):
          if i >= len(plist):
            break
          pname = plist[i]
          t = threading.Thread(target=clear, args=(wiki_name, pname, doprint))
          threads.append(t)
          t.start()
          i += 1
        for t in threads:
          t.join()

      #while threading.activeCount() > 1:
      #  time.sleep(.1)
  # XXX FIXME
  else: # causes deadlock for mysql..not entirely sure why, but single-thread will work for now :-/
      for pname in plist:
          clear(wiki_name, pname, doprint)

  if doprint:
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
    print "Cleared page caches!"
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

def buildCaches(wiki_name, plist, doprint=False):
  if doprint: print "Building page caches..."

  if config.db_type != 'mysql':
      i = 0 
      while True:
        if i >= len(plist):
          break
        threads = []
        for num in xrange(0, MAX_THREADS):
          if i >= len(plist):
            break
          pname = plist[i]
          t = threading.Thread(target=build, args=(wiki_name, pname, doprint))
          threads.append(t)
          t.start()
          i += 1
        for t in threads:
          t.join()

  # XXX FIXME
  else: # causes deadlock for mysql..not entirely sure why, but single-thread will work for now :-/
      for pname in plist:
          build(wiki_name, pname, doprint)
   
  if doprint:
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
    print "rebuilt page caches!"
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"

if __name__ == "__main__":
  print "-------------------------------------"
  print "  1) Rebuild all page caches."
  print "  2) Rebuild only outdated page caches."
  print "  3) Rebuild the search index."
  print "  4) Update configuration options on all wikis."
  print "-------------------------------------"
  print "         Enter 1-3 to continue"

  choice = raw_input()
  if choice[0] == '1':
    req = request.RequestDummy()
    wiki_list = wikiutil.getWikiList(req)
    for wiki_name in wiki_list:
      req.switch_wiki(wiki_name)
      plist = wikiutil.getPageList(req)
      buildCaches(wiki_name, plist, doprint=True)
    req.db_disconnect()
  elif choice[0] == '2':
    req = request.RequestDummy()
    wiki_list = wikiutil.getWikiList(req)
    for wiki_name in wiki_list:
      req.switch_wiki(wiki_name)
      plist = wikiutil.getPageList(req)
      plist = [ pname for pname in plist if caching.CacheEntry(pname, req).needsUpdate() ] 
      buildCaches(wiki_name, plist)
    req.db_disconnect()
  elif choice[0] == '3':
    if not config.has_xapian:
      print "You do not have xapian...skipping."
      sys.exit()

    print "Rebuilding search index..."
    req = request.RequestDummy()

    timenow = time.time()
    # search location is created by buildDB, but let's make it in case it got removed 
    if not os.path.exists(config.search_db_location):
      os.mkdir(config.search_db_location)
    tmp_db_location = os.path.join(os.path.join(config.search_db_location, ".."), "search.%s" % timenow)
    os.mkdir(tmp_db_location)

    wiki_list = wikiutil.getWikiList(req)
    for wiki_name in wiki_list:
      req.switch_wiki(wiki_name)
      plist = wikiutil.getPageList(req)
      for pagename in plist:
        page = Page(pagename, req, wiki_name=wiki_name)
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
  elif choice[0] == '4':
    print "Updating configurations for all wikis..."
    req = request.RequestDummy()
    wiki_list = wikiutil.getWikiList(req)
    for wiki_name in wiki_list:
      print " -->", wiki_name
      req.switch_wiki(wiki_name)
      req.config.zap_config(req)
    req.db_disconnect()
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"
    print "updated all wiki configurations!"
    print "XXXXXXXXXXXXXXXXXXXXXXXXXXX"


