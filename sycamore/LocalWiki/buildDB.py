import sys
import time
sys.path.extend(['/Library/Webserver','/Library/Webserver/Documents/installhtml/dwiki'])
from LocalWiki import wikiutil, config
from LocalWiki.Page import Page
from LocalWiki.logfile import editlog

import os, cPickle, time,shutil
import MySQLdb


def build_mySQLdb():
    """
    woo!
    """
    db = MySQLdb.connect(host="localhost", user="root", db="wikitest")
    cursor = db.cursor()
    #pages = wikiutil.getPageList(config.text_dir)
    ourList = []
    #cursor.execute('start transaction')
    ed_time = ''
    """
    for page in pages:
	p = Page(page)
	# let's get the last edit time, or at least give it the old college try

	try:
		line = editlog.EditLog(wikiutil.getPagePath(p.page_name, 'last-edited', check_create=0)).next()
	except StopIteration:
		line = None
	if line:
		ed_time = line.ed_time
	# we don't have a last-edited file..uh..i guess we'll use the current time..?
	if not line:
		log = editlog.EditLog(config.data_dir + '/pages/' + wikiutil.quoteFilename(p.page_name) + '/editlog')     
        	try:
                	log.to_end()
        	except StopIteration:
                	line = None
        	try:
            		line = log.previous()
        	except StopIteration:
            	# page has no history (system page)
			line = None
		if line:
			ed_time = line.ed_time
		else:
			ed_time = str(time.time())
	
	time_struct = time.gmtime(float(ed_time))
	year = time_struct[0]
	month = time_struct[1]
	if month < 10:
		month = "0" + str(month)
	else:
		month = str(month)	
	day = time_struct[2]
	if day< 10:
		day= "0" + str(day)
	else:
		day= str(day)	
	hour = time_struct[3]	
	if hour< 10:
		hour= "0" + str(hour)
	else:
		hour= str(hour)	
	minute = time_struct[4]
	if minute< 10:
		minute= "0" + str(minute)
	else:
		minute= str(minute)	
	second = time_struct[5]
	if second< 10:
		second= "0" + str(second)
	else:
		second= str(second)	
	time_string = "%s-%s-%s %s:%s:%s" % (year, month, day, hour, minute, second)
	ourList.append((p.page_name, p.get_raw_body(), p.get_raw_body(), time_string, time_string))  

	
    cursor.executemany("INSERT into curPages values (%s, %s, %s, %s, %s)", ourList)
    cursor.execute('commit')
    """
    cursor.execute("INSERT into curPages values (%s, %s, %s, FROM_UNIXTIME(%s), FROM_UNIXTIME(%s))", ('hiyaaa', 'hi', 'hi', time.time(), time.time()))
    cursor.close()

build_mySQLdb()

