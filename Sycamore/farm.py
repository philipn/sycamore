# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Wiki farm support functions

    @copyright: 2005 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""
# Imports
import os, sys
from copy import copy
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', 'share'))]),
import __init__
from Sycamore.wikiutil import quoteFilename, mc_quote
from Sycamore import config, buildDB, wikiutil, search, wikiacl, request, maintenance
from Sycamore.Page import Page

WIKINAME_CHARS = '0123456789abcdefghijklmnopqrstuvwxyz-'
WIKINAME_MAX_LENGTH = 40

def isValidWikiName(wikiname):
   import re
   return  (len(wikiname) < WIKINAME_MAX_LENGTH and not re.search('[^%s]' % WIKINAME_CHARS, wikiname))

def get_name_from_domain(domain, request):
    if request.req_cache['wiki_domains'].has_key(domain):
         return request.req_cache['wiki_domains'][domain]  
    else:
         wiki_name = None
         if config.memcache:
             wiki_name = request.mc.get('wiki_domains:%s' % domain, wiki_global=True)
         if wiki_name is None:
             request.cursor.execute("SELECT name from wikis where domain=%(domain)s", {'domain': domain})
             result = request.cursor.fetchone()
             if result and result[0]:
                 wiki_name = result[0]

         return wiki_name
            

def create_config(wikiname, request):
    config_dict = config.reduce_to_local_config(config.CONFIG_VARS)
    config_dict['wiki_id'] = None
    config_dict['wiki_name'] = wikiname
    config_dict['active'] = True
    site_conf = config.Config(wikiname, request)
    site_conf.set_config(wikiname, config_dict, request)

def add_wiki_to_watch(wikiname, request):
    watched_wiki_list = copy(request.user.getWatchedWikis())
    if wikiname not in watched_wiki_list:
         watched_wiki_list[wikiname] = None
    request.user.setWatchedWikis(watched_wiki_list)

def rem_wiki_from_watch(wikiname, request):
    watched_wiki_list = copy(request.user.getWatchedWikis())
    del watched_wiki_list[wikiname]
    request.user.setWatchedWikis(watched_wiki_list)

def build_search_index(request):
    pages = wikiutil.getPageList(request, objects=True)
    for page in pages:
        search.add_to_index(page)

def setup_admin(adminname, request):
    group = wikiacl.Group("Admin", request, fresh=True)
    groupdict = {adminname.lower(): None}
    group.update(groupdict)
    group.save()

def build_page_caches(request):
    plist = wikiutil.getPageList(request)
    maintenance.buildCaches(request.config.wiki_name, plist, doprint=False)

def clear_page_caches(request):
    plist = wikiutil.getPageList(request)
    maintenance.clearCaches(request.config.wiki_name, plist, doprint=False)

def create_wiki(wikiname, adminname, request):
    wikiname = wikiname.lower()
    is_in_farm = wikiutil.isInFarm(wikiname, request)
    is_valid_name = isValidWikiName(wikiname)
    if is_valid_name and not is_in_farm:
        old_wiki = request.config.wiki_name
        wikiname = wikiname.lower()
        create_config(wikiname, request) 

        request.switch_wiki(wikiname)
        buildDB.insert_pages(request)
        setup_admin(adminname, request)
        clear_page_caches(request)
        build_search_index(request)
        request.switch_wiki(old_wiki)
        return None

    if is_in_farm:
        return """Wiki creation failed because the wiki "%s" already exists!""" % wikiname
    if not is_valid_name:
        return """Wiki creation failed because the wiki name "%s" is invalid.  You may only use the numbers 0-9, the letters a-z, and the dash "-" in a wiki name.""" % wikiname

def link_to_wiki(wikiname, formatter, no_icon=False):
    return formatter.interwikilink('%s:%s' % (wikiname, 'Front Page'), wikiname, no_icon=no_icon)

def link_to_page(wikiname, pagename, formatter, no_icon=True, force_farm=False, text=''):
    if not text: text = pagename
    return formatter.interwikilink('%s:%s' % (wikiname, pagename), text, no_icon=no_icon, force_farm=force_farm)

def getWikiURL(wikiname, request):
    """
    Get the url of the wiki in the farm.
    """
    wiki_config = config.Config(wikiname, request)     
    if wiki_config.domain and wiki_config.domain != config.wiki_base_domain:
        return "http://%s/" % wiki_config.domain
    else:
        if config.wiki_farm_subdomains:
            if wiki_config.wiki_id != 1:
                return "http://%s.%s/" % (wikiname, config.wiki_base_domain)
            else:
                return "http://%s/" % config.wiki_base_domain
        elif config.wiki_farm_dir:
            if wiki_config.wiki_id != 1:
                return "http://%s/%s/%s/" % (config.wiki_base_domain, config.wiki_farm_dir, wikiname)
            else:
                return "http://%s/%s/" % (config.wiki_base_domain, config.wiki_farm_dir)
        else:
            if wiki_config.wiki_id != 1:
                return "http://%s/%s/" % (config.wiki_base_domain, wikiname)
            else:
                return "http://%s/" % config.wiki_base_domain


def getBaseFarmURL(request):
    """
    Get the url of the base wiki in the farm.
    """
    return "http://%s/" % config.wiki_base_domain

def isBaseWiki(request):
    """
    Are we the base wiki of the farm?
    """
    return request.config.wiki_id == 1


if __name__ == '__main__':
   request = request.RequestDummy() 
   create_wiki('santacruz', 'PhilipNeustrom', request) 
   request.db_disconnect() 

