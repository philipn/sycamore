# -*- coding: utf-8 -*-

# Import
import sys
import os
import unittest
import random

__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..',
                                              '..'))])
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..'))])
import __init__

from Sycamore import request
from Sycamore import config
from Sycamore import wikiutil
from Sycamore.Page import MAX_PAGENAME_LENGTH

from basics import RequestBasics

_did_rollback = False

def make_random_string(length, alphanum_only=True):
    import random, string
    # not everything, but good nuff for now
    chars = string.letters + string.digits 
    rand_char_loc = random.randint(0, len(chars)-1)
    random_string = ''
    for j in xrange(0, random.randint(0, length)):
        random_string += random.choice(chars)
    return random_string

def make_impossible_pages(request, numpages):
    """
    Make a list of numpages pagenames that can't exist
    (aren't in the list of all pages).
    """
    import random
    all_pages = [pagename.lower() for pagename in
        wikiutil.getPageList(request)]
    impossible = []
    for i in xrange(0, numpages):
       random_string = None
       random_string_lower = None
       while random_string_lower not in all_pages and random_string is None:
          random_string = make_random_string(MAX_PAGENAME_LENGTH)
          random_string_lower = random_string.lower()
       impossible.append(random_string)
    return impossible

class PageBasics(RequestBasics):
    def _get_list_of_wikis(self):
        """A helper function which grabs the list of all wikis."""
        self.request.cursor.execute("SELECT name from wikis") 
        results = self.request.cursor.fetchall()
        wikis = [name[0] for name in results]
        return wikis

    def testBasicSave(self):
        """Test basic page save."""
        pass
    
    def testUrl(self):
        """Test's Page.url()."""
        from Sycamore.Page import Page
        from Sycamore import farm
        list_of_wikis = self._get_list_of_wikis()

        # relative, w/o query string
        for trial in xrange(0, 200):
            pagename = make_random_string(MAX_PAGENAME_LENGTH)
            page = Page(pagename, self.request)
            pagename = page.proper_name()
            pagename_encoded = wikiutil.quoteWikiname(pagename)
            proper_url = '/%s' % pagename_encoded
            self.assertEqual(proper_url, page.url())

        # relative, w/ query string
        for trial in xrange(0, 200):
            pagename = make_random_string(MAX_PAGENAME_LENGTH)
            query = '?'
            the_range = random.randint(0, 10)
            for i in xrange(0, the_range):
                if i < (the_range-1): amperstand = '&'
                else: amperstand = ''
                query += ('%s=%s%s' %
                    (make_random_string(50, alphanum_only=True),
                     make_random_string(50, alphanum_only=True),
                     amperstand))
            page = Page(pagename, self.request)
            pagename = page.proper_name()
            pagename_encoded = wikiutil.quoteWikiname(pagename)
            proper_url = '/%s?%s' % (pagename_encoded, query)
            self.assertEqual(proper_url, page.url(querystr = query))

        original_wiki_name = self.request.config.wiki_name

        # absolute url, switched request
        for wiki_trial in xrange(0, 10):
            self.request.switch_wiki(random.choice(list_of_wikis))
            for trial in xrange(0, 200):
                pagename = make_random_string(MAX_PAGENAME_LENGTH)
                farm_url = farm.getWikiURL(self.request.config.wiki_name,
                                           self.request)
                page = Page(pagename, self.request)
                pagename = page.proper_name()
                pagename_encoded = wikiutil.quoteWikiname(pagename)
                proper_url = '%s%s' % (farm_url, pagename_encoded)
                self.assertEqual(proper_url, page.url(relative=False))

            for trial in xrange(0, 200):
                pagename = make_random_string(MAX_PAGENAME_LENGTH)
                farm_url = farm.getWikiURL(self.request.config.wiki_name,
                                           self.request)
                query = '?'
                the_range = random.randint(0, 10)
                for i in xrange(0, the_range):
                    if i < (the_range-1):
                        amperstand = '&'
                    else:
                        amperstand = ''
                    query += ('%s=%s%s' %
                        (make_random_string(50, alphanum_only=True),
                         make_random_string(50, alphanum_only=True),
                         amperstand))
                page = Page(pagename, self.request)
                pagename = page.proper_name()
                pagename_encoded = wikiutil.quoteWikiname(pagename)
                proper_url = '%s%s?%s' % (farm_url, pagename_encoded, query)
                self.assertEqual(proper_url,
                                 page.url(querystr=query, relative=False))

        self.request.switch_wiki(original_wiki_name)

        # absolute url, non-switched request
        for wiki_trial in xrange(0, 10):
            wiki_name = random.choice(list_of_wikis)
            for trial in xrange(0, 200):
                pagename = make_random_string(MAX_PAGENAME_LENGTH)
                farm_url = farm.getWikiURL(wiki_name, self.request)
                page = Page(pagename, self.request, wiki_name=wiki_name)
                pagename = page.proper_name()
                pagename_encoded = wikiutil.quoteWikiname(pagename)
                proper_url = '%s%s' % (farm_url, pagename_encoded)
                self.assertEqual(proper_url, page.url(relative=False))

            for trial in xrange(0, 200):
                pagename = make_random_string(MAX_PAGENAME_LENGTH)
                farm_url = farm.getWikiURL(wiki_name, self.request)
                query = '?'
                the_range = random.randint(0, 10)
                for i in xrange(0, the_range):
                    if i < (the_range-1):
                        amperstand = '&'
                    else:
                        amperstand = ''
                    query += ('%s=%s%s' %
                        (make_random_string(50, alphanum_only=True),
                         make_random_string(50, alphanum_only=True),
                         amperstand))
                page = Page(pagename, self.request, wiki_name=wiki_name)
                pagename = page.proper_name()
                pagename_encoded = wikiutil.quoteWikiname(pagename)
                proper_url = '%s%s?%s' % (farm_url, pagename_encoded, query)
                self.assertEqual(proper_url,
                                 page.url(querystr = query, relative=False))

if __name__ == "__main__":
    unittest.main()
