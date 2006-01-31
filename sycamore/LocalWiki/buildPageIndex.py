import sys
sys.path.extend(['/usr/local/lib/python2.4/site-packages','/var/www/installhtml/dwiki'])
from LocalWiki import wikiutil, config
from LocalWiki.Page import Page

import os, cPickle, time, shutil


def repair_index():
    """
    Rebuilds the search index
    """
    db = wikidb.connect()
    cursor = db.cursor()
    req = request.RequestCGI(db)
    req.redirect(cStringIO.StringIO())

    pages = wikiutil.getPageList()
    stamp_time = str(time.time())
    os.mkdir(config.app_dir + '/search_db.' + stamp_time)
    os.mkdir(config.app_dir + '/title_search_db.' + stamp_time)
    for page in pages:
                #time.sleep(0.1)
                print page
                p = Page(page, cursor)
                os.spawnl(os.P_WAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index', wikiutil.quoteWikiname(page), wikiutil.quoteWikiname(p.get_raw_body()), 'search_db.' + stamp_time, 'title_search_db.' + stamp_time)
    if os.path.exists(config.app_dir + '/search_db'): shutil.rmtree(config.app_dir + '/search_db')
    shutil.move(config.app_dir + '/search_db.' + stamp_time, config.app_dir + '/search_db')
    if os.path.exists(config.app_dir + '/title_search_db'): shutil.rmtree(config.app_dir + '/title_search_db')
    shutil.move(config.app_dir + '/title_search_db.' + stamp_time, config.app_dir + '/title_search_db')
    cursor.close()
    db.close()
    req.redirect()

repair_index()
