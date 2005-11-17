import sys
sys.path.extend(['/home/dwiki/lib/python','/home/dwiki/public_html/dwiki'])
from LocalWiki import wikiutil, config
import cPickle

def exe():
        pdfile= open(config.data_dir +'/pagedict.pickle' , 'r') # pickled pagedict
        pagedict = cPickle.load( pdfile)
        pdfile.close()
        print pagedict
exe()
