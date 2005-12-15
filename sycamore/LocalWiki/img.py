# This is the code that's use for serving up an image from the database.
#It's called from RequestBase.run() if the query string indicates we want an image

from LocalWiki import wikiutil, wikidb
import os, urllib, mimetypes, re, time
from LocalWiki import config

# We get the pagename as a wikiutil.quoteWikiname()
# We wikiutil.unquoteWikiname() it and then grab the given image from the pagename from the db

def imgSend(request):
  # Front_Page?file=larry_coho.jpg&thumb=yes&size=240
  # httpd_referer is like "http://daviswiki.org/blahblah/page?test=goajf" -- the whole string.
  # let's test against it using their possibly configured regular expression.  this is to prevent image hotlinking


  if config.referer_regexp:
    allowed = re.search(config.referer_regexp, request.http_referer)
  else: allowed = True
  
  if not allowed:
    # this should do a 'return' when incorporated into the LocalWiki code
    #return
    return
  
  deleted = False
  version = ''
  thumbnail = False
  thumbnail_size = 0
  
  pagename_encoded = request.path_info[1:]
  pagename = wikiutil.unquoteWikiname(pagename_encoded)
  qsplit = request.query_string.split('&')
  filename_encoded = qsplit[1][5:]
  if len(qsplit) > 2:
    if qsplit[2] == 'deleted=true': deleted = True
    if len(qsplit) >= 3:
     if qsplit[2] == 'thumb=yes':
       thumbnail = True
       if len(qsplit) > 3:
         if qsplit[3].startswith('size='): thumbnail_size = int(qsplit[3][5:])
     if len(qsplit) >= 4:
       if qsplit[2].startswith('version='):  version = qsplit[3][8:]
  
  filename = urllib.unquote_plus(filename_encoded)
  
  cursor = request.db.cursor()
  if not deleted:
    if not thumbnail:
      cursor.execute("SELECT image, uploaded_time from images where name=%s and attached_to_pagename=%s", (filename, pagename))
    else:
      cursor.execute("SELECT image, last_modified from thumbnails where name=%s and attached_to_pagename=%s", (filename, pagename))
  
    result = cursor.fetchone()
  else:
    if not version:
      # default behavior is to just grab the most recently deleted version of the image
      cursor.execute("SELECT image, uploaded_time from oldImages where name=%s and attached_to_pagename=%s order by uploaded_time desc;", (filename, pagename))
    else:
      cursor.execute("SELECT image, uploaded_time from oldImages where name=%s and attached_to_pagename=%s and uploaded_time=%s", (filename, pagename, version))
    result = cursor.fetchone()
  cursor.close()
  
  
  if result:
    image = result[0]
    modified_time_unix = result[1]
  
    mimetype = mimetypes.guess_type(filename)[0]
    
    if mimetype:
      # we're good to go to output the image
      datestring = time.strftime('%a, %d %b %Y %H:%M:%S', time.gmtime(modified_time_unix)) + ' GMT' 
      request.http_headers(["Content-Type: " + mimetype, "Last-Modified: " + datestring])
      #output image
      request.write(image.tostring())
    else:
      request.http_headers(["Content-Type: text/html"])
      request.write("No image..?")
  
  else:
    request.http_headers(["Content-Type: text/html"])
    request.write("No image..?")
