# -*- coding: utf-8 -*-
"""
  [[Image(filename, caption, size, alignment, thumb, noborder)]]
  
  filename : name of the file, an image.
    required. should provide error message if not present.
    must be the first element. all others can be in any order. 
  
  size : the size of the image. if size is supplied this implies it's a
    thumbnail. Can be either width or height depending on whichever is larger
    in source image. The size supplied is the desired scaled size.
  
  alignment : left/right. if it's a thumbnail then it gives it a usual
    float:left or float:right. if it's not a thumbnail then you need to wrap
    the image in a span that sends it left or right (i'm not sure it even
    needs to float..)
  
  thumb : this is just the string "thumb" or "thumbnail" that tells us it's
    a thumbnail. optional if size is supplied, if size not supplied defaults
    to (default size?). Should default size be a systemwide variable, or hard
    coded?
  
  noborder : just the string "noborder" to tell us, for non-thumbnails, to not
    use the tiny black image border. in the case it's a thumbnail, i suppose
    the best behavior would be to drop the caption and frame around the
    thumbnail (sort of consealing its thumbnail-ness)
    (We can have a caption w/o a border, as well)
"""

# Imports
import sys
import re
import os
import array
import time
import urllib

from Sycamore import config
from Sycamore import wikiutil
from Sycamore import wikidb
from Sycamore.action import Files

IMAGE_MACRO = re.compile(r'^(\s*(\[\[image((\(.*\))|())\]\])\s*)+$')
DIGITS = ['1','2','3','4','5','6','7','8','9']

Dependencies = []

default_px_size = 192

def recordCaption(pagename, linked_from_pagename, image_name, caption, request):
    """
    records the caption to the db so that we can easily look it up
    
    very simple -- no versioning or anything.
    just keeps it there for easy/quick reference
    (linked_from_pagename is for future use)
    """
    cursor = request.cursor
    mydict = {'pagename': pagename.lower(), 'image_name': image_name,
              'caption': caption, 'linked_from_pagename': linked_from_pagename,
              'wiki_id': request.config.wiki_id}
    cursor.execute("""SELECT image_name
                      FROM imageCaptions
                      WHERE attached_to_pagename=%(pagename)s and
                            image_name=%(image_name)s and
                            linked_from_pagename=%(linked_from_pagename)s and
                            wiki_id=%(wiki_id)s""", mydict)
    result = cursor.fetchone()
    if result:
        cursor.execute("""
            UPDATE imageCaptions
            SET caption=%(caption)s
            WHERE attached_to_pagename=%(pagename)s and
                  image_name=%(image_name)s and
                  linked_from_pagename=%(linked_from_pagename)s and
                  wiki_id=%(wiki_id)s""", mydict)
    else:
        cursor.execute("""INSERT INTO imageCaptions
                          (attached_to_pagename, image_name, caption,
                           linked_from_pagename, wiki_id)
                          values (%(pagename)s, %(image_name)s, %(caption)s,
                                  %(linked_from_pagename)s, %(wiki_id)s)""",
                       mydict)

def deleteCaption(pagename, linked_from_pagename, image_name, request):
    request.cursor.execute("""
        DELETE FROM imageCaptions
        WHERE attached_to_pagename=%(pagename)s and
              image_name=%(image_name)s and
              linked_from_pagename=%(linked_from_pagename)s and
              wiki_id=%(wiki_id)s""",
        {'pagename':pagename.lower(), 'image_name':image_name,
         'linked_from_pagename':linked_from_pagename,
         'wiki_id':request.config.wiki_id})

def getImageSize(pagename, image_name, request):
    """
    gets the size of an image (not a thumbnail) in the DB
    """
    request.cursor.execute("""SELECT xsize, ysize
                              FROM imageInfo
                              WHERE attached_to_pagename=%(pagename)s and
                                    name=%(image_name)s and
                                    wiki_id=%(wiki_id)s""",
                           {'pagename':pagename.lower(),
                            'image_name':image_name,
                            'wiki_id':request.config.wiki_id})
    result = request.cursor.fetchone()
    if result and result[0] and result[1]:
        return (result[0], result[1])
    return (0, 0)

def setImageSize(pagename, image_name, request):
    """
    Sets the image size in the db.
    We only need this if the image's size isn't set yet.
    """
    # has side-effect we want :p
    Files.getCaptionsHTML(pagename, image_name, request) 

def touchCaption(pagename, linked_from_pagename, image_name, caption, request):
    stale = True
    db_caption = ''
    cursor = request.cursor
    cursor.execute("""SELECT caption
                      FROM imageCaptions
                      WHERE attached_to_pagename=%(pagename)s and
                            linked_from_pagename=%(linked_from_pagename)s and
                            image_name=%(image_name)s and
                            wiki_id=%(wiki_id)s""",
                   {'pagename':pagename.lower(),
                    'linked_from_pagename':linked_from_pagename,
                    'image_name':image_name,
                    'wiki_id':request.config.wiki_id})
    result = cursor.fetchone()
    if result:
        db_caption = result[0] 
    if caption != db_caption: 
        recordCaption(pagename, linked_from_pagename, image_name, caption,
                      request)
    if not caption:
        deleteCaption(pagename, linked_from_pagename, image_name, request)

def touchThumbnail(request, pagename, image_name, maxsize, formatter,
                   fresh=True):
    # we test formatter.name because we use isPreview() to force some
    # things to be ignored on the second-formatting phase with the
    # python formatter.
    # in this case, we want to render a temporary thumbnail when we're in an
    # actual preview or viewing an old version of a page, not when we're doing
    # the formatting phase of a normal page save
    ticket = None
    temporary = ((formatter.isPreview() and formatter.name != 'text_python') or
                 formatter.page.prev_date)
    if temporary:
        ticket = _createTicket()
    cursor = request.cursor
    # first we see if the thumbnail is there with the proper size
    cursor.execute("""SELECT xsize, ysize
                      FROM thumbnails
                      WHERE name=%(image_name)s and
                            attached_to_pagename=%(pagename)s and
                            wiki_id=%(wiki_id)s""",
                   {'image_name':image_name, 'pagename':pagename.lower(),
                    'wiki_id':request.config.wiki_id})
    result = cursor.fetchone()
    if result:
        if result[0] and result[1]:
            x = result[0]
            y = result[1]
            if max(x, y) == maxsize:
                # this means the thumbnail is the right size
                return ((x, y), None)
    # we need to generate a new thumbnail of the right size
    return (generateThumbnail(request, pagename, image_name, maxsize,
                              fresh=fresh, temporary=temporary),
            ticket)


def sharpen_thumbnail(im):
   """
   Does a simple sharpen filter on the image.

   We do this because when an image is resampled it loses a lot of its
   crispness.
   """
   from PIL import ImageEnhance
   return ImageEnhance.Sharpness(im).enhance(1.5)

def generateThumbnail(request, pagename, image_name, maxsize, temporary=False,
                      ticket=None, return_image=False, fresh=False):
    cursor = request.cursor 
    from PIL import Image
    import cStringIO
    dict = {'filename':image_name, 'page_name':pagename}

    open_imagefile = cStringIO.StringIO(wikidb.getFile(request, dict,
                                                       fresh=fresh)[0])
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
            shrunk_im = sharpen_thumbnail(shrunk_im)
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
            shrunk_im = sharpen_thumbnail(shrunk_im)

    if converted == 1:
        shrunk_im = shrunk_im.convert("P", dither=Image.NONE,
                                      palette=Image.ADAPTIVE)

    import mimetypes
    type = mimetypes.guess_type(image_name)[0][6:]
    save_imagefile = cStringIO.StringIO()
    try:
        shrunk_im.save(save_imagefile, type, quality=90)
    except IOError:
        request.write('<em style="background-color: #ffffaa; padding: 2px;">'
                      'There was a problem with image %s.  '
                      'It probably has the wrong file extension.</em>' %
                      image_name)
    image_value = save_imagefile.getvalue()
    if return_image:
        # one-time generation for certain things like preview.
        # just return the image string
        return image_value
    dict = {'x':x, 'y':y, 'filecontent':image_value,
            'uploaded_time':time.time(), 'filename':image_name,
            'pagename':pagename}
    wikidb.putFile(request, dict, thumbnail=True, temporary=temporary,
                   ticket=ticket)

    save_imagefile.close()
    open_imagefile.close()
    
    return x, y

def getArguments(args):
    """
    This gets the arguments given to the image macro.

    This function is gross and should be redone by a regular expression,
    but only if it's somehow less gross.
    """
    #filename stuff
    split_args = args.split(',')
    f_end_loc = len(split_args[0])

    caption = ''
    px_size = 0
    alignment = ''
    thumbnail = False
    border = True

    # mark the beginning of the non-filename arguments
    # we use this to figure out what the image name is if there are commas
    # in the image name
    start_other_args_loc = len(args)

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
        # mark the start of the caption so that we can use it to grab the
        # image name if we need to
        start_other_args_loc = min(start_other_args_loc, q_start-1)
    else:
      q_start = 0

    # let's get the arguments without the caption or filename
    if caption:
        simplier_args = args[f_end_loc+1:q_start] + args[q_end+1:]
        # now our split will work to actually split properly
        list_args = simplier_args.split(',')
    else:
        list_args = args.split(',')[1:]

    arg_loc = len(args.split(',')[0])
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
        elif (clean_arg and
              (clean_arg[0] in DIGITS)):
            px_size = int(arg) 
        else:
            # keep track of how far we've gone
            arg_loc += len(arg) + 1
            continue

        # keep track of how far we've gone
        start_other_args_loc = min(start_other_args_loc, arg_loc)
        arg_loc += len(arg) + 1
	  
    # image name is the distance from the start of the string to the
    # first 'real' non-filename argument
    image_name = args[:start_other_args_loc].strip()
    # there may be leftover commas
    end_char = image_name[-1]
    while end_char == ',':
        image_name = image_name[:-1]
        end_char = image_name[-1]

    return (image_name, caption.strip(), thumbnail, px_size, alignment, border)

def line_has_just_macro(macro, args, formatter):
    line = macro.parser.lines[macro.parser.lineno-1].lower().strip()
    if IMAGE_MACRO.match(line):
        return True
    return False

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    if line_has_just_macro(macro, args, formatter):
      macro.parser.inhibit_br = 2

    macro_text = ''

    baseurl = macro.request.getScriptname()
    action = 'Files' # name of the action that does the file stuff
    html = []
    ticketString = None # for temporary thumbnail generation
    pagename = formatter.page.page_name
    urlpagename = wikiutil.quoteWikiname(formatter.page.proper_name())

    if not args:
        macro_text += formatter.rawHTML(
            '<b>Please supply at least an image name, e.g. '
            '[[Image(image.jpg)]], where image.jpg is an image that\'s been '
            'uploaded to this page.</b>')
	return macro_text

    # image.jpg, "caption, here, yes", 20, right --- in any order
    # (filename first)
    # the number is the 'max' size (width or height) in pixels

    # parse the arguments
    try:
        (image_name, caption, thumbnail, px_size, alignment,
         border) = getArguments(args)
    except:
        macro_text += formatter.rawHTML('[[Image(%s)]]' % wikiutil.escape(args))
        return macro_text

    if not wikiutil.isImage(image_name):
        macro_text += "%s does not seem to be an image file." % image_name
        return macro_text

    url_image_name = urllib.quote(image_name.encode(config.charset))

    if (macro.formatter.processed_thumbnails.has_key(
            (pagename, image_name)) and
        (thumbnail or caption)):
        macro_text += ('<em style="background-color: #ffffaa; padding: 2px;">'
                       'A thumbnail or caption may be displayed only once per '
                       'image.</em>')
        return macro_text

    macro.formatter.processed_thumbnails[(pagename, image_name)] = True
    
    #is the original image even on the page?
    macro.request.cursor.execute("""SELECT name
                                    FROM files
                                    WHERE name=%(image_name)s and
                                    attached_to_pagename=%(pagename)s and
                                    wiki_id=%(wiki_id)s""",
                                 {'image_name':image_name,
                                  'pagename':pagename.lower(),
                                  'wiki_id':macro.request.config.wiki_id})
    result = macro.request.cursor.fetchone()
    image_exists = result

    if not image_exists:
        # lets make a link telling them they can upload the image,
        # just like the normal attachment
        linktext = 'Upload new image "%s"' % (image_name)
        macro_text += wikiutil.attach_link_tag(macro.request,
                  '%s?action=Files&amp;rename=%s#uploadFileArea' % (
                      wikiutil.quoteWikiname(formatter.page.proper_name()),
                      url_image_name),
                  linktext)
        return macro_text

    full_size_url = (baseurl + "/" + urlpagename + "?action=" + action +
                     "&amp;do=view&amp;target=" + url_image_name)
    # put the caption in the db if it's new and if we're not in preview mode
    if not formatter.isPreview():
        touchCaption(pagename, pagename, image_name, caption, macro.request)
    if caption:
        # parse the caption string
        caption = wikiutil.stripOuterParagraph(wikiutil.wikifyString(
            caption, formatter.request, formatter.page, formatter=formatter))

    if thumbnail:
        # let's generated the thumbnail or get the dimensions if it's
        # already been generated
        if not px_size:
            px_size = default_px_size
        (x, y), ticketString = touchThumbnail(macro.request, pagename,
                                              image_name, px_size, formatter)

        d = {'right':'floatRight', 'left':'floatLeft', '':'noFloat'}
        floatSide = d[alignment]
        if caption and border:
            html.append('<span class="%s thumb" style="width: %spx;">'
                        '<a style="color: black;" href="%s">'
                        '<img src="%s" alt="%s" style="display:block;"/></a>'
                        '<span>%s</span>'
                        '</span>' %
                        (floatSide, int(x)+2, full_size_url,
                         Files.getAttachUrl(pagename, image_name,
                                            macro.request, thumb=True,
                                            size=px_size, ticket=ticketString),
                         image_name, caption))
        elif border:
            html.append('<span class="%s thumb" style="width: %spx;">'
                        '<a style="color: black;" href="%s">'
                        '<img src="%s" alt="%s" style="display:block;"/></a>'
                        '</span>' %
                        (floatSide, int(x)+2, full_size_url,
                         Files.getAttachUrl(pagename, image_name,
                                            macro.request, thumb=True,
                                            size=px_size, ticket=ticketString),
                         image_name))
        elif caption and not border:
            html.append('<span class="%s thumb noborder" style="width: %spx;">'
                        '<a style="color: black;" href="%s">'
                        '<img src="%s" alt="%s" style="display:block;"/></a>'
                        '<span>%s</span></span>' %
                        (floatSide, int(x)+2, full_size_url,
                         Files.getAttachUrl(pagename, image_name,
                                            macro.request, thumb=True,
                                            size=px_size, ticket=ticketString),
                         image_name, caption))
        else:
            html.append('<span class="%s thumb noborder" style="width: %spx;">'
                        '<a style="color: black;" href="%s">'
                        '<img src="%s" alt="%s" style="display:block;"/></a>'
                        '</span>' %
                        (floatSide, int(x)+2, full_size_url,
                         Files.getAttachUrl(pagename, image_name,
                                            macro.request, thumb=True,
                                            size=px_size, ticket=ticketString),
                         image_name))
    else:
        x, y = getImageSize(pagename, image_name, macro.request)

        if not x and not y:
            # image has no size..something went amuck
            setImageSize(pagename, image_name, macro.request)
            x, y = getImageSize(pagename, image_name, macro.request)

        if not border and not caption:
            img_string = ('<a href="%s">'
                          '<img class="borderless" src="%s" alt="%s"/></a>' %
                          (full_size_url,
                           Files.getAttachUrl(pagename, image_name,
                                              macro.request,
                                              ticket=ticketString),
                           image_name))
        elif border and not caption:
            img_string = ('<a href="%s">'
                          '<img class="border" src="%s" alt="%s"/></a>' %
                          (full_size_url,
                           Files.getAttachUrl(pagename, image_name,
                                              macro.request,
                                              ticket=ticketString),
                           image_name))
        elif border and caption:
            img_string = ('<a href="%s">'
                          '<img class="border" src="%s" alt="%s"/></a>'
                          '<div style="width: %spx;">'
                          '<p class="normalCaption">%s</p></div>' %
                          (full_size_url,
                           Files.getAttachUrl(pagename, image_name,
                                              macro.request,
                                              ticket=ticketString),
                           image_name, x, caption))
        elif not border and caption:
            img_string = ('<a href="%s">'
                          '<img class="borderless" src="%s" alt="%s"/></a>'
                          '<div style="width: %spx;">'
                          '<p class="normalCaption">%s</p></div>' %
                          (full_size_url,
                           Files.getAttachUrl(pagename, image_name,
                                              macro.request,
                                              ticket=ticketString),
                           image_name, x, caption))

        if alignment == 'right':
            img_string = '<span class="floatRight">' + img_string + '</span>'
        elif alignment == 'left':
            img_string = '<span class="floatLeft">' + img_string + '</span>'

        html.append(img_string)
      
    macro_text += ''.join(html)
    return macro_text

def _createTicket(tm = None):
    """
    Create a ticket using a site-specific secret (the config)
    """
    import hashlib, types
    if tm:
        tm = int(tm) 
    else:
        tm = int(time.time())
    ticket_hex = "%010x" % tm
    digest = hashlib.new('sha1')
    digest.update(ticket_hex)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return str(tm) + '.' + digest.hexdigest()

def checkTicket(ticket):
    """
    Check validity of a previously created ticket
    """
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return (ticket == ourticket) and ((time.time()-60) < int(timestamp))
