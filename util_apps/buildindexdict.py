import sys
sys.path.extend(['/var/www/lib/python_dev','/var/www/html/dwiki_dev'])
from LocalWiki import wikiutil, config
import cPickle

#this is for converting from the old system to the new system

def exe():
	indexdict = {}
	idfile_old = open(config.app_dir + '/index_id_file', 'r')
	name = idfile_old.readline()

	while (name):
		id = idfile_old.readline()	
		indexdict[name] = id
		name = idfile_old.readline()	
		

        idfile_new = open(config.app_dir +'/index_id.pickle' , 'w') # pickled pagedict
        cPickle.dump(indexdict, idfile_new, 2)
        idfile_new.close()

exe()
