import sys
sys.path.extend(['/var/www/lib','/var/www/html/installhtml/dwiki'])
from LocalWiki import wikiutil, config
import cPickle, os

def exe():
    pagedict = {}
    pages = os.listdir(config.text_dir)
    result = []
    for file in pages:
        if file[0] in ['.', '#'] or file in ['CVS']: continue
        result.append(file)
    result = map(wikiutil.unquoteFilename, result)

    for page in result:
        pagedict[page.lower()] = page
    idfile = open(config.data_dir + '/pagedict.pickle', 'w')
    cPickle.dump(pagedict, idfile, 2)
    idfile.close()

exe()
