import sys
sys.path.extend(['/var/www/lib','/var/www/html/installhtml/dwiki'])
from LocalWiki import wikiutil, config
from LocalWiki.Page import Page

import os, cPickle, time,shutil


def repair_index():
    """
    adds pages to the search index that weren't added with build_index (due to our host killing the process or something weird happening)
    """
    pages = wikiutil.getPageList(config.text_dir)
    stamp_time = str(time.time())
    os.mkdir(config.app_dir + '/search_db.' + stamp_time)
    os.mkdir(config.app_dir + '/title_search_db.' + stamp_time)
    for page in pages:
                #time.sleep(0.1)
                print page
                p = Page(page)
                os.spawnl(os.P_WAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index', wikiutil.quoteWikiname(page), wikiutil.quoteFilename(p.get_raw_body()), 'search_db.' + stamp_time, 'title_search_db.' + stamp_time)

repair_index()
