import sys
sys.path.extend(['/home/dwiki/lib/python','/home/dwiki/public_html/dwiki'])
from LocalWiki import wikiutil, config
import cPickle

def exe():
        pagelist = wikiutil.getPageList(config.text_dir)
        pagedict = dict ([(x.lower(), x) for x in pagelist]) # we should only run this infrequently
        pdfile= open(config.data_dir +'/pagedict.pickle' , 'w') # pickled pagedict
        cPickle.dump(pagedict, pdfile, 2)
        pdfile.close()

def append():
        pdfile= open(config.data_dir +'/pagedict.pickle' , 'r') # pickled pagedict
        pagedict =  cPickle.load(pdfile)
        pdfile.close()

        pdfile= open(config.data_dir +'/pagedict.pickle' , 'w') # pickled pagedict
        pagedict['boobies1'] = 'Boobies'
        test = open("/home/dwiki/test.pickle","w")
        cPickle.dump(pagedict, pdfile, 2)
        pdfile.close()

        
append()
