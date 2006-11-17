"""
Experimental nuke of edits/memory hole.
"""

import sys, cStringIO
sys.path.extend(['/Users/philipneustrom/sycamore_base/trunk'])
import __init__
from Sycamore import wikiutil, config, request, caching, wikidb
from Sycamore.Page import Page

all works on an AND basis.

purge: remove all old versions of a page.

purgeImages(request, until_point, **kw)
  --> purgeRemovedImages
  kw has:
    pages
purgePages(request, until_point, **kw)
  kw has:
    pages
  --> purgeRemovedPages
purgePoints(request, until_point)
  --> purgeRemovedPoints
  kw has:
    pages

rollBack: roll back the wiki to a particular state, with lots of parameters

  kw has:
    pages
      with optional at_point
    users
      with optional list of ips (as range) for each user
    ips (as ranges)

 rollback to state at time at_point IF
  page A,   page B,   page C
   AND       AND       AND
  user A    user A    user A
   AND       AND       AND
   IP C      IP C      IP C


rollBackImages(request, at_point, **kw)
rollBackPages(request, at_point, **kw)
rollBackPoints(request, at_point, **kw)
rollBackEvents(request, at_point, **kw)

req = request.RequestDummy()
req.db_disconnect()
