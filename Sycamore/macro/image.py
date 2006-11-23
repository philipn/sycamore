# Part of Sycamore (projectsycamore.org) 
# -*- coding: iso-8859-1 -*-
from Sycamore import config, wikiutil, wikidb
from Sycamore.action import Files
import sys, re, os, array, time, urllib

#  [[Image(filename, caption, size, alignment, thumb, noborder)]]
#  
#  filename : name of the file, an image.
#    required. should provide error message if not present. must be the first element. all others can be in any order. 
#  
#  size : the size of the image. if size is supplied this implies it's a thumbnail. Can be either width or height depending on whichever is larger in source image. The size supplied is the desired scaled size.
#  
#  alignment : left/right. if it's a thumbnail then it gives it a usual float:left or float:right. if it's not a thumbnail then you need to wrap the image in a span that sends it left or right (i'm not sure it even needs to float..)
#  
#  thumb : this is just the string "thumb" or "thumbnail" that tells us it's a thumbnail. optional if size is supplied, if size not supplied defaults to (default size?). Should default size be a systemwide variable, or hard coded?
#  
#  noborder : just the string "noborder" to tell us, for non-thumbnails, to not use the tiny black image border. in the case it's a thumbnail, i suppose the best behavior would be to drop the caption and frame around the thumbnail (sort of consealing its thumbnail-ness)
#      (We can have a caption w/o a border, as well)
#  

IMAGE_MACRO = re.compile(r'^(\s*(\[\[image((\(.*\))|())\]\])\s*)+$')

Dependencies = []

default_px_size = 192

def recordCaption(pagename, linked_from_pagename, image_name, caption, request):
   # records the caption to the db so that we can easily look it up
   # very simple -- no versioning or anything.  just keeps it there for easy/quick reference
   #  (linked_from_pagename is for future use)
   cursor = request.cursor
   mydict = {'pagename': pagename.lower(), 'image_name': image_name, 'caption': caption, 'linked_from_pagename': linked_from_pagename, 'wiki_id': request.config.wiki_id}
   cursor.execute("SELECT image_name from imageCaptions where attached_to_pagename=%(pagename)s and image_name=%(image_name)s and linked_from_pagename=%(linked_from_pagename)s and wiki_id=%(wiki_id)s", mydict)
   result = cursor.fetchone()
   if result:
     cursor.execute("UPDATE imageCaptions set caption=%(caption)s where attached_to_pagename=%(pagename)s and image_name=%(image_name)s and linked_from_pagename=%(linked_from_pagename)s and wiki_id=%(wiki_id)s", mydict)
   else:
     cursor.execute("INSERT into imageCaptions (attached_to_pagename, image_name, caption, linked_from_pagename, wiki_id) values (%(pagename)s, %(image_name)s, %(caption)s, %(linked_from_pagename)s, %(wiki_id)s)", mydict)

def deleteCaption(pagename, linked_from_pagename, image_name, request):
   request.cursor.execute("DELETE from imageCaptions where attached_to_pagename=%(pagename)s and image_name=%(image_name)s and linked_from_pagename=%(linked_from_pagename)s and wiki_id=%(wiki_id)s", {'pagename':pagename.lower(), 'image_name':image_name, 'linked_from_pagename':linked_from_pagename, 'wiki_id':request.config.wiki_id})


def getImageSize(pagename, image_name, request):
    # gets the size of an image (not a thumbnail) in the DB
    request.cursor.execute("SELECT xsize, ysize from imageInfo where attached_to_pagename=%(pagename)s and name=%(image_name)s and wiki_id=%(wiki_id)s", {'pagename':pagename.lower(), 'image_name':image_name, 'wiki_id':request.config.wiki_id})
    result = request.cursor.fetchone()
    if result:
      return (result[0], result[1])
    else:
      return (0, 0)

def touchCaption(pagename, linked_from_pagename, image_name, caption, request):
    stale = True
    db_caption = ''
    cursor = request.cursor
    cursor.execute("SELECT caption from imageCaptions where attached_to_pagename=%(pagename)s and linked_from_pagename=%(linked_from_pagename)s and image_name=%(image_name)s and wiki_id=%(wiki_id)s", {'pagename':pagename.lower(), 'linked_from_pagename':linked_from_pagename, 'image_name':image_name, 'wiki_id':request.config.wiki_id})
    result = cursor.fetchone()
    if result: db_caption = result[0] 
    if caption != db_caption: 
      recordCaption(pagename, linked_from_pagename, image_name, caption, request)
    if not caption:
      deleteCaption(pagename, linked_from_pagename, image_name, request)

def touchThumbnail(request, pagename, image_name, maxsize, formatter):
    # we test formatter.name because we use isPreview() to force some things to be ignored on the second-formatting phase with the python formatter.
    # in this case, we want to render a temporary thumbnail when we're in an actual preview or viewing an old version of a page, not when we're doing
    # the formatting phase of a normal page save
    temporary = (formatter.isPreview() and formatter.name != 'text_python') or formatter.page.prev_date
    if temporary:
      ticket = _createTicket()
      return (generateThumbnail(request, pagename, image_name, maxsize, temporary=True, ticket=ticket), ticket)
    cursor = request.cursor
    # first we see if the thumbnail is there with the proper size
    cursor.execute("SELECT xsize, ysize from thumbnails where name=%(image_name)s and attached_to_pagename=%(pagename)s and wiki_id=%(wiki_id)s", {'image_name':image_name, 'pagename':pagename.lower(), 'wiki_id':request.config.wiki_id})
    result = cursor.fetchone()
    if result:
     if result[0] and result[1]:
      x = result[0]
      y = result[1]
      if max(x, y) == maxsize:
      	# this means the thumbnail is the right size
        return ((x, y), None)
    # we need to generate a new thumbnail of the right size
    return (generateThumbnail(request, pagename, image_name, maxsize), None)

def generateThumbnail(request, pagename, image_name, maxsize, temporary=False, ticket=None, return_image=False):
    cursor = request.cursor 
    from PIL import Image
    import cStringIO
    dict = {'filename':image_name, 'page_name':pagename}

    open_imagefile = cStringIO.StringIO(wikidb.getFile(request, dict)[0])
    im = Image.open(open_imagefile)
    converted = 0
    if not im.palette is None:
       if im.info.has_key('transparency'):
         trans = im.info['transparency']
         pal = []
         ind = 0
         numcols = len(im.palette.palette) / 3;
         while ind < numcols:
           if ind == trans:
             pal.append( ord('\xff') )
             pal.append(ord('\xff'))
             pal.append( ord('\xff'))
           else:
             pal.append(ord(im.palette.palette[ind * 3]))
             pal.append(ord(im.palette.palette[ind * 3 + 1]))
             pal.append(ord(im.palette.palette[ind * 3 + 2]))
           ind = ind + 1
         im.putpalette(pal)
       im = im.convert("RGB")
       converted = 1
    if im.size[0] >= im.size[1]:
       max = im.size[0]
       min = im.size[1]
       if maxsize >= max:
         shrunk_im = im
         x, y = im.size
       else:
         x = maxsize
         y = int((min * maxsize)/max)
         shrunk_im = im.resize((x, y), Image.ANTIALIAS)
    else:
       max = im.size[1]
       min = im.size[0]
       if maxsize >= max:
         shrunk_im = im
         x, y = im.size
       else:
         x = int((min * maxsize)/max)
         y = maxsize
         shrunk_im = im.resize((x,y), Image.ANTIALIAS)
    if converted == 1:
      shrunk_im = shrunk_im.convert("P",dither=Image.NONE, palette=Image.ADAPTIVE)

    import mimetypes
    type = mimetypes.guess_type(image_name)[0][6:]
    save_imagefile = cStringIO.StringIO()
    try:
      shrunk_im.save(save_imagefile, type, quality=90)
    except IOError:
      request.write('<em style="background-color: #ffffaa; padding: 2px;">There was a problem with image %s.  It probably has the wrong file extension.</em>' % image_name)
    image_value = save_imagefile.getvalue()
    if return_image:
      # one-time generation for certain things like preview..just return the image string
      return image_value
    dict = {'x':x, 'y':y, 'filecontent':image_value, 'uploaded_time':time.time(), 'filename':image_name, 'pagename':pagename}
    wikidb.putFile(request, dict, thumbnail=True, temporary=temporary, ticket=ticket)

    save_imagefile.close()
    open_imagefile.close()
    
    return x, y

def getArguments(args, request):
    #filename stuff
    split_args = args.split(',')
    f_end_loc = len(split_args[0])
    image_name = split_args[0].strip()

    caption = ''
    px_size = 0
    alignment = ''
    thumbnail = False
    border = True

    # gross, but let's find the caption, if it's there
    q_start = args.find('"')
    q_end = 0
    if q_start != -1:
      # we have a quote
      q_end = q_start
      quote_loc = args[q_end+1:].find('"')
      q_end += quote_loc + 1
      while quote_loc != -1:
        quote_loc = args[q_end+1:].find('"')
        q_end += quote_loc + 1
      caption = args[q_start+1:q_end]
    else:
      q_start = 0

    # let's get the arguments without the caption or filename
    if caption:
      simplier_args = args[f_end_loc+1:q_start] + args[q_end+1:]
      list_args = simplier_args.split(',') # now our split will work to actually split properly
    else:
      list_args = args.split(',')[1:]

    for arg in list_args:
      clean_arg = arg.strip().lower()
      if clean_arg.startswith('thumb'):
        thumbnail = True
      elif clean_arg == 'noborder':
        border = False
      elif clean_arg == 'left':
        alignment = 'left'
      elif clean_arg == 'right':
        alignment = 'right'
      elif clean_arg and clean_arg[0] in ['1','2','3','4','5','6','7','8','9']:
        px_size = int(arg) 
	  
    return (image_name, caption, thumbnail, px_size, alignment, border)

def line_has_just_macro(macro, args, formatter):
  line = macro.parser.lines[macro.parser.lineno-1].lower().strip()
  if IMAGE_MACRO.match(line):
    return True
  return False


def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    if line_has_just_macro(macro, args, formatter):
      macro.parser.inhibit_br = 2

    baseurl = macro.request.getScriptname()
    action = 'Files' # name of the action that does the file stuff
    html = []
    ticketString = None # for temporary thumbnail generation
    pagename = formatter.page.page_name
    urlpagename = wikiutil.quoteWikiname(formatter.page.proper_name())

    if not args:
        return formatter.rawHTML('<b>Please supply at least an image name, e.g. [[Image(image.jpg)]], where image.jpg is an image that\'s been uploaded to this page.</b>')

    # image.jpg, "caption, here, yes", 20, right --- in any order (filename first)
    # the number is the 'max' size (width or height) in pixels

    # parse the arguments
    try:
      image_name, caption, thumbnail, px_size, alignment, border = getArguments(args, macro.request)
    except:
      return formatter.rawHTML('[[Image(%s)]]' % wikiutil.escape(args))

    if not wikiutil.isImage(image_name):
      return "%s does not seem to be an image file." % image_name

    url_image_name = urllib.quote(image_name)

    if formatter.isPreview() or formatter.page.prev_date:
      if macro.formatter.processed_thumbnails.has_key((pagename, image_name)) and (thumbnail or caption):
         return '<em style="background-color: #ffffaa; padding: 2px;">A thumbnail or caption may be displayed only once per image.</em>'
      macro.formatter.processed_thumbnails[(pagename, image_name)] = True

    #is the original image even on the page?
    macro.request.cursor.execute("SELECT name from files where name=%(image_name)s and attached_to_pagename=%(pagename)s and wiki_id=%(wiki_id)s", {'image_name':image_name, 'pagename':pagename.lower(), 'wiki_id':macro.request.config.wiki_id})
    result = macro.request.cursor.fetchone()
    image_exists = result

    if not image_exists:
      #lets make a link telling them they can upload the image, just like the normal attachment
      linktext = 'Upload new image "%s"' % (image_name)
      return wikiutil.attach_link_tag(macro.request,
                '%s?action=Files&amp;rename=%s#uploadFileArea' % (
                    wikiutil.quoteWikiname(formatter.page.proper_name()),
                    url_image_name),
                linktext)

    full_size_url = baseurl + "/" + urlpagename + "?action=" + action + "&amp;do=view&amp;target=" + url_image_name
    # put the caption in the db if it's new and if we're not in preview mode
    if not formatter.isPreview(): touchCaption(pagename, pagename, image_name, caption, macro.request)
    if caption:
      # parse the caption string
      caption = wikiutil.wikifyString(caption, formatter.request, formatter.page, formatter=formatter)

    if thumbnail:
      # let's generated the thumbnail or get the dimensions if it's already been generated
      if not px_size: px_size = default_px_size
      (x, y), ticketString = touchThumbnail(macro.request, pagename, image_name, px_size, formatter)

      d = { 'right':'floatRight', 'left':'floatLeft', '':'noFloat' }
      floatSide = d[alignment]
      if caption and border:
        html.append('<span class="%s thumb" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s" alt="%s"/></a><div>%s</div></span>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, thumb=True, size=px_size, ticket=ticketString), image_name, caption))
      elif border:
        html.append('<span class="%s thumb" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s" alt="%s"/></a></span>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, thumb=True, size=px_size, ticket=ticketString), image_name))
      elif caption and not border:
        html.append('<span class="%s thumb noborder" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s" alt="%s"/></a><div>%s</div></span>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, thumb=True, size=px_size, ticket=ticketString), image_name, caption))
      else:
        html.append('<span class="%s thumb noborder" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s" alt="%s"/></a></span>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, thumb=True, size=px_size, ticket=ticketString), image_name))
    else:
      x, y = getImageSize(pagename, image_name, macro.request)
      if not border and not caption:
        img_string = '<a href="%s"><img class="borderless" src="%s" alt="%s"/></a>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, ticket=ticketString), image_name)
      elif border and not caption:
        img_string = '<a href="%s"><img class="border" src="%s" alt="%s"/></a>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, ticket=ticketString), image_name)
      elif border and caption:
        img_string = '<a href="%s"><img class="border" src="%s" alt="%s"/></a><div style="width: %spx;"><p class="normalCaption">%s</p></div>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, ticket=ticketString), image_name, x, caption)
      elif not border and caption:
        img_string = '<a href="%s"><img class="borderless" src="%s" alt="%s"/></a><div style="width: %spx;"><p class="normalCaption">%s</p></div>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, ticket=ticketString), image_name, x, caption)
      if alignment == 'right': img_string = '<span class="floatRight">' + img_string + '</span>'
      elif alignment == 'left': img_string = '<span class="floatLeft">' + img_string + '</span>'

      html.append(img_string)
      
    return ''.join(html)

def _createTicket(tm = None):
    """Create a ticket using a site-specific secret (the config)"""
    import sha, types
    if tm: tm = int(tm) 
    else: tm = int(time.time())
    ticket_hex = "%010x" % tm
    digest = sha.new()
    digest.update(ticket_hex)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return str(tm) + '.' + digest.hexdigest()

def checkTicket(ticket):
    """Check validity of a previously created ticket"""
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return (ticket == ourticket) and ((time.time()-60) < int(timestamp))
