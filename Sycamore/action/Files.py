# -*- coding: iso-8859-1 -*- """
"""
    Sycamore - Files action

    This action lets a page have multiple attachment files.
    It writes to the images and oldImages tables.

    To insert an image into the page, use the [[Image]] macro.
    To insert a link to a general file, use [[File]].

    @copyright: 2001 by Ken Sugino (sugino@mediaone.net)
    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @copyright: 2005-2006 by Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

import os, mimetypes, time, urllib, string
from Sycamore import config, user, util, wikiutil, wikidb
from Sycamore.Page import Page
from Sycamore.util import SycamoreNoFooter 
from Sycamore.widget.infobar import InfoBar
import xml.dom.minidom

action_name = __name__.split('.')[-1]
htdocs_access = isinstance(config.attachments, type({}))

icon_dict = {
'.pdf': 'file-pdf.png',
'.ps': 'file-pdf.png',
'.jpe': 'file-image.png',
'.jpeg': 'file-image.png',
'.jpg': 'file-image.png',
'.png': 'file-image.png',
'.gif': 'file-image.png',
'.mpg': 'file-movie.png',
'.mpeg': 'file-movie.png',
'.avi': 'file-movie.png',
'.mov': 'file-movie.png',
'.moov': 'file-movie.png',
'.mp4': 'file-movie.png',
'.qt': 'file-movie.png',
'.rm': 'file-movie.png',
'.divx': 'file-movie.png',
'.asf': 'file-movie.png',
'.aac': 'file-sound.png',
'.aiff': 'file-sound.png',
'.aif': 'file-sound.png',
'.mp1': 'file-sound.png',
'.mp2': 'file-sound.png',
'.mp3': 'file-sound.png',
'.m4a': 'file-sound.png',
'.ogg': 'file-sound.png',
'.ram': 'file-sound.png',
'.wav': 'file-sound.png',
'.wma': 'file-sound.png',
'.py': 'file-script.png',
'.pl': 'file-script.png',
'.pm': 'file-script.png',
'.php': 'file-script.png',
'.sh': 'file-script.png',
'.rb': 'file-script.png',
'.tcl': 'file-script.png',
#'.patch': 'file-patch.png',
#'.diff': 'file-patch.png',
#'.js': 'file-patch.png',
'.txt': 'file-text.png',
'.css': 'file-text.png',
'.html': 'file-text.png',
'.htm': 'file-text.png',
'.js': 'file-text.png',
'.xml': 'file-text.png',
#'.zip': 'file-compressed.png',
#'.gz': 'file-compressed.png',
#'.bz2': 'file-compressed.png',
#'.bz': 'file-compressed.png',
#'.hqx': 'file-compressed.png',
#'.tbz': 'file-compressed.png',
#'.tbz2': 'file-compressed.png',
#'.tgz': 'file-compressed.png',
#'.sea': 'file-compressed.png',
#'.rar': 'file-compressed.png',
#'.sit': 'file-compressed.png',
#'.sitx': 'file-compressed.png',
'.doc': 'file-doc.png',
'.xls': 'file-xls.png',
'*': 'file-generic.png'
}


def get_icon(filename, request):
  file_extension = getExtension(request, '', filename)
  if file_extension.lower() in icon_dict:
    file_icon = request.theme.get_icon(icon_dict[file_extension.lower()])[1]
  else:
    file_icon = request.theme.get_icon(icon_dict['*'])[1]
  return file_icon


#############################################################################
### External interface - these are called from the core code
#############################################################################

def openImage(filecontent):
    """
    Return image size or throw exception if not an image.
    """
    from PIL import Image
    import cStringIO
    im = Image.open(cStringIO.StringIO(filecontent))
    return im
    

def getAttachUrl(pagename, filename, request, addts=0, escaped=0, deleted=0, version=None, thumb=False, size=0, ticket=None):
    """ Get URL that points to file `filename` of page `pagename`.

        If 'addts' is true, a timestamp with the file's modification time
        is added, so that browsers reload a changed file.
        NOTE:  FOR NOW we ignore addts..may add back if needed later.
    """
    pagename = Page(pagename, request).proper_name()
    if not deleted:
      if not thumb:
        url = "%s/%s?sendfile=true&amp;file=%s" % (wikiutil.baseScriptURL(), 
            wikiutil.quoteWikiname(pagename),
            urllib.quote(filename))
      else:
        if not size:
          url = "%s/%s?sendfile=true&amp;file=%s&amp;thumb=yes" % (wikiutil.baseScriptURL(), 
            wikiutil.quoteWikiname(pagename),
            urllib.quote(filename))
        else:
          url = "%s/%s?sendfile=true&amp;file=%s&amp;thumb=yes&amp;size=%s" % (wikiutil.baseScriptURL(), 
            wikiutil.quoteWikiname(pagename),
            urllib.quote(filename), size)
        if ticket:
           url = "%s&amp;ticket=%s&amp;size=%s" % (url, ticket,size)
    else:
      if version is None:
        url = "%s/%s?sendfile=true&amp;file=%s&amp;deleted=true" % (wikiutil.baseScriptURL(), 
            wikiutil.quoteWikiname(pagename),
            urllib.quote(filename))
      else:
        url = "%s/%s?sendfile=true&amp;file=%s&amp;deleted=true&amp;version=%s" % (wikiutil.baseScriptURL(), 
            wikiutil.quoteWikiname(pagename),
            urllib.quote(filename), repr(version))


    return url


def _revisions_footer(request,revisions, baseurl, urlpagename, action, filename):
    text = '<div><h4>File history</h4></div><ul>'

    for revision in revisions:
      if revision[1]:
        text += '<li>[<a href="%s/%s?action=%s&amp;do=restore&amp;target=%s&amp;uploaded_time=%s">revert</a>] <a href="%s/%s?action=%s&amp;do=view&amp;target=%s&amp;version=%s">%s</a> uploaded by %s.  %s deleted by %s.</li>' % (baseurl, urlpagename, action, filename, repr(revision[1]), baseurl, urlpagename, action, filename, repr(revision[1]), request.user.getFormattedDateTime(revision[1]), user.getUserLink(request, user.User(request, revision[2])), request.user.getFormattedDateTime(revision[3]), user.getUserLink(request, user.User(request, revision[4])))
      else:
        text += '<li>[<a href="%s/%s?action=%s&amp;do=restore&amp;target=%s&amp;uploaded_time=%s">revert</a>] <a href="%s/%s?action=%s&amp;do=view&amp;target=%s&amp;version=%s">%s</a> uploaded by unknown.  %s deleted by %s.</li>' % (baseurl, urlpagename, action, filename, repr(revision[1]), baseurl, urlpagename, action, filename, repr(revision[1]), filename, request.user.getFormattedDateTime(revision[3]), user.getUserLink(request, user.User(request, revision[4])))
    text += '</ul>'
    return text

def _action_footer(request, pagename, baseurl, urlpagename, action, filename):
   page = Page(pagename, request)
   if request.user.may.delete(page):
      urlfile = urllib.quote(filename)
      return '<div class="actionBoxes"><span><a href="%s/%s?action=%s&amp;rename=%s#uploadFileArea">replace file</a></span><span><a href="%s/%s?action=%s&amp;do=del&amp;target=%s">delete file</a></span></div>' % (baseurl, urlpagename, action, filename, baseurl, urlpagename, action, urlfile)
   return ''
     


#############################################################################
### Internal helpers
#############################################################################

def _isValidExtension(extension):
    if extension in config.valid_image_extensions:
      return True
    return False

def _has_deleted_files(pagename, request):
    request.cursor.execute("""
        SELECT oldFiles.name from oldFiles where
                    (oldFiles.name, oldFiles.attached_to_pagename) not in (SELECT files.name, files.attached_to_pagename from files) and oldFiles.attached_to_pagename=%(pagename)s""", {'pagename':pagename.lower()})

    result = request.cursor.fetchone()
    if result: return True
    else: return False
        

def has_file(request, pagename, filename):
  if get_filedict(request, pagename).has_key(filename):  return True 
  return False

 
def get_filedict(request, pagename, fresh=False, set=False):
  # returns a dict of filenames on the page {'filename': True/False ..}
  pagename = pagename.lower()
  files = None
  if not fresh:
    if request.req_cache['file_dict'].has_key(pagename):
      return request.req_cache['file_dict'][pagename]
    if config.memcache:
      files = request.mc.get('filedict:%s' % wikiutil.quoteFilename(pagename))
  if files is None:
    files = {}
    request.cursor.execute("SELECT name from files where attached_to_pagename=%(pagename)s order by name", {'pagename':pagename})
    result = request.cursor.fetchone()
    while result:
      files[result[0]] = True
      result = request.cursor.fetchone()
  if config.memcache:
    if not set:
      request.mc.add('filedict:%s' % wikiutil.quoteFilename(pagename), files)
    else:
      request.mc.set('filedict:%s' % wikiutil.quoteFilename(pagename), files)

  request.req_cache['file_dict'][pagename] = files
  return files


def get_filelist(request, pagename):
  return get_filedict(request, pagename).keys()


def _get_filelist(request, pagename):
    _ = request.getText
    
    str = []
    baseurl = request.getScriptname()
    action = action_name
    urlpagename = wikiutil.quoteWikiname(pagename)
    files = get_filelist(request, pagename)

    if files:
        str.append(_("<p>"
            "To refer to files on a page, use <strong><tt>[[Image(filename)]]</tt></strong> for images or "
            "<strong><tt>[[File(filename)]]</tt></strong> for general filenames "
            "where filename is one of the file names below.</p>"
        ))
        str.append('<div class="fileList"><ul class="wikipage">')

                
        for file in files:
            urlfile = urllib.quote(file)
            #base, ext = os.path.splitext(file)
            file_icon = get_icon(file, request)
            
            get_url = getAttachUrl(pagename, file, request, escaped=1)
            parmdict = {'baseurl': baseurl, 'urlpagename': urlpagename,
                        'urlfile': urlfile, 'action': action,
                        'get_url': get_url,
                        'file': file, 
                        'icon': file_icon,
                        'pagename': pagename}
            
            
            str.append(('<li class="wikipage"><img src="%(icon)s"/><a href="%(baseurl)s/%(urlpagename)s?action=%(action)s&amp;do=view&target=%(urlfile)s">%(file)s</a></li>') % parmdict)
        str.append("</ul></div>")
    else:
        str = ['%s<p>%s</p>' % (''.join(str), _("No files stored on %(pagename)s") % {'pagename': pagename})]
    
    if _has_deleted_files(pagename, request): str.append('<div class="actionBoxes"><span><a href="%s/%s?action=%s&amp;do=show_deleted">Page\'s deleted files</a></span></div>' % (baseurl, urlpagename, action))

    return ''.join(str)
        
    
def error_msg(pagename, request, msg):
    #Page(pagename).send_page(request, msg=msg)
    request.http_headers()
    wikiutil.simple_send_title(request, pagename, msg)
    send_uploadform(pagename, request)

#############################################################################
### Create parts of the Web interface
#############################################################################

def send_link_rel(request, pagename):
    attach_dir = ''
    if os.path.isdir(attach_dir):
        files = os.listdir(attach_dir)
        files.sort()
        for file in files:
            get_url = getAttachUrl(pagename, file, request, escaped=1)
            request.write('<link rel="Appendix" title="%s" href="%s">\n' % (
                wikiutil.escape(file), get_url))


def send_uploadform(pagename, request):
    """ Send the HTML code for the list of already stored attachments and
        the file upload form.
    """
    _ = request.getText
    
    page = Page(pagename, request)
    if not request.user.may.read(page):
        request.write('<p>%s</p>' % _('You are not allowed to view this page.'))
        return

    #request.write('<h2>' + _("Attached Images") + '</h2>')
    InfoBar(request, pagename).render()
    request.write('<div id="tabPage">')

    request.write(_get_filelist(request, pagename))

    if not request.user.may.edit(page):
        request.write('<p>%s</p>' % _('You are not allowed to attach a file to this page.'))
        return


    request.write('<h2 id="uploadFileArea">' + _("Upload a new file") + '</h2><p>' +
_("""If you upload a file with the same name an an existing file then your version will replace the old version.
If "Save as" is left blank, the original filename will be used (might be ugly) . You should give it a name!  Just name it whatever.jpg/png/gif (in "Save as").""") + '</p>')
    request.write("""
<form action="%(baseurl)s/%(pagename)s?action=%(action_name)s" method="POST" enctype="multipart/form-data">
<dl>
<dt>%(upload_label_file)s</dt>
<dd><input type="file" name="file" size="50"></dd>
<dt>%(upload_label_rename)s</dt>
<dd><input type="text" name="rename" size="50" value="%(rename)s"></dd>
</dl>
<p>
<input type="hidden" name="action" value="%(action_name)s">
<input type="hidden" name="do" value="upload">
<input type="submit" value="%(upload_button)s">&nbsp;&nbsp;<input type="button" onclick="opener.preview();window.close();" value="Close and Preview">
</p>
</form>
""" % {
    'action_name': action_name,
    'baseurl': request.getScriptname(),
    'pagename': wikiutil.quoteWikiname(pagename),
    'action_name': action_name,
    'upload_label_file': _('File to upload'),
    'upload_label_rename': _('Save as'),
    'rename': request.form.get('rename', [''])[0],
    'upload_button': _('Upload'),
})
    request.write('<h3>' + _("How do I do this?") + '</h3>' +
_("""<p>Once you've selected a file on your hard disk, use "Save as" to name it whateveryouwant.png/jpg/gif.  Then click "Upload" to upload the file to the page. To make an image appear on the page you need to edit the page and add the line <tt>[[Image(whatyounamedyourimage)]]</tt> where you want the image to appear.  For general files, add the line <tt>[[File(whatyounamedyourfile]]</tt> to make link to the file.  That's it!</p>"""))


#############################################################################
### Web interface for file upload, viewing and deletion
#############################################################################

def execute(pagename, request):
    """ Main dispatcher for the 'Files' action.
    """
    _ = request.getText

    msg = None
    page = Page(pagename, request)
    if action_name in config.excluded_actions:
        msg = _('File attachments are not allowed in this wiki!')
    elif not request.form.has_key('do'):
        upload_form(pagename, request)
    elif request.form['do'][0] == 'upload':
        if request.user.may.edit(page):
            do_upload(pagename, request)
        else:
            msg = _('You are not allowed to attach a file to this page.')
    elif request.form['do'][0] == 'del':
        if request.user.may.delete(page):
            del_file(pagename, request)
        else:
            msg = _('You are not allowed to delete files on this page.')
    elif request.form['do'][0] == 'restore':
        if request.user.may.edit(page):
            restore_file(pagename, request)
        else:
            msg = _('You are not allowed to restore files to this page.')

    elif request.form['do'][0] == 'show_deleted':
        show_deleted_files(pagename, request)
    elif request.form['do'][0] == 'get':
        if request.user.may.read(page):
            get_file(pagename, request)
        else:
            msg = _('You are not allowed to get files from this page.')
    elif request.form['do'][0] == 'view':
        if request.user.may.read(page):
            view_file(pagename, request)
        else:
            msg = _('You are not allowed to view files on this page.')
    else:
        msg = _('Unsupported upload action: %s') % (request.form['do'][0],)

    if msg:
        error_msg(pagename, request, msg)


def upload_form(pagename, request, msg=''):
    _ = request.getText

    request.http_headers()
    wikiutil.simple_send_title(request, pagename, msg=msg, strict_title='Files for "%s"' % pagename)
    request.write('<div id="content" class="content">')
    send_uploadform(pagename, request)
    request.write('</div></div>')
    wikiutil.send_after_content(request)
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)

def send_title(request, desc, pagename, msg, title=''):
    request.write(
        '<html><head>'
        '<link rel="stylesheet" type="text/css" charset="iso-8859-1" media="all" href="' +config.url_prefix + '/eggheadbeta/css/common.css">'
        '<link rel="stylesheet" type="text/css" charset="iso-8859-1" media="screen" href="' +config.url_prefix + '/eggheadbeta/css/screen.css">'
        '<link rel="stylesheet" type="text/css" charset="iso-8859-1" media="print" href="' +config.url_prefix + 'eggheadbeta/css/print.css">'
        '<meta name="robots" content="noindex,nofollow"/><title>%s</title></head><body><p><h3>&nbsp;%s</h3></p>' % (title, desc)
        )
    if msg :
      request.write('<div id="message"><p>%s</p></div>' % msg)

def allowedExtension(ext):
    if ext.lower() in config.allowed_extensions:
        return True
    return False

def allowedMime(ext):
    if not config.allow_all_mimetypes:
      mimetype = mimetypes.guess_type(ext)[0]
      allowed = config.allowed_mimetypes + [mimetypes.guess_type(e)[0] for e in config.allowed_extensions]
      if mimetype in allowed:
          return True
      return False
    else:
      return True

def _fixFilename(filename, request):
  # MSIE sends the entire path to us.  Mozilla doesn't.
  if request.http_user_agent.find("MSIE") != -1:
    # it's IE
    filename_split = filename.split("\\")
    filename = filename_split[-1]
  return filename

def getExtension(request, target, filename):
    def _extFromFileext(req, t, f):
        return os.path.splitext(f)[-1]

    def _extFromFormMime(req, t, f):
        if req.form.has_key('mime'):
            return mimetypes.guess_extension(request.form['mime'][0])

    def _extFromTarget(req, t, f):
        return os.path.splitext(t)[-1]

    extGuessers = (_extFromTarget, _extFromFileext, _extFromFormMime)

    for eg in extGuessers:
        ext = eg(request, target, filename)
        if ext:
            break
        
    if not ext:
        ext = ''

    return ext


def do_upload(pagename, request):
    import cStringIO
    from PIL import Image
    _ = request.getText
    msg = ''

    is_image = False

    # make filename
    filename = None
    if request.form.has_key('file__filename__'):
        filename = _fixFilename(request.form['file__filename__'], request)
    rename = None
    if request.form.has_key('rename'):
        rename = request.form['rename'][0].strip()

    # if we use twisted, "rename" field is NOT optional, because we
    # can't access the client filename
    if rename:
        target = rename
    elif filename:
        target = filename
    else:
        error_msg(pagename, request, _("Filename was not specified!"))
        return

    if string.find(filename, '<') != -1 or string.find(filename, '>') != -1 or string.find(filename, '&') != -1 or string.find(filename, '?') != -1 or string.find(filename, '"') != -1:
        error_msg(pagename, request, _("The characters '<', '>', '&', '\"', and '?' are not allowed in file names."))
        return

    # get file content
    filecontent = request.form['file'][0]
    
    if config.max_file_size and len(filecontent) > config.max_file_size * 1024:
        error_msg(pagename, request, _("Files must be %sKb or smaller." % config.max_file_size)) 
        return


    target = wikiutil.taintfilename(target)

    ext = getExtension(request, target, filename)

    target = os.path.splitext(target)[0] + ext

    if not allowedExtension(ext) and not allowedMime(ext):
        error_msg(pagename, request, _("The file extension %s is not allowed on this wiki." % ext))
        return

    if wikiutil.isImage(ext):
       # open the image
       try:
         im = openImage(filecontent)
       except IOError:
         error_msg(pagename, request, _('Your file ended with "%s" but doesn\'t seem to be an image or I don\'t know know to process it!' % ext))
         return

       is_image = True

       f2e = {'PNG': ['.png'], 'JPEG': ['.jpg', '.jpeg'], 'GIF': ['.gif']}
       imfe = f2e.get(im.format, '')[0]
   
       if ext.lower() not in imfe:
         msg += _("File extension %s did not match image format %s, changing extension to %s.<br/>" % (ext, im.format, imfe))
         ext = imfe

    # save file
    request.cursor.execute("SELECT name from files where attached_to_pagename=%(pagename)s and name=%(filename)s", {'pagename':pagename.lower(), 'filename':target})
    result = request.cursor.fetchone()

    uploaded_time = time.time()
    uploaded_by = request.user.id
    d = {'filename':target, 'filecontent':filecontent, 'uploaded_time':uploaded_time, 'uploaded_by':uploaded_by, 'pagename':pagename, 'uploaded_by_ip':request.remote_addr}
    
    if is_image:
      xsize, ysize = im.size
      d['xsize'] = xsize
      d['ysize'] = ysize

    wikidb.putFile(request, d)
    if request.user.valid:
      # upadate their file count
      request.cursor.execute("SELECT file_count from users where id=%(id)s", {'id':request.user.id})
      count = request.cursor.fetchone()[0]
      count += 1
      request.cursor.execute("UPDATE users set file_count=%(newcount)s where id=%(id)s", {'id':request.user.id, 'newcount':count})
    
    bytes = len(filecontent)
    msg += _("File '%(target)s'"
             " with %(bytes)d bytes saved.") % {
             'target': target, 'bytes': bytes}

    # return attachment list
    upload_form(pagename, request, msg)


def del_file(pagename, request):
    _ = request.getText

    filename = request.form['target'][0]
    d = {'filename': filename, 'pagename': pagename.lower(), 'deleted_time': time.time(), 'deleted_by':request.user.id, 'deleted_by_ip': request.remote_addr}
    wikidb.putFile(request, d, do_delete=True)
    upload_form(pagename, request, msg=_("File '%(filename)s' deleted.") % {'filename': filename})

def restore_file(pagename, request):
    _ = request.getText
    
    lower_pagename = pagename.lower()
    pagename_propercased = Page(pagename, request).proper_name()
    timenow = time.time()
    filename = request.form['target'][0]
    uploaded_time = request.form['uploaded_time'][0]

    request.cursor.execute("SELECT name, uploaded_time from files where name=%(filename)s and attached_to_pagename=%(pagename)s", {'filename':filename, 'pagename':pagename.lower()})
    is_in_files = request.cursor.fetchone()
    is_image = wikiutil.isImage(filename)
    if is_in_files:
        # this means the file wasn't most recently deleted but the user still would like to revert to this version of the file
        #backup the current version of the file
        dict = {'filename':filename, 'pagename':lower_pagename, 'timenow':timenow, 'userid':request.user.id, 'pagename_propercased':pagename_propercased, 'userip': request.remote_addr, 'uploaded_time': uploaded_time }
        request.cursor.execute("INSERT into oldFiles (name, attached_to_pagename, file, uploaded_by, uploaded_time, uploaded_by_ip, deleted_time, deleted_by, deleted_by_ip, attached_to_pagename_propercased) values (%(filename)s, %(pagename)s, (select file from files where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_by from files where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_time from files where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_by_ip from files where name=%(filename)s and attached_to_pagename=%(pagename)s), %(timenow)s, %(userid)s, %(userip)s, %(pagename_propercased)s)", dict, isWrite=True)
        request.cursor.execute("INSERT into oldImageInfo (name, attached_to_pagename, xsize, ysize, uploaded_time) values (%(filename)s, %(pagename)s, (select xsize from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s), (select ysize from imageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s), (select uploaded_time from files where name=%(filename)s and attached_to_pagename=%(pagename)s))", dict, isWrite=True)
        #revert by putting their version as the current version
        request.cursor.execute("UPDATE files set file=(select file from oldFiles where name=%(filename)s and attached_to_pagename=%(pagename)s and uploaded_time=%(uploaded_time)s), uploaded_by=%(userid)s, uploaded_by_ip=%(userip)s, uploaded_time=%(timenow)s where name=%(filename)s and attached_to_pagename=%(pagename)s", dict, isWrite=True)
        request.cursor.execute("UPDATE imageInfo set xsize=(select xsize from oldImageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s and uploaded_time=%(uploaded_time)s), ysize=(select ysize from oldImageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s and uploaded_time=%(uploaded_time)s)", dict, isWrite=True)

    else:
      dict = { 'filename':filename, 'pagename':lower_pagename, 'uploaded_time':uploaded_time, 'userid':request.user.id, 'userip':request.remote_addr, 'timenow':time.time(), 'pagename_propercased':pagename_propercased }
      request.cursor.execute("INSERT into files (name, attached_to_pagename, file, uploaded_by, uploaded_by_ip, uploaded_time, attached_to_pagename_propercased) values (%(filename)s, %(pagename)s, (select file from oldFiles where name=%(filename)s and attached_to_pagename=%(pagename)s and uploaded_time=%(uploaded_time)s), %(userid)s, %(userip)s, %(timenow)s, %(pagename_propercased)s)", dict, isWrite=True)
      if is_image:
        request.cursor.execute("INSERT into imageInfo (name, attached_to_pagename, xsize, ysize) values (%(filename)s, %(pagename)s, (select xsize from oldImageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s and uploaded_time=%(uploaded_time)s), (select ysize from oldImageInfo where name=%(filename)s and attached_to_pagename=%(pagename)s and uploaded_time=%(uploaded_time)s))", dict, isWrite=True)

    # delete the thumbnail -- this also has the effect of clearing the cache for the page/image
    wikidb.putFile(request, {'pagename': lower_pagename, 'filename': filename}, thumbnail=True, do_delete=True) 

    upload_form(pagename, request, msg=_("File '%s' version %s reactivated on page \"%s\".") % (filename, time.asctime(time.gmtime(float(uploaded_time))), pagename))


def getCaptionsHTML(attached_to_pagename, image_name, request):
   # outputs HTML of the caption for the image
   # note:  currently displays 'right' for only one caption
   # should be adapted to say "captions" when the image can be linked from other pages
   request.cursor.execute("SELECT caption from imageCaptions where attached_to_pagename=%(pagename)s and image_name=%(imagename)s", {'pagename':attached_to_pagename.lower(), 'imagename':image_name})
   results = request.cursor.fetchall()
   if results:
     request.cursor.execute("SELECT xsize from imageInfo where name=%(imagename)s and attached_to_pagename=%(pagename)s", {'imagename':image_name, 'pagename':attached_to_pagename.lower()})
     size_result = request.cursor.fetchone()
     if size_result: xsize = size_result[0]
   html = ''
   from Sycamore.formatter.text_html import Formatter
   html_formatter = Formatter(request)
   for result in results:
     # right now, there will only be one of these, but the plural is for later when images can be refered to by multiple pages
     html += '<div style="width: %spx;"><p class="bigCaption"><em>%s</em></p></div>' % (xsize, wikiutil.wikifyString(result[0], request, Page(attached_to_pagename, request), formatter=html_formatter))
   return html

def send_viewfile(pagename, request):
    _ = request.getText
    revisions = []
    lower_pagename = pagename.lower()

    if not request.form.get('target', [''])[0]:
        error = _("Filename of attachment not specified!")
        request.write(error)
        return

    else:
        filename = request.form['target'][0]
        if request.form.get('version', [''])[0]: version = float(request.form['version'][0])
        else: version = None

        is_image = wikiutil.isImage(filename)

        if version is None:
           # in some rare cases the images were not uploaded by a user, so let's check to see if there's information on the upload-er
           request.cursor.execute("SELECT name, uploaded_time, uploaded_by, length(file) from files where attached_to_pagename=%(pagename)s and name=%(filename)s", {'pagename':lower_pagename, 'filename':filename})
        else:
          request.cursor.execute("SELECT name, uploaded_time, uploaded_by, length(file) from files where attached_to_pagename=%(pagename)s and files.name=%(filename)s and files.uploaded_time=%(version_date)s", {'pagename':lower_pagename, 'filename':filename, 'version_date':version})
        result = request.cursor.fetchone()

        deleted_file = True
        request.cursor.execute("SELECT name from files where name=%(filename)s and attached_to_pagename=%(pagename)s",
           {'filename':filename, 'pagename':lower_pagename})  
        if request.cursor.fetchone():  deleted_file = False

        if is_image:
          request.write("<h4>Image '%s' of page %s:</h4>" % (filename, Page(pagename, request).link_to()))
        else:
          request.write("<h4>File '%s' of page %s:</h4>" % (filename, Page(pagename, request).link_to()))

        if version is None:
        # this means the image is 'active' and wasn't most recently deleted.
        # let's get some image history, if it's around
           request.cursor.execute("SELECT name, uploaded_time, uploaded_by, deleted_time, deleted_by from oldFiles where attached_to_pagename=%(pagename)s and oldFiles.name=%(filename)s order by uploaded_time desc;", {'pagename':lower_pagename, 'filename':filename})
           revisions_item = request.cursor.fetchone()
           while revisions_item:
             revisions.append((revisions_item[0], revisions_item[1], revisions_item[2], revisions_item[3], revisions_item[4]))
             revisions_item = request.cursor.fetchone()
           if deleted_file: revisions = revisions[1:] # skip own listing

        if not result:
           # let's see if the image was deleted, and if so we'll display it with a note about how it was removed.
           if version is None:
           # grab the most recent version of the image
             request.cursor.execute("SELECT name, uploaded_time, uploaded_by, length(file), deleted_time, deleted_by from oldFiles where attached_to_pagename=%(pagename)s and oldFiles.name=%(filename)s order by uploaded_time desc;", {'pagename':lower_pagename, 'filename':filename})
           else:
             # let's grab the proper version of the image
             request.cursor.execute("SELECT name, uploaded_time, uploaded_by, length(file), deleted_time, deleted_by from oldFiles where attached_to_pagename=%(pagename)s and name=%(filename)s and uploaded_time=%(version_date)s order by uploaded_time desc;", {'pagename':lower_pagename, 'filename':filename, 'version_date':version})
           latest_revision = request.cursor.fetchone()
           result = latest_revision
           if result:
              deleted_file = True
           else:
             error = _("File '%(filename)s' does not exist!") % {'filename': filename}
             request.write(error)
             return

        uploaded_time = ''
        uploaded_by = ''
        deleted_time = ''
        deleted_by = ''
        file_size = 0
        if result[1]: uploaded_time = result[1]
        if result[2]: 
            uploaded_by = user.User(request, result[2])
        if result[3]: file_size = result[3]
        if deleted_file:
          deleted_time = result[4]
          deleted_by = user.User(request, result[5])

        file_size = file_size/1024
    
    baseurl = request.getScriptname()
    action = action_name
    urlpagename = wikiutil.quoteWikiname(pagename)

    timestamp = ''
    if deleted_file:
      request.write('<p>This version of the file was <b>deleted</b> by %s on %s.</p>' % (user.getUserLink(request, deleted_by), request.user.getFormattedDateTime(deleted_time)))
      if is_image:
        request.write('<p class="imageDisplay"><img src="%s%s" alt="%s"></p>' % (
          getAttachUrl(pagename, filename, request, escaped=1, deleted=1, version=version), timestamp, wikiutil.escape(filename, 1)))
      else:
        request.write('<p class="downloadLink"><img src="%s" /><a href="%s">Download %s</a></p>' % (get_icon(filename, request), getAttachUrl(pagename, filename, request, escaped=1, deleted=1, version=version),  filename))
    else:
      if is_image:
        request.write('<p class="imageDisplay"><img src="%s%s" alt="%s"></p>' % (
          getAttachUrl(pagename, filename, request, escaped=1), timestamp, wikiutil.escape(filename, 1)))
        request.write(getCaptionsHTML(pagename, filename, request))
      else:
        request.write('<p class="downloadLink"><img src="%s" /><a href="%s">Download %s</a></p>' % (get_icon(filename, request), getAttachUrl(pagename, filename, request, escaped=1),  filename))
    if uploaded_by:
      request.write('<p>Uploaded by %s on %s.  File size: %sKB</p>' % (user.getUserLink(request, uploaded_by), request.user.getFormattedDateTime(uploaded_time), file_size))
    else:
      request.write('<p>Upload information unknown.  Please refer to the original page </p>')

    if deleted_file: request.write('<p><div class="actionBoxes"><span><a href="%s/%s?action=%s&amp;do=restore&amp;target=%s&amp;uploaded_time=%s">revert to this version of the file</a></span></div></p>' %(baseurl, urlpagename, action, filename, repr(uploaded_time)))

    if version is None and not deleted_file:
      request.write(_action_footer(request, pagename, baseurl, urlpagename, action, filename))

    if revisions:
      request.write(_revisions_footer(request, revisions, baseurl, urlpagename, action, filename))
    
    
def view_file(pagename, request):
    _ = request.getText

    filename = request.form['target'][0]

    # send header & title
    pagetitle = filename + " on " + config.sitename
    request.http_headers()
    wikiutil.simple_send_title(request, pagename, strict_title='Image \'%s\' on "%s"' % (filename, pagename))

    # send body
    request.write('<div id="content" class="content">')
    InfoBar(request, pagename).render()
    request.write('<div id="tabPage">')

    send_viewfile(pagename, request)
    request.write('</div></div>')
    wikiutil.send_after_content(request)
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)

def show_deleted_files(pagename, request):
    _ = request.getText

    # send header & title
    pagetitle = "Deleted files for \"%s\"" % (pagename)
    request.cursor.execute("""SELECT oldFiles.name, oldFiles.deleted_time, oldFiles.deleted_by, oldFiles.uploaded_time from 
    (
       SELECT name, max(deleted_time) as deleted_time from oldFiles where attached_to_pagename=%(pagename)s and (oldFiles.name, oldFiles.attached_to_pagename) not in (SELECT name, attached_to_pagename from files) group by name
    )
    as recentDeletedFiles, oldFiles where oldFiles.name=recentDeletedFiles.name and oldFiles.deleted_time=recentDeletedFiles.deleted_time"""
    , {'pagename':pagename.lower()})
    result = request.cursor.fetchall()
    text_list = ['<div class="fileList"><p><ul>']
    baseurl = request.getScriptname()
    action = action_name
    urlpagename = wikiutil.quoteWikiname(pagename)
    for item in result:
      text_list.append("<li><img src=\"%s\" /><a href=\"%s/%s?action=%s&amp;do=view&amp;target=%s\">%s</a> deleted by %s on %s. [<a href=\"%s/%s?action=%s&amp;do=restore&amp;target=%s&amp;uploaded_time=%s\">restore to page</a>] </li>" % ( get_icon(item[0], request), baseurl, urlpagename, action, item[0], item[0], user.getUserLink(request, user.User(request, item[2])), request.user.getFormattedDateTime(item[1]), baseurl, urlpagename, action, item[0], repr(item[3])))
    text_list.append('</p></div>')


    request.http_headers()
    wikiutil.simple_send_title(request, pagename, strict_title='Deleted files on "%s"' % pagename)

    # send body
    request.write('<div id="content" class="content">')
    InfoBar(request, pagename).render()
    request.write('<div id="tabPage">')

    request.write('<p>These files have been <b>deleted</b> from the original page, which means they can\'t be included in the wiki anymore and are possibly (in some cases) subject to permanent deletion:</p>')
    request.write(''.join(text_list))
    request.write('</div></div>')
    wikiutil.send_after_content(request)
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)
