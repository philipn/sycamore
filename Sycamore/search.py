import sys, string, os.path, re, time

from Sycamore import config, wikiutil
from Sycamore.Page import Page

quotes_re = re.compile('"(?P<phrase>[^"]+)"')

MAX_PROB_TERM_LENGTH = 64
DIVIDERS = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
DIVIDERS_RE = r"""!"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~"""

#word_characters = string.letters + string.digits
def build_regexp(terms):
  """builds a query out of the terms.  Takes care of things like "quoted text" properly"""
  regexp = []
  for term in terms:
    if type(term) == type([]):
      # an exactly-quoted sublist
      regexp.append('(((%s)|^)%s((%s)|$))' % (DIVIDERS_RE, ' '.join(term), DIVIDERS_RE))
    elif term:
      regexp.append('([%s]|^|\s)%s([%s]|$|\s)' % (DIVIDERS_RE, term, DIVIDERS_RE))

  regexp = re.compile('|'.join(regexp), re.IGNORECASE|re.UNICODE)

  return regexp

def find_num_matches(regexp, text):
  """
  Finds the number of occurances of regexp in text
  """
  i = 0
  loc = 0
  found = regexp.search(text)
  while found:
    i += 1
    loc += found.end()
    found = regexp.search(text[loc:])

  return i

def isdivider(w):
  """
  Does w contain a character/is a character that's a divider.  Examples are:  :,/-  etc.
  """
  for c in w:
    if c in DIVIDERS: return True
  return False

def iswhitespace(w):
  return not (w.strip() == w)

def isdivider_or_whitespace(w):
  return isdivider(w) or iswhitespace(w)

def notdivider_or_whitespace(w):
  return not isdivider_or_whitespace(w)

def _p_isalnum(c):
  return c.isalnum()

def _p_notalnum(c):
  return not _p_isalnum(c)

def _p_divider(c):
    return isdivider(c)

def _p_notdivider(c):
    return not _p_divider(c)

def notplusminus(c):
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

class SearchBase(object):
  def __init__(self, needles, request, p_start_loc=0, t_start_loc=0, num_results=10):
    self.request = request
    self.needles = needles
    self.p_start_loc = p_start_loc
    self.t_start_loc = t_start_loc
    self.num_results = 10

    self.text_results = [] # list of (percentage, page object, text data)
    self.title_results = [] # list of (percentage, page object, text data)
    
  def _remove_junk(self, terms):
    # Cut each needle accordingly so that it returns good results. E.g. the user searches for "AM/PM" we want to cut this into "am" and "pm"
    nice_terms = []
    for term in terms:
      if type(term) == type([]):
        nice_terms.append(self._remove_junk(term))
	continue

      if not term.strip(): continue

      exact_match = False
      if not isdivider(term):
        nice_terms.append(term)
        continue

      if term.startswith('"') and term.endswith('"'):
        # we have an exact-match quote thing
        nice_terms.append(self._remove_junk(term.split())[1:-1])
        continue

      i = 0
      j = 0
      for c in term:
        if not isdivider(c):
          j += 1
          continue
        term_new = term[i:j].strip()
        if term_new: nice_terms.append(term_new)
        i = j+1
        j += 1
      term_new = term[i:j].strip()
      if term_new: nice_terms.append(term_new)

    return nice_terms

if config.has_xapian:
  import xapian
  class XapianSearch(SearchBase):
    def __init__(self, needles, request, p_start_loc=0, t_start_loc=0, num_results=10):
      SearchBase.__init__(self, needles, request, p_start_loc, t_start_loc, num_results)
  
      # load the databases
      self.text_database = xapian.Database(
          os.path.join(config.search_db_location, 'text'))
      self.title_database = xapian.Database(
          os.path.join(config.search_db_location, 'title'))
  
      self.stemmer = xapian.Stem("english")
      self.terms = self._remove_junk(self._stem_terms(needles))
      self.printable_terms = self._remove_junk(needles)
      if self.terms: self.query = self._build_query(self.terms)
      else: self.query = None
  
    def _stem_terms(self, terms):
      new_terms = []
      for term in terms:
        if type(term) == list:
          new_terms.append(self._stem_terms(term))
        else:
          new_terms.append(self.stemmer.stem_word(term.lower().encode('utf-8')))
      return new_terms
      
  
    def _build_query(self, terms, op=xapian.Query.OP_OR):
      """builds a query out of the terms.  Takes care of things like "quoted text" properly"""
      query = None
      for term in terms:
        if type(term) == type([]):
          # an exactly-quoted sublist
  	  exact_query = self._build_query(term, op)
  	  if query: query = xapian.Query(op, query, exact_query)
  	  else: query = xapian.Query(op, exact_query)
        else:
          if query: query = xapian.Query(op, query, xapian.Query(op, [term]))
  	  else: query = xapian.Query(op, [term])
  
      return query
  
    def process(self):
      if not self.query: return
      # processes the search
      enquire = xapian.Enquire(self.text_database)
      enquire.set_query(self.query)
      t0 = time.time()
      matches = enquire.get_mset(self.p_start_loc, self.num_results+1)
      t1 = time.time()
      for match in matches:
        title = match[xapian.MSET_DOCUMENT].get_value(0)
        page = Page(title, self.request)
        percentage = match[xapian.MSET_PERCENT]
        data = page.get_raw_body()
        search_item = searchResult(title, data, percentage, page)
        self.text_results.append(search_item)
  
      enquire = xapian.Enquire(self.title_database)
      enquire.set_query(self.query)
      matches = enquire.get_mset(self.t_start_loc, self.num_results+1)
      for match in matches:
        title = match[xapian.MSET_DOCUMENT].get_value(0)
        page = Page(title, self.request)
        percentage = match[xapian.MSET_PERCENT]
        data = page.page_name
        search_item = searchResult(title, data, percentage, page)
        self.title_results.append(search_item)

class RegexpSearch(SearchBase):
  def __init__(self, needles, request, p_start_loc=0, t_start_loc=0, num_results=10):
    SearchBase.__init__(self, needles, request, p_start_loc, t_start_loc, num_results)

    self.terms = self._remove_junk(needles)
    self.regexp = build_regexp(self.terms)

  
  def process(self):
    # processes the search
    pagelist = wikiutil.getPageList(self.request, objects=True)
    matches = []
    for page in pagelist:
      text = page.get_raw_body()
      text_matches = find_num_matches(self.regexp, text)
      if text_matches:
        percentage = (text_matches*1.0/len(text.split()))*100
	self.text_results.append(searchResult(page.page_name, text, percentage, page)) 
      
      title = page.page_name
      title_matches = find_num_matches(self.regexp, title)
      if title_matches:
        percentage = (title_matches*1.0/len(title.split()))*100
	self.title_results.append(searchResult(title, title, percentage, page))

    # sort the title and text results by relevancy
    self.title_results.sort(lambda x,y: cmp(y.percentage, x.percentage))
    self.text_results.sort(lambda x,y: cmp(y.percentage, x.percentage))

    # normalize the percentages.  still gives shit, but what can you expect from regexp..install xapian!
    if self.title_results:
      i = 0
      max_title_percentage = self.title_results[0].percentage
      self.title_results = self.title_results[self.t_start_loc:self.t_start_loc+self.num_results+1]
      for title in self.title_results:
        if i > self.num_results: break
        title.percentage = (title.percentage/max_title_percentage)*100
	i += 1

    if self.text_results: 
      i = 0 
      max_text_percentage = self.text_results[0].percentage
      self.text_results = self.text_results[self.p_start_loc:self.p_start_loc+self.num_results+1]
      for text in self.text_results:
        if i > self.num_results: break
        text.percentage = (text.percentage/max_text_percentage)*100
	i += 1


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
  id = id.encode('utf-8')
  text = text.encode('utf-8')
  doc.add_term("Q:%s" % id.lower())

  doc.add_value(0, id)

  i = 0
  while i < len(text):
      i = _find_p(text, i, notdivider_or_whitespace)
      j = _find_p(text, i, isdivider_or_whitespace)
      k = _find_p(text, j, notplusminus)
      if k == len(text) or not notdivider_or_whitespace(text[k]):
          j = k
      if (j - i) <= MAX_PROB_TERM_LENGTH and j > i:
          term = stemmer.stem_word(text[i:j].lower())
          doc.add_posting(term, pos)
          pos += 1
      i = j

def index(page, db_location=None, text_db=None, title_db=None):
  if not config.has_xapian: return
  if not db_location: db_location = config.search_db_location
  # Add page to the search index
  stemmer = xapian.Stem("english")

  if not title_db:
    database = xapian.WritableDatabase(
      os.path.join(db_location, 'title'),
      xapian.DB_CREATE_OR_OPEN)
  else: database = title_db

  text = page.page_name.encode('utf-8')
  pagename = page.page_name.encode('utf-8')
  doc = xapian.Document()
  _do_postings(doc, text, pagename, stemmer)
  database.replace_document("Q:%s" % pagename.lower(), doc)

  if not text_db:
    database = xapian.WritableDatabase(
      os.path.join(db_location, 'text'), 
      xapian.DB_CREATE_OR_OPEN)
  else: database = text_db

  text = page.get_raw_body()
  doc = xapian.Document()
  _do_postings(doc, text, pagename, stemmer)
  database.replace_document("Q:%s" % pagename.lower(), doc)

def remove_from_index(page):
  """removes the page from the index.  call this on page deletion.  all other page changes can just call index(). """
  if not config.has_xapian: return
  pagename = page.page_name.encode('utf-8')
  database = xapian.WritableDatabase(
      os.path.join(config.search_db_location, 'title'),
      xapian.DB_CREATE_OR_OPEN)

  database.delete_document("Q:%s" % pagename.lower())

  database = xapian.WritableDatabase(
      os.path.join(config.search_db_location, 'text'),
      xapian.DB_CREATE_OR_OPEN)

  database.delete_document("Q:%s" % pagename.lower())

def prepare_search_needle(needle):
  """Basically just turns a string of "terms like this" and turns it into a form usable by Search(), paying attention to "quoted subsections" for exact matches."""
  new_list = []
  quotes = quotes_re.finditer(needle)
  i = 0
  had_quote = False
  for quote in quotes:
    had_quote = True
    non_quoted_part = needle[i:quote.start()].strip().split()
    if non_quoted_part: new_list += non_quoted_part
    i = quote.end()
    new_list.append(quote.group('phrase').split())
  if had_quote: return new_list
  else:return needle.split()


if config.has_xapian: Search = XapianSearch
else: Search = RegexpSearch
