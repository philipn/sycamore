"""
This script will nuke the provided wikis and all data associated with them.  Don't do this unless you really want to.
"""

import sys, time, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', 'share'))]),
import __init__
from Sycamore import config, request, user, wikiutil, caching
from Sycamore.Page import Page

############################################
# CHANGEME:
############################################
wikis_to_nuke = ['spamwiki']

if __name__ == '__main__':
    req = request.RequestDummy()
    cursor = req.cursor
    for wiki_name in wikis_to_nuke:
        # get the wiki id
        d = { 'wiki_name': wiki_name } 
        cursor.execute("SELECT id from wikis where name=%(wiki_name)s", d)
        wiki_id = cursor.fetchone()[0]
        d['wiki_id'] = wiki_id

        cursor.execute("DELETE from allPages where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from curPages where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from events where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from files where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from imageCaptions where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from imageInfo where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from links where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from mapCategoryDefinitions where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from mapPointCategories where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from mapPoints where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from metadata where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from oldFiles where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from oldImageInfo where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from oldMapPointCategories where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from oldMapPoints where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from pageAcls where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from pageDependencies where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from thumbnails where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from userFavorites where wiki_name=%(wiki_name)s", d, isWrite=True)
        cursor.execute("DELETE from userGroups where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from userGroupsIPs where wiki_id=%(wiki_id)s", d, isWrite=True)
        cursor.execute("DELETE from userWatchedWikis where wiki_name=%(wiki_name)s", d, isWrite=True)
        cursor.execute("DELETE from userWikiInfo where wiki_id=%(wiki_id)s", d, isWrite=True)

        cursor.execute("DELETE from wikis where id=%(wiki_id)s", d, isWrite=True)

        # nuke the memcache'd configuration
        req.mc.delete("settings:%s" % wikiutil.mc_quote(wiki_name), wiki_global=True)
        
        # clear the recent wikis display, because this wiki is history!
        req.mc.delete('recentwikis', wiki_global=True)
    
    req.db_disconnect()
