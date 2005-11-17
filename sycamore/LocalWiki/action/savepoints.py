# Imports
import time,string
import os
import xml.dom.minidom
from LocalWiki import config, user, util, wikiutil
from LocalWiki.logfile import editlog, eventlog
from LocalWiki.PageEditor import PageEditor

def clean(text):
	text=text.replace('\x85','&#8230;') # elipsis
	text=text.replace('\x91','&#8216;') # opening single quote
	text=text.replace('\x92','&#8217;') # closing single quote
	text=text.replace('\x93','&#8220;') # opening double quote
	text=text.replace('\x94','&#8221;') # closing double quote
	text=text.replace('\x96','&#8211;') # en-dash
	text=text.replace('\x97','&#8212;') # em-dash
	return text

def execute(pagename, request):
    actname = __name__.split('.')[-1]

    request.http_headers()

    if not request.form.has_key('name'):
      request.write('Error: no name');
      raise util.LocalWikiNoFooter
    if not request.form.has_key('xml'):
      request.write('Error: no xml')
      raise util.LocalWikiNoFooter
    findName = request.form.get("name")[0]
    
    # be extra paranoid
    if actname in config.excluded_actions or \
        not request.user.may.edit(pagename):
            request.write('Error: you cannot edit this page')
            raise util.LocalWikiNoFooter
    os.system('cp %s/points.xml "%s/map_backup/points.xml.%s.%s"' % (config.web_root + config.web_dir, config.app_dir, time.strftime("%Y%m%d%H%M%S"), request.user.name))
    dom = xml.dom.minidom.parse(config.web_root + config.web_dir + "/points.xml")
    pages = dom.getElementsByTagName("page")
    root = dom.getElementsByTagName("pages")[0]
    maxId = 0
    for p in pages:
      curId = int(p.getAttribute("id"))
      if curId > maxId:
        maxId = curId
      name = p.getAttribute("name")
      if name == findName:
        root.removeChild(p)
                    
    dom2 = xml.dom.minidom.parseString(request.form.get("xml")[0])
    pages = dom2.getElementsByTagName("page")
    for p in pages:
      strId = p.getAttribute("id")
      if not strId:
        maxId = maxId + 1
        strId = str(maxId)
        p.setAttribute("id", strId)
      root.appendChild(p)

    the_xml = dom.toxml()
    xmlfile = open(config.web_root + config.web_dir + "/points.xml", "w")
    xmlfile.write(the_xml)
    xmlfile.close()
    request.write('Your changes have been saved.')
    log = editlog.EditLog()
    log.add(request, findName, None, os.path.getmtime(config.web_root + config.web_dir + "/points.xml"),
    ('Map location(s) modified'), 'MAPCHANGE')
    raise util.LocalWikiNoFooter
