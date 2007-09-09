import sys, os, cStringIO
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])

from Sycamore import config, request, wikidb, wikiutil
from PIL import Image

#################################################
# This script will rebuild the imageInfo table.
#################################################
req = request.RequestDummy()

req.cursor.execute("SELECT files.name, files.attached_to_pagename, wikis.name from files, wikis where files.wiki_id=wikis.id")
files_list = req.cursor.fetchall()
for file_info in files_list:
    name, attached_to_pagename, wiki_name = file_info
    print name
    
    if wikiutil.isImage(name):
        d = {'filename': name, 'page_name': attached_to_pagename}
        req.switch_wiki(wiki_name)
        file_get = wikidb.getFile(req, d)
	if not file_get:  continue
        filecontent, last_modified = file_get

    
        file = cStringIO.StringIO(filecontent)
        img = Image.open(file)
        img_size = img.size
        file.close()
    
        d['x'] = img_size[0]
        d['y'] = img_size[1]
        d['wiki_name'] = wiki_name
    
        req.cursor.execute("UPDATE imageInfo set xsize=%(x)s, ysize=%(y)s where imageInfo.name=%(filename)s and imageInfo.attached_to_pagename=%(page_name)s and imageInfo.wiki_id=(SELECT id from wikis where name=%(wiki_name)s)", d, isWrite=True)
    

req.db_disconnect()

print "Done with imageInfo rebuilding."
