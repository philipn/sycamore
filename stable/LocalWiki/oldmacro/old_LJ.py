import re,time
import urllib

def execute(macro, args):
    if args:
	url = "http://www.livejournal.com/customview.cgi?username=%s&styleid=101" % (args)
    	x = urllib.urlopen(url)
	viewsource = x.read()
    else:
	viewsource = ""
    return macro.formatter.rawHTML(viewsource)
