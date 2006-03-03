import sys, string
sys.path.extend(['/Library/Webserver/sycamore/installhtml/dwiki', '/Library/Webserver/sycamore/'])
from LocalWiki import config, wikiutil
from LocalWiki.Page import Page
import xapian

MAX_PROB_TERM_LENGTH = 64

valid_characters = string.ascii_letters + string.digits

def _p_alnum(c):
    return (c in valid_characters)

def _p_notalnum(c):
    return not _p_alnum(c)

def _p_notplusminus(c):
    return c != '+' and c != '-'

def _find_p(string, start, predicate):
    while start<len(string) and not predicate(string[start]):
        start += 1
    return start

class searchResult(object):
  def __init__(self, title, data, percentage, page):
    self.title = title
    self.data = data
    self.percentage = percentage
    self.page = page

class Search(object):
  def __init__(self, needle_list, request, p_start_loc=0, t_start_loc=0, num_results=10):
    self.request = request
    self.needle = needle_list
    self.p_start_loc = p_start_loc
    self.t_start_loc = t_start_loc
    self.num_results = 10
    self.text_database = xapian.Database(config.text_search_db_location)
    self.title_database = xapian.Database(config.title_search_db_location)
    self.stemmer = xapian.Stem("english")
    self.terms = []
    self.text_results = [] # list of (percentage, page object, text data)
    self.title_results = [] # list of (percentage, page object, text data)
    for term in needle_list:
      self.terms.append(self.stemmer.stem_word(term.lower()))
    self.query = xapian.Query(xapian.Query.OP_OR, self.terms)

  def process(self):
    # processes the search
    enquire = xapian.Enquire(self.text_database)
    enquire.set_query(self.query)
    matches = enquire.get_mset(self.p_start_loc, self.num_results)
    for match in matches:
      title = match[xapian.MSET_DOCUMENT].get_value(0)
      page = Page(title, self.request)
      percentage = match[xapian.MSET_PERCENT]
      data = match[xapian.MSET_DOCUMENT].get_data()
      search_item = searchResult(title, data, percentage, page)
      self.text_results.append(search_item)

    enquire = xapian.Enquire(self.title_database)
    enquire.set_query(self.query)
    matches = enquire.get_mset(self.t_start_loc, self.num_results)
    for match in matches:
      title = match[xapian.MSET_DOCUMENT].get_value(0)
      page = Page(title, self.request)
      percentage = match[xapian.MSET_PERCENT]
      data = match[xapian.MSET_DOCUMENT].get_data()
      search_item = searchResult(title, data, percentage, page)
      self.title_results.append(search_item)


def _do_postings(doc, text, id, stemmer):
  # Does positional indexing
  pos = 0
  # At each point, find the next alnum character (i), then
  # find the first non-alnum character after that (j). Find
  # the first non-plusminus character after that (k), and if
  # k is non-alnum (or is off the end of the para), set j=k.
  # The term generation string is [i,j), so len = j-i

  # unique id     
  # NOTE on unique id:  we assume this is unique and not creatable via the user.  We consider 'q:this' to split as q, this -- so this shouldn't be exploitable.
  # The reason we use such a unique id is that it's the easiest way to do this using xapian.
  doc.add_term("Q:%s" % id)

  doc.add_value(0, id)

  i = 0
  while i < len(text):
      i = _find_p(text, i, _p_alnum)
      j = _find_p(text, i, _p_notalnum)
      k = _find_p(text, j, _p_notplusminus)
      if k == len(text) or not _p_alnum(text[k]):
          j = k
      if (j - i) <= MAX_PROB_TERM_LENGTH and j > i:
      	  print term
          term = stemmer.stem_word(text[i:j].lower())
          doc.add_posting(term, pos)
          pos += 1
      i = j

def index(page):
  # Add page to the search index
  stemmer = xapian.Stem("english")

  database = xapian.WritableDatabase(config.title_search_db_location, xapian.DB_CREATE_OR_OPEN)
  text = page.page_name
  doc = xapian.Document()
  doc.set_data(text)
  _do_postings(doc, text, page.page_name.lower(), stemmer)
  database.replace_document("Q:%s" % page.page_name.lower(), doc)

  database = xapian.WritableDatabase(config.text_search_db_location, xapian.DB_CREATE_OR_OPEN)
  text = page.get_raw_body()
  doc = xapian.Document()
  doc.set_data(text)
  _do_postings(doc, text, page.page_name.lower(), stemmer)
  database.replace_document("Q:%s" % page.page_name.lower(), doc)

def remove_from_index(page):
  # removes the page from the index.  call this on page deletion.  all other page changes can just call index().
  database = xapian.WritableDatabase(config.text_search_db_location, xapian.DB_CREATE_OR_OPEN)
  database.delete_document("Q:%s" % page.page_name.lower())
  database = xapian.WritableDatabase(config.title_search_db_location, xapian.DB_CREATE_OR_OPEN)
  database.delete_document("Q:%s" % page.page_name.lower())


# = Page()
#index(p)
#from LocalWiki import request
#req = request.RequestDummy()
#s = Search(['new'], req)
#s.process()
#for obj in s.title_results:
#  print obj.title
#database = xapian.WritableDatabase(config.title_search_db_location, xapian.DB_CREATE_OR_OPEN)
#database.delete_document("Q:%s" % 'Front Page')
#s = Search(['front'])
#s.process()
#print s.title_results, s.text_results
#s = Search(['front'])
#s.process()
#print s.title_results, s.text_results
#print s.__dict__
#import time
#index(p)
#s = Search(['front'])
#s.process()
#print s.title_results, s.text_results
