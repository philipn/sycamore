# Part of the Local Wiki (http://daviswiki.org) Project
# -*- coding: iso-8859-1 -*-
from LocalWiki import config, wikiutil
import sys, re, os

Dependencies = []


def execute(macro, args):
    html = []
    pagename = wikiutil.quoteWikiname(macro.formatter.page.page_name)
    image_location = config.data_dir + '/pages/' + pagename + '/attachments/'

    if not args:
        return macro.formatter.rawHTML('<b>Please supply at least an image name, e.g. [[Thumb(image.jpg)]], where image.jpg is an image that\'s been uploaded to this page.</b>')

    import urllib
    # image.jpg, "caption, here, yes", 20, right --- in any order (filename first)
    # the number is the 'max' size (width or height) in pixels

    # parse the arguments
    re_obj = re.match('(?P<image_name>.*?)\.(?P<extension>jpg|jpeg|png|gif)(?P<the_rest>.*)', args, re.IGNORECASE) 
    image_extension = re_obj.group('extension')
    image_name = re_obj.group('image_name')

    full_image_name = image_name + "." + image_extension
    #is the original image even on the page?
    if not os.path.exists(image_location + full_image_name):
      #lets make a link telling them they can upload the image, just like the normal attachment
      linktext = 'Upload new attachment "%s"' % (full_image_name)
      return wikiutil.attach_link_tag(macro.request,
                '%s?action=AttachFile&amp;rename=%s%s' % (
                    pagename,
                    full_image_name,
                    ''),
                linktext)

    image_name = wikiutil.quoteWikiname(image_name)
    the_rest = re_obj.group('the_rest')
    re_obj = re.search('.+?"(?P<caption>.+)"', the_rest)
    if re_obj is not None:
        caption = re_obj.group('caption')
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

    # does the thumbnail already exist?
    import dircache
    attachment_list = dircache.listdir(image_location)
    has_thumb = False
    for attachment in attachment_list:
	match = re.match(image_name + '\.thumbnail\.(?P<thumb_size>(%s\.[0-9]+)|([0-9]+\.%s))\.%s' % (px_size, px_size, image_extension), attachment)
	if match:
	  has_thumb = True
	  x, y = (match.group('thumb_size')).split('.') 
	  break

    if not has_thumb:
      # do they have another thumbnail of the image, just a different size?
      for attachment in attachment_list:
        attachment_re = re.match('(?P<another_thumb>' + image_name + '\.thumbnail\.[0-9]+\.[0-9]+\.' + image_extension + ')', attachment)
        #there is already a thumbnail for this image, lets delete the old thumbnail and replace it with a new one
        # this only deletes one old thumbnail associated with one new thumbnail.
        if attachment_re is not None:
          filename = attachment_re.group('another_thumb')
          os.remove(image_location + filename)
          break
                
      # open the original image
      from PIL import Image

      im = Image.open(image_location + full_image_name)
      if im.size[0] >= im.size[1]:
         max = im.size[0]
         min = im.size[1]
         if px_size >= max:
           shrunk_im = im
	   x, y = im.size
         else:
	   x = px_size
	   y = int((min * px_size)/max)
           shrunk_im = im.resize((x, y), Image.ANTIALIAS)
      else:
         max = im.size[1]
         min = im.size[0]
         if px_size >= max:
           shrunk_im = im
	   x, y = im.size
         else:
	   x = int((min * px_size)/max)
	   y = px_size
           shrunk_im = im.resize((x,y), Image.ANTIALIAS)

      # save the image's thumbnail in the format image.thumbnail.192.23.jpg or image.thumbnail.60.26.png, where the number indicates the size
      shrunk_im.save(image_location + image_name + '.thumbnail.%s.%s.%s' % (x, y, image_extension), quality=90)
    captionJS = caption.replace('"', "\'")
    captionJS = captionJS.replace("'", "\\'")
    d = { 'right':'floatRight', 'left':'floatLeft', '':'noFloat' }
    floatSide = d[alignment]

    # God damn, I am a perfectionist
    if caption:
      html.append('<div class="%s thumb" style="width: %spx;"><img onclick="imgPopup(\'%s\', \'%s\');" src="%s"/><div>%s</div></div>' % (floatSide, int(x)+2, captionJS, config.attachments['url'] + '/' + pagename + '/attachments/' + full_image_name, config.attachments['url'] + '/' + pagename + '/attachments/' + image_name + '.thumbnail.%s.%s.%s' % (x, y, image_extension), caption))
    else:
      html.append('<div class="%s thumb" style="width: %spx; height: %spx;"><img onclick="imgPopup(\'%s\', \'%s\');" src="%s"/></div>' % (floatSide, int(x)+2, int(y)+2, captionJS, config.attachments['url'] + '/' + pagename + '/attachments/' + full_image_name, config.attachments['url'] + '/' + pagename + '/attachments/' + image_name + '.thumbnail.%s.%s.%s' % (x, y, image_extension)))	
    return ''.join(html)
