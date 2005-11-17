import sys, re, os
sys.path.extend(['/var/www/lib/python','/var/www/html/dwiki'])
from LocalWiki import wikiutil, config
from LocalWiki.logfile import editlog

editlog = open(config.data_dir + '/editlog', 'r')
editlist = editlog.readlines()
for line in editlist:
	robj = re.match('(?P<pagename>.+?)\t', line)
	if robj:
		pagename = robj.group('pagename')
		if os.path.exists(config.data_dir + '/pages/' + pagename):
			page_editlog = open(config.data_dir + '/pages/' + pagename + '/editlog', 'a')
			page_editlog.write(line)
			page_editlog.close()
