# Part of the Local Wiki (http://daviswiki.org) Project
# -*- coding: iso-8859-1 -*-
from LocalWiki import config, wikiutil, wikidb
from LocalWiki.action import Files
import sys, re, os, array

Dependencies = []

def touchThumbnail(pagename, image_name, maxsize=0):
    if not maxsize: maxsize = 192
    db = wikidb.connect()
    cursor = db.cursor()
    # first we see if the thumbnail is there with the proper size
    cursor.execute("SELECT xsize, ysize from thumbnails where name=%s and attached_to_pagename=%s", (image_name, pagename))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    if result:
      x = result[0]
      y = result[1]
      if max(x, y) == maxsize:
      	# this means the thumbnail is the right size
        return x, y
    # we need to generate a new thumbnail of the right size
    return generateThumbnail(pagename, image_name, maxsize)

def generateThumbnail(pagename, image_name, maxsize):
    from PIL import Image
    import cStringIO

    db = wikidb.connect()
    cursor = db.cursor()
    # first we see if the thumbnail is there with the proper size
    cursor.execute("SELECT image from images where name=%s and attached_to_pagename=%s", (image_name, pagename))
    result = cursor.fetchone()
    	
    imagefile = cStringIO.StringIO(result[0].tostring())
    im = Image.open(imagefile)
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
      image_extension = 'png'

    imagefile.close()
    import mimetypes
    type = mimetypes.guess_type(image_name)[0][6:]
    imagefile = cStringIO.StringIO()
    shrunk_im.save(imagefile, type, quality=90)
    cursor.execute("SELECT name from thumbnails where name=%s and attached_to_pagename=%s", (image_name, pagename))
    thumb_exists = cursor.fetchone()
    if thumb_exists:
      image_value = imagefile.getvalue()
      cursor.execute("start transaction;")
      cursor.execute("UPDATE thumbnails set xsize=%s, ysize=%s, image=%s where name=%s and attached_to_pagename=%s;", (x, y, image_value,image_name, pagename))
      cursor.execute("commit;")
    else:
      cursor.execute("start transaction;")
      cursor.execute("INSERT into thumbnails set xsize=%s, ysize=%s, image=%s, name=%s, attached_to_pagename=%s;", (x, y, imagefile.getvalue(),image_name, pagename))
      cursor.execute("commit;")

    
    return x, y


def execute(macro, args):
    baseurl = macro.request.getScriptname()
    action = 'Files' # name of the action that does the file stuff
    html = []
    pagename = macro.formatter.page.page_name
    urlpagename = wikiutil.quoteWikiname(pagename)

    if not args:
        return macro.formatter.rawHTML('<b>Please supply at least an image name, e.g. [[Thumbnail(image.jpg)]], where image.jpg is an image that\'s been uploaded to this page.</b>')

    import urllib
    # image.jpg, "caption, here, yes", 20, right --- in any order (filename first)
    # the number is the 'max' size (width or height) in pixels

    # parse the arguments
    re_obj = re.match('(?P<image_name>.*?)\.(?P<extension>jpg|jpeg|png|gif)(?P<the_rest>.*)', args, re.IGNORECASE) 
    image_extension = re_obj.group('extension')
    image_name = re_obj.group('image_name')

    full_image_name = image_name + "." + image_extension
    #is the original image even on the page?
    db = wikidb.connect()
    cursor = db.cursor()
    cursor.execute("SELECT name from images where name=%s and attached_to_pagename=%s", (full_image_name, pagename))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    image_exists = result

    if not image_exists:
      #lets make a link telling them they can upload the image, just like the normal attachment
      linktext = 'Upload new image "%s"' % (full_image_name)
      return wikiutil.attach_link_tag(macro.request,
                '%s?action=Files&amp;rename=%s%s' % (
                    wikiutil.quoteWikiname(macro.formatter.page.page_name),
                    full_image_name,
                    ''),
                linktext)

    the_rest = re_obj.group('the_rest')
    re_obj = re.search('.+?"(?P<caption>.+)"', the_rest)
    if re_obj is not None:
        caption = re_obj.group('caption')
	caption = wikiutil.escape(caption)
        caption = wikiutil.simpleParse(macro.request, caption)
    else:
        caption = ''
    re_obj = re.search('\,(\s)*?(?P<size>[0-9]+)(\s)*?(\,){0,1}', the_rest) 
    # px_size is our 'max'
    if re_obj is not None:
      px_size = int(re_obj.group('size'))
    else:
      px_size = 192
    re_obj = re.search('\,( )*?(?P<alignment>(right)|(left))( )*?(\,){0,1}', the_rest)
    if re_obj:
      alignment = re_obj.group('alignment')
    else:
      alignment = ''
   
    # let's generated the thumbnail or get the dimensions if it's already been generated
    x, y = touchThumbnail(macro.formatter.page.page_name, full_image_name, px_size)	

      ## open the original image
      #from PIL import Image
      #im = Image.open(image_location + full_image_name)
      #converted = 0
      #if not im.palette is None:
      #   if im.info.has_key('transparency'):
      #     trans = im.info['transparency']
      #     pal = []
      #     ind = 0
      #     numcols = len(im.palette.palette) / 3;
      #     while ind < numcols:
      #       if ind == trans:
      #         pal.append( ord('\xff') )
      #         pal.append(ord('\xff'))
      #         pal.append( ord('\xff'))
      #       else:
      #         pal.append(ord(im.palette.palette[ind * 3]))
      #         pal.append(ord(im.palette.palette[ind * 3 + 1]))
      #         pal.append(ord(im.palette.palette[ind * 3 + 2]))
      #       ind = ind + 1
      #     im.putpalette(pal)
      #   im = im.convert("RGB")
      #   converted = 1
      #if im.size[0] >= im.size[1]:
      #   max = im.size[0]
      #   min = im.size[1]
      #   if px_size >= max:
      #     shrunk_im = im
      #     x, y = im.size
      #   else:
      #     x = px_size
      #     y = int((min * px_size)/max)
      #     shrunk_im = im.resize((x, y), Image.ANTIALIAS)
      #else:
      #   max = im.size[1]
      #   min = im.size[0]
      #   if px_size >= max:
      #     shrunk_im = im
      #     x, y = im.size
      #   else:
      #     x = int((min * px_size)/max)
      #     y = px_size
      #     shrunk_im = im.resize((x,y), Image.ANTIALIAS)
      #if converted  == 1:
      #  shrunk_im = shrunk_im.convert("P",dither=Image.NONE, palette=Image.ADAPTIVE)
      #  image_extension = 'png'
      ## save the image's thumbnail in the format image.thumbnail.192.23.jpg or image.thumbnail.60.26.png, where the number indicates the size
      #shrunk_im.save(image_location + image_name + '.thumbnail.%s.%s.%s' % (x, y, image_extension), quality=90)
    captionJS = caption.replace('"', "\'")
    captionJS = captionJS.replace("'", "\\'")
    d = { 'right':'floatRight', 'left':'floatLeft', '':'noFloat' }
    floatSide = d[alignment]

    # God damn, I am a perfectionist
    full_size_url = baseurl + "/" + urlpagename + "?action=" + action + "&do=view&target=" + full_image_name
    if caption:
      html.append('<div class="%s thumb" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s"/></a><div>%s</div></div>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, full_image_name, macro.request, thumb=True, size=px_size),caption))
    else:
      html.append('<div class="%s thumb" style="width: %spx;"><a style="color: black;" href="%s"><img src="%s"/></a></div>' % (floatSide, int(x)+2, full_size_url, Files.getAttachUrl(pagename, full_image_name, macro.request, thumb=True, size=px_size)))
    return ''.join(html)
