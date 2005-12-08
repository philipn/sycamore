# Part of the Local Wiki (http://daviswiki.org) Project
# -*- coding: iso-8859-1 -*-
from LocalWiki import config, wikiutil, wikidb
from LocalWiki.action import Files
import sys, re, os, array

#  [[Image(filename, caption, size, alignment, thumb, noborder)]]
#  
#  filename : name of the file, an image.
#    required. should provide error message if not present. must be the first element. all others can be in any order. 
#  
#  size : the size of the image. if size is supplied this implies it's a thumbnail. Can be either width or height depending on whichever is larger in source image. The size supplied is the desired scaled size.
#  
#  alignment : left/right. if it's a thumbnail then it gives it a usual float:left or float:right. if it's not a thumbnail then you need to wrap the image in a div that sends it left or right (i'm not sure it even needs to float..)
#  
#  thumb : this is just the string "thumb" or "thumbnail" that tells us it's a thumbnail. optional if size is supplied, if size not supplied defaults to (default size?). Should default size be a systemwide variable, or hard coded?
#  
#  noborder : just the string "noborder" to tell us, for non-thumbnails, to not use the tiny black image border. in the case it's a thumbnail, i suppose the best behavior would be to drop the caption and frame around the thumbnail (sort of consealing its thumbnail-ness)
#      (We can have a caption w/o a border, as well)
#  


# we want 'new' links to show up properly, and we want the image to change if deleted/reuploaded/etc.
Dependencies = ["pages"]

default_px_size = 192

def recordCaption(pagename, linked_from_pagename, image_name, caption, cursor):
   # records the caption to the db so that we can easily look it up
   # very simple -- no versioning or anything.  just keeps it there for easy/quick reference
   #  (linked_from_pagename is for future use)
   cursor.execute("SELECT image_name from imageCaptions where attached_to_pagename=%s and image_name=%s and linked_from_pagename=%s", (pagename, image_name, linked_from_pagename))
   result = cursor.fetchone()
   if result:
     cursor.execute("UPDATE imageCaptions set caption=%s where attached_to_pagename=%s and image_name=%s and linked_from_pagename=%s", (caption, pagename, image_name, linked_from_pagename))
   else:
     cursor.execute("INSERT into imageCaptions set attached_to_pagename=%s, image_name=%s, caption=%s, linked_from_pagename=%s", (pagename, image_name, caption, linked_from_pagename))

def deleteCaption(pagename, linked_from_pagename, image_name, cursor):
   cursor.execute("DELETE from imageCaptions where attached_to_pagename=%s and image_name=%s and linked_from_pagename=%s", (pagename, image_name, linked_from_pagename))



def getImageSize(pagename, image_name):
    # gets the size of an image (not a thumbnail) in the DB
    db = wikidb.connect()
    cursor = db.cursor()
    cursor.execute("SELECT xsize, ysize from images where attached_to_pagename=%s and name=%s", (pagename, image_name))
    result = cursor.fetchone()
    if result:
      return (result[0], result[1])
    else:
      return (0, 0)

def touchCaption(pagename, linked_from_pagename, image_name, caption):
    stale = True
    db_caption = ''
    db = wikidb.connect()
    cursor = db.cursor()
    cursor.execute("start transaction;")
    cursor.execute("SELECT caption from imageCaptions where attached_to_pagename=%s and linked_from_pagename=%s and image_name=%s", (pagename, linked_from_pagename, image_name))
    result = cursor.fetchone()
    if result: db_caption = result[0] 
    if caption != db_caption: 
      recordCaption(pagename, linked_from_pagename, image_name, caption, cursor)
    if not caption:
      deleteCaption(pagename, linked_from_pagename, image_name, cursor)
    cursor.execute("commit;") 
    cursor.close()
    db.close()


def touchThumbnail(pagename, image_name, maxsize=0):
    if not maxsize: maxsize = default_px_size
    db = wikidb.connect()
    cursor = db.cursor()
    # first we see if the thumbnail is there with the proper size
    cursor.execute("SELECT xsize, ysize from thumbnails where name=%s and attached_to_pagename=%s", (image_name, pagename))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    if result:
     if result[0] and result[1]:
      x = result[0]
      y = result[1]
      if max(x, y) == maxsize:
      	# this means the thumbnail is the right size
        return x, y
    # we need to generate a new thumbnail of the right size
    return generateThumbnail(pagename, image_name, maxsize)

def generateThumbnail(pagename, image_name, maxsize):
    from PIL import Image
    import cStringIO,time

    db = wikidb.connect()
    cursor = db.cursor()
    cursor.execute("SELECT image from images where name=%s and attached_to_pagename=%s", (image_name, pagename))
    result = cursor.fetchone()
    	
    open_imagefile = cStringIO.StringIO(result[0].tostring())
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
    shrunk_im.save(save_imagefile, type, quality=90)
    cursor.execute("SELECT name from thumbnails where name=%s and attached_to_pagename=%s", (image_name, pagename))
    thumb_exists = cursor.fetchone()
    if thumb_exists:
      image_value = save_imagefile.getvalue()
      cursor.execute("start transaction;")
      cursor.execute("UPDATE thumbnails set xsize=%s, ysize=%s, image=%s, last_modified=%s where name=%s and attached_to_pagename=%s;", (x, y, image_value, time.time(), image_name, pagename))
    else:
      cursor.execute("start transaction;")
      cursor.execute("INSERT into thumbnails set xsize=%s, ysize=%s, image=%s, name=%s, last_modified=%s, attached_to_pagename=%s;", (x, y, save_imagefile.getvalue(),image_name, time.time(), pagename))

    cursor.execute("commit;")
    cursor.close()
    db.close()
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


def execute(macro, args):
    baseurl = macro.request.getScriptname()
    action = 'Files' # name of the action that does the file stuff
    html = []
    pagename = macro.formatter.page.page_name
    urlpagename = wikiutil.quoteWikiname(pagename)

    if not args:
        return macro.formatter.rawHTML('<b>Please supply at least an image name, e.g. [[Image(image.jpg)]], where image.jpg is an image that\'s been uploaded to this page.</b>')

    import urllib
    # image.jpg, "caption, here, yes", 20, right --- in any order (filename first)
    # the number is the 'max' size (width or height) in pixels

    # parse the arguments
    image_name, caption, thumbnail, px_size, alignment, border = getArguments(args, macro.request)

    #is the original image even on the page?
    db = wikidb.connect()
    cursor = db.cursor()
    cursor.execute("SELECT name from images where name=%s and attached_to_pagename=%s", (image_name, pagename))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    image_exists = result

    if not image_exists:
      #lets make a link telling them they can upload the image, just like the normal attachment
      linktext = 'Upload new image "%s"' % (image_name)
      return wikiutil.attach_link_tag(macro.request,
                '%s?action=Files&amp;rename=%s%s' % (
                    wikiutil.quoteWikiname(pagename),
                    image_name,
                    ''),
                linktext)

    full_size_url = baseurl + "/" + urlpagename + "?action=" + action + "&do=view&target=" + image_name
    # put the caption in the db if it's new and if we're not in preview mode
    if not macro.formatter.isPreview(): touchCaption(pagename, pagename, image_name, caption)
    if caption:
      # parse the caption string
      caption = wikiutil.wikifyString(caption, macro.request)

    if thumbnail:
      # let's generated the thumbnail or get the dimensions if it's already been generated
      x, y = touchThumbnail(pagename, image_name, px_size)	
      d = { 'right':'floatRight', 'left':'floatLeft', '':'noFloat' }
      floatSide = d[alignment]
      if caption and border:
        html.append('<div class="%s thumb" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s"/></a><div>%s</div></div>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, thumb=True, size=px_size),caption))
      elif border:
        html.append('<div class="%s thumb" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s"/></a></div>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, thumb=True, size=px_size)))
      elif caption and not border:
        html.append('<div class="%s thumb noborder" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s"/></a><div>%s</div></div>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, image_name, macro.request, thumb=True, size=px_size),caption))
    else:
      x, y = getImageSize(pagename, image_name)
      if not border and not caption:
        img_string = '<a href="%s"><img class="borderless" src="%s"/></a>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request))
      elif border and not caption:
        img_string = '<a href="%s"><img class="border" src="%s"/></a>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request))
      elif border and caption:
        img_string = '<a href="%s"><img class="border" src="%s"/></a><div style="width: %spx;"><p class="normalCaption">%s</p></div>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request), x, caption)
      elif not border and caption:
        img_string = '<a href="%s"><img class="borderless" src="%s"/></a><div style="width: %spx;"><p class="normalCaption">%s</p></div></div>' % (full_size_url, Files.getAttachUrl(pagename, image_name, macro.request), x, caption)
      if alignment == 'right': img_string = '<div class="floatRight">' + img_string + '</div>'
      elif alignment == 'left': img_string = '<div class="floatLeft">' + img_string + '</div>'

      html.append(img_string)
      


    return ''.join(html)
