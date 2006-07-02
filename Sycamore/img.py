# This is the code that's use for serving up an image from the database.
#It's called from RequestBase.run() if the query string indicates we want an image

from Sycamore import wikidb
from Sycamore.macro.image import checkTicket
import os, urllib, mimetypes, re, time
from Sycamore import config
from Sycamore.wikiutil import unquoteWikiname

# We get the pagename as a wikiutil.quoteWikiname()
# We wikiutil.unquoteWikiname() it and then grab the given image from the pagename from the db

def imgSend(request):
  # Front_Page?file=larry_coho.jpg&thumb=yes&size=240

  # httpd_referer is like "http://daviswiki.org/blahblah/page?test=goajf" -- the whole string.
  # let's test against it using their possibly configured regular expression.  this is to prevent image hotlinking
  if config.referer_regexp:
    allowed = re.search(config.referer_regexp, request.http_referer, re.IGNORECASE)
  else: allowed = True
  
  if not allowed:
    # this should do a 'return' when incorporated into the Sycamore code
    #return
    return
  
  deleted = False
  version = 0
  thumbnail = False
  thumbnail_size = 0
  ticket = None
  size = None

  pagename = request.pagename
  
  filename_encoded = request.form['file'][0]
  if request.form.has_key('deleted'):
    if request.form['deleted'][0] == 'true': deleted = True
  if request.form.has_key('thumb'):
    if request.form['thumb'][0] == 'yes': thumbnail = True
  if request.form.has_key('size'):
    thumbnail_size = int(request.form['size'][0])
  if request.form.has_key('version'):
    version = float(request.form['version'][0])
  if request.form.has_key('ticket'):
    ticket = request.form['ticket'][0]
    if not checkTicket(ticket) or not request.form.has_key('size'):
       request.http_headers()
       request.write("No image..?")
       return
    try:
      size = int(request.form['size'][0])
    except:
       request.http_headers()
       request.write("No image..?")

  filename = urllib.unquote(filename_encoded)
  d = {'filename':filename, 'page_name':pagename, 'image_version':version, 'maxsize': size} 
  try:
    image, modified_time_unix = wikidb.getImage(request, d, deleted=deleted, thumbnail=thumbnail, version=version, ticket=ticket)
  except:
    request.http_headers()
    request.write("No image..?")
    return

  mimetype = mimetypes.guess_type(filename)[0]
  
  if mimetype:
    # we're good to go to output the image
    if modified_time_unix is None: modified_time_unix = 0
    datestring = time.strftime('%a, %d %b %Y %H:%M:%S', time.gmtime(modified_time_unix)) + ' GMT' 
    # images are usually compressed anyway, so let's not bother gziping
    request.do_gzip = False
    request.http_headers([("Content-Type", mimetype), ("Last-Modified", datestring)])
    #output image
    request.write(image, raw=True)
  else:
    request.http_headers()
    request.write("No image..?")
    return
