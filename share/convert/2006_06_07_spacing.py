import sys, cStringIO, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))])

from Sycamore import wikiutil, config, request, caching, wikidb
from Sycamore.Page import Page
from Sycamore import rebuildPageCaches

import re
#header: ^=+[^=]*=+
#br: \[\[[bB][rR]\]\]
#hr: ----+
#bullet: ^ *\*
#image: .*[[Image.*
#table: \|\|.*\|\|
ignore_expr = re.compile('^=+[^=]*=+|\[\[[bB][rR]\]\]|----+|.*\[\[Image.*|\|\|.*\|\|', re.IGNORECASE)
nextln_expr = re.compile('^ *\*|^=+[^=]*=+|----+|.*\[\[Image.*|\|\|.*\|\|', re.IGNORECASE)

def newline_sucker(line): #replace newlines with strings sometimes
    match = ignore_expr.search(line)
    if(match): return line
    else: return line.replace('\n', ' ')

def file_sucker(text): #diddle around with newlines in a file
    blank = [line.isspace() or line.startswith(" ") for line in text] # boolean array 'is this a blank line?'
    result = []
    for linenum in range(0,len(text)-1): #not a 'for line in text', we need lookahead
        if blank[linenum] or blank[linenum+1]:
            result.append(text[linenum]) #don't remove \n for blank lines or lines before blank lines
            continue
            
        keepline = nextln_expr.search(text[linenum+1])
        if keepline:
            result.append(text[linenum]) #don't remove \n if nextline satisfies criterion
        else:
            result.append(newline_sucker(text[linenum])) #otherwise replace \n with space
    result.append(text[-1]) #stick in the last line verbatim
    return ''.join(result)

req = request.RequestDummy()
plist = wikiutil.getPageList(req)
print "Converting pages for spacing consistency.."
print "-----------"
for pagename in plist:
  print "Updating %s" % pagename.encode('utf-8')
  req.cursor.execute("SELECT text from curPages where name=%(pagename)s", {'pagename':pagename.lower()})
  mtime = Page(pagename, req).mtime()
  text = req.cursor.fetchone()[0]
  lines = text.splitlines(True)
  fixed_text = file_sucker(lines)

  # replace the latest version of the page text
  req.cursor.execute("UPDATE curPages set text=%(fixed_text)s where name=%(pagename)s", {'pagename':pagename.lower(), 'fixed_text':fixed_text})
  req.cursor.execute("UPDATE allPages set text=%(fixed_text)s where name=%(pagename)s and editTime=%(mtime)s", {'pagename':pagename.lower(), 'fixed_text':fixed_text, 'mtime':mtime})
req.db_disconnect()
print "-----------"
print "Pages converted for spacing consistency!"

rebuildPageCaches.clearCaches(plist)
rebuildPageCaches.buildCaches(plist)
