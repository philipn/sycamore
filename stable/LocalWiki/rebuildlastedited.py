import sys
sys.path.extend(['/var/www/lib/python','/var/www/html/dwiki'])
from LocalWiki import wikiutil, config
from LocalWiki.logfile import editlog

def exe():
	pagelist = wikiutil.getPageList(config.text_dir)
	for page in pagelist:
        	log = editlog.EditLog(config.data_dir + '/pages/' + wikiutil.quoteFilename(page) + '/editlog')
		try:
        		log.to_end()
		except StopIteration:
			continue
        	try:
            		line = log.previous()
        	except StopIteration:
            		# page has no history (system page)
            		continue
		while line.action != 'SAVE' or line.action != 'COMMENT_MACRO':
			try:
            			line = log.previous()
        		except StopIteration:
            			# page has no history (system page)
            			continue
			



		

exe()
