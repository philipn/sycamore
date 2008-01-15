# -*- coding: utf-8 -*-

# Imports
import sys
import string
import os.path
import re
import time
import threading
import socket
import random

from Sycamore.Page import Page

from Sycamore import config
from Sycamore import wikiutil

quotes_re = re.compile('"(?P<phrase>[^"]+)"')

MAX_PROB_TERM_LENGTH = 64
DIVIDERS = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
DIVIDERS_RE = r"""!"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~"""

# number of times to try and grab a result set from xapian
# (only used if we get an error)
NUM_ENQUIRE_TRIES = 10 

# Limit imposed by xapian's internal btree
BTREE_SAFE_KEY_LEN = 240

# I know this is repetitive..
NOT_ALLOWED_CHARS = '><?#[]_{}|~"'
# ..but we can't import because it's circular
id_seperator = NOT_ALLOWED_CHARS[0]

# How many results can a spelling-corrected query differ
# from a normal query before we display the correction?
SPELLING_DELTA = 1

def make_id(pagename, wikiname):
    if config.wiki_farm:
        # TODO: let's fix this so we really only send this function one type
        if type(wikiname) == unicode:
            wikiname = wikiname.encode('utf-8')
        if type(pagename) == unicode:
            pagename = pagename.encode('utf-8')
        return "%s%s%s" % (wikiname, id_seperator, pagename)
    else:
        return pagename.encode('utf-8')

def get_id(id):
    if config.wiki_farm:
        id_split = id.split(id_seperator) 
        wikiname = id_split[0]
        pagename = id_split[1]
        return (pagename, wikiname)
    else:
        return id

def build_regexp(terms):
    """
    Builds a query out of the terms.
    Takes care of things like "quoted text" properly
    """
    regexp = []
    for term in terms:
        if type(term) == type([]):
            # an exactly-quoted sublist
            regexp.append('(((%s)|^)%s((%s)|$))' % (
                DIVIDERS_RE, ' '.join(term), DIVIDERS_RE))
        elif term:
            regexp.append('([%s]|^|\s)%s([%s]|$|\s)' % (
                DIVIDERS_RE, term, DIVIDERS_RE))

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

def flatten(L):
    if type(L) != type([]): return [L]
    if L == []: return L
    return flatten(L[0]) + flatten(L[1:])

def isdivider(w):
    """
    Does w contain a character/is a character that's a divider.
    Examples are:  :,/-  etc.
    """
    for c in w:
        if c in DIVIDERS:
            return True
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
    def __init__(self, title, data, percentage, page_name, wiki_name):
        self.title = title
        self.data = data
        self.percentage = percentage
        self.page_name = page_name
        self.wiki_name = wiki_name

class SearchBase(object):
    def __init__(self, needles, request, p_start_loc=0, t_start_loc=0,
                 num_results=10, wiki_global=False):
        self.request = request
        self.needles = needles
        self.p_start_loc = p_start_loc
        self.t_start_loc = t_start_loc
        self.num_results = 10
        self.wiki_global = wiki_global
        self.exact_match = False

        self.text_results = [] # list of searchResult objects
        self.title_results = [] # list of searchResult objects
      
    def _remove_junk(self, terms):
        """
        Cut each needle accordingly so that it returns good results.
        E.g. the user searches for "AM/PM" we want to cut this
        into "am" and "pm"
        """
        nice_terms = []
        for term in terms:
            if type(term) == type([]):
              nice_terms.append(self._remove_junk(term))
              continue

            if not term.strip():
                continue

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
                if term_new:
                    nice_terms.append(term_new)
                i = j+1
                j += 1
            term_new = term[i:j].strip()
            if term_new:
                nice_terms.append(term_new)

        return nice_terms

    def spelling_suggestion():
        pass

if config.has_xapian:
    import xapian
    class XapianSearch(SearchBase):
        def __init__(self, needles, request, p_start_loc=0, t_start_loc=0,
                     num_results=10, db_location=None, processed_terms=None,
                     wiki_global=False):
            SearchBase.__init__(self, needles, request, p_start_loc,
                                t_start_loc, num_results,
                                wiki_global=wiki_global)
    
            # load the databases
            if not db_location:
                db_location = config.search_db_location
            self.text_database = xapian.Database(os.path.join(db_location,
                                                              'text'))
            self.title_database = xapian.Database(os.path.join(db_location,
                                                               'title'))
            # just where we keep it
            self.spelling_database = self.title_database

            if not processed_terms:
                self.stemmer = xapian.Stem("english")
                self.terms = self._remove_junk(self._stem_terms(needles))
                self.unstemmed_terms = self._remove_junk(needles)
                self.printable_terms = needles
            else:
                self.terms = processed_terms

            if self.terms:
                self.query = self._build_query(self.terms)
            else:
                self.query = None
    
        def _stem_terms(self, terms):
            new_terms = []
            if not terms:
                return []
            for term in terms:
                if type(term) == list:
                    new_terms.append(self._stem_terms(term))
                else:
                    term = term.lower()
                    for stemmed_term, real_term, pos in get_stemmed_text(
                            term, self.stemmer):
                        new_terms.append(stemmed_term)
            return new_terms
    
        def _build_query(self, terms, op=xapian.Query.OP_OR):
            """
            builds a query out of the terms.
            Takes care of things like "quoted text" properly
            """
            query = None

            if type(terms[0]) == list:
                query = xapian.Query(xapian.Query.OP_PHRASE, terms[0])
                self.exact_match = True
            else:
                for term in terms:
                    # an exactly-quoted sublist
                    if type(term) == list:
                        subquery = xapian.Query(xapian.Query.OP_PHRASE, term)
                        if query:
                            query = xapian.Query(op, query, subquery)
                        else:
                            query = subquery
                    else:
                        if query:
                            query = xapian.Query(op, query,
                                                 xapian.Query(op, [term]))
                        else:
                            query = xapian.Query(op, [term])

                terms_without_exact = filter(lambda x: type(x) != list, terms) 
                query = xapian.Query(xapian.Query.OP_OR, query,
                                     xapian.Query(xapian.Query.OP_NEAR,
                                                  terms_without_exact))
              
            if config.wiki_farm and not self.wiki_global:
                specific_wiki = xapian.Query(xapian.Query.OP_OR, [
                    ('F:%s' % self.request.config.wiki_name).encode('utf-8')])
                query = xapian.Query(xapian.Query.OP_AND, query, specific_wiki)

            return query

        def _get_matchset(self, enquire, database, start_loc, num_results):
            for i in range(0, NUM_ENQUIRE_TRIES):
                try:
                    matches = enquire.get_mset(start_loc, num_results)
                except IOError, e:
                    if "DatabaseModifiedError" in str(e):
                         had_error = True
                         _search_sleep_time()
                         database.reopen()
                         continue
                    else:
                         raise
                except RuntimeError, e:
                    if "iunknown error in Xapian" in str(e):
                         had_error = True
                         _search_sleep_time()
                         database.reopen()
                         continue
                    else:
                         raise

                break
                if i == (NUM_ENQUIRE_TRIES-1):
                    raise (Exception, "DatabaseModifiedError")
            return matches
    
        def process(self):
            if not self.query:
                return
            # processes the search
            enquire = xapian.Enquire(self.text_database)
            enquire.set_query(self.query)
            t0 = time.time()

            matches = self._get_matchset(enquire, self.text_database,
                                         self.p_start_loc, self.num_results+1)
            
            self.estimated_results = matches.get_matches_estimated()
            t1 = time.time()
            for match in matches:
                id = match[xapian.MSET_DOCUMENT].get_value(0)
                wiki_name = self.request.config.wiki_name
                if config.wiki_farm:
                    title, wiki_name = get_id(id)
                    # xapian uses utf-8
                    title = title.decode('utf-8')
                    wiki_name = wiki_name.decode('utf-8')
                else:
                    title = get_id(id).decode('utf-8')
                page = Page(title, self.request, wiki_name=wiki_name)
                if not page.exists():
                    continue
                percentage = match[xapian.MSET_PERCENT]
                data = page.get_raw_body()
                search_item = searchResult(title, data, percentage,
                                           page.page_name, wiki_name)
                self.text_results.append(search_item)
    
            enquire = xapian.Enquire(self.title_database)
            enquire.set_query(self.query)
            matches = self._get_matchset(enquire, self.text_database,
                                         self.t_start_loc, self.num_results+1)

            self.estimated_results += matches.get_matches_estimated()
            for match in matches:
                id = match[xapian.MSET_DOCUMENT].get_value(0)
                wiki_name = self.request.config.wiki_name
                if config.wiki_farm:
                    title, wiki_name = get_id(id)
                    # xapian uses utf-8
                    title = title.decode('utf-8')
                    wiki_name = wiki_name.decode('utf-8')
                else:
                    title = get_id(id).decode('utf-8')
                page = Page(title, self.request, wiki_name=wiki_name)
                if not page.exists():
                    continue
                percentage = match[xapian.MSET_PERCENT]
                data = page.page_name
                search_item = searchResult(title, data, percentage,
                                           page.page_name, wiki_name)
                self.title_results.append(search_item)

        def spelling_suggestion(self, needle):
            def _fill_in_corrected(corrected_terms, html=False):
                correct_string = []
                word = []
                i = 0
                unstemmed_terms = flatten(self.unstemmed_terms)
                for c in needle:
                    if isdivider_or_whitespace(c):
                        if word:
                            this_word_differed = (
                                unstemmed_terms[i] != corrected_terms[i]
                            )
                            if html and this_word_differed:
                                correct_string.append('<strong>')
                            correct_string += corrected_terms[i]
                            if html and this_word_differed:
                                correct_string.append('</strong>')
                            i += 1
                        correct_string.append(c)
                        word = []
                    else:
                        word.append(c)
                if word:
                    correct_string += corrected_terms[i]

                return ''.join(correct_string)

            if not self.terms:
                return

            corrected_terms = [
                self.spelling_database.get_spelling_suggestion(word) or word
                for word in flatten(self.unstemmed_terms)
            ]
            corrected_needle = _fill_in_corrected(corrected_terms)
            corrected_html = _fill_in_corrected(corrected_terms, html=True)

            corrected_terms_for_query = self._remove_junk(
                self._stem_terms(corrected_terms))
            corrected_query = self._build_query(corrected_terms_for_query)

            enquire = xapian.Enquire(self.text_database)
            enquire.set_query(corrected_query)
            matches = self._get_matchset(enquire, self.text_database,
                                         0, self.num_results+1)
            corrected_estimated_results = matches.get_matches_estimated()

            enquire = xapian.Enquire(self.title_database)
            enquire.set_query(corrected_query)
            matches = self._get_matchset(enquire, self.title_database,
                                         0, self.num_results+1)
            corrected_estimated_results += matches.get_matches_estimated()

            num_results_difference = (corrected_estimated_results -
                                      self.estimated_results)
            if (num_results_difference >= 0 and
                corrected_terms != flatten(self.unstemmed_terms)):
                return (corrected_needle, corrected_html)

    class RemoteSearch(XapianSearch):
        def __init__(self, needles, request, p_start_loc=0, t_start_loc=0,
                     num_results=10, wiki_global=False, needle_as_entered=''):
            SearchBase.__init__(self, needles, request, p_start_loc,
                                t_start_loc, num_results,
                                wiki_global=wiki_global)
            self.stemmer = xapian.Stem("english")
            self.terms = self._remove_junk(self._stem_terms(needles))
            self.unstemmed_terms = self._remove_junk(needles)
            self.printable_terms = self._remove_junk(needles)
            self.needles = needles
            self._spelling_suggestion = None
            self.needle_as_entered = needle_as_entered

        def process(self):
            import socket, cPickle
            encoded_terms = wikiutil.quoteFilename(
                cPickle.dumps(self.needle_as_entered, True))
            server_address, server_port = config.remote_search
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
            s.connect((server_address, server_port))

            output = s.makefile('w', 0)
            output.write('F\n')
            if self.wiki_global:
                output.write('*\n\n')
            else:
                output.write('%s\n\n' % self.request.config.wiki_name)
            output.write('S\n%s\n%s\n' % (self.p_start_loc, self.t_start_loc))
            output.write('%s\n' % encoded_terms)
            output.write('\n')
            output.write('E\n\n') # end
            output.close()

            input = s.makefile('r', 0)
            for line in input:
                results_encoded = line.strip()
                break

            title_results, text_results, spelling_suggest = cPickle.loads(
                wikiutil.unquoteFilename(results_encoded))

            s.close()

            self.title_results = title_results
            self.text_results = text_results
            self._spelling_suggestion = spelling_suggest

        def spelling_suggestion(self, needle):
            return self._spelling_suggestion

class RegexpSearch(SearchBase):
    def __init__(self, needles, request, p_start_loc=0, t_start_loc=0,
                 num_results=10, wiki_global=False):
        SearchBase.__init__(self, needles, request, p_start_loc, t_start_loc,
                            num_results, wiki_global=wiki_global)
        self.terms = self._remove_junk(needles)
        self.printable_terms = self.terms
        self.regexp = build_regexp(self.terms)
    
    def process(self):
        # processes the search
        wiki_name = self.request.config.wiki_name
        if not self.wiki_global:
            wikis = [wiki_name]
        else:
            wikis = wikiutil.getWikiList(self.request)

        for wiki_name in wikis: 
            pagelist = wikiutil.getPageList(self.request)
            matches = []
            for pagename in pagelist:
                page = Page(pagename, self.request, wiki_name=wiki_name)
                text = page.get_raw_body()
                text_matches = find_num_matches(self.regexp, text)
                if text_matches:
                    percentage = (text_matches*1.0/len(text.split()))*100
                    self.text_results.append(searchResult(page.page_name, text,
                                                          percentage,
                                                          page.page_name,
                                                          wiki_name)) 
              
                title = page.page_name
                title_matches = find_num_matches(self.regexp, title)
                if title_matches:
                      percentage = (title_matches*1.0/len(title.split()))*100
                      self.title_results.append(searchResult(title, title,
                                                             percentage,
                                                             page.page_name,
                                                           wiki_name))
            # sort the title and text results by relevancy
            self.title_results.sort(lambda x,y: cmp(y.percentage,
                                                    x.percentage))
            self.text_results.sort(lambda x,y: cmp(y.percentage,
                                                   x.percentage))

            # normalize the percentages.
            # still gives shit, but what can you expect from regexp?
            # install xapian!
            if self.title_results:
                i = 0
                max_title_percentage = self.title_results[0].percentage
                self.title_results = self.title_results[
                    self.t_start_loc:self.t_start_loc+self.num_results+1]
                for title in self.title_results:
                    if i > self.num_results:
                        break
                    title.percentage = title.percentage/max_title_percentage
                    title.percentage = title.percentage*100
                    i += 1

            if self.text_results: 
                i = 0 
                max_text_percentage = self.text_results[0].percentage
                self.text_results = self.text_results[
                    self.p_start_loc:self.p_start_loc+self.num_results+1]
                for text in self.text_results:
                    if i > self.num_results:
                        break
                    text.percentage = text.percentage/max_text_percentage
                    text.percentage = text.percentage*100
                    i += 1


def get_stemmed_text(text, stemmer):
    """
    Returns a stemmed version of text.

    @return list of stemmed_term, real_term, position tuples.
    """
    postings = []
    pos = 0
    # At each point, find the next alnum character (i), then
    # find the first non-alnum character after that (j). Find
    # the first non-plusminus character after that (k), and if
    # k is non-alnum (or is off the end of the para), set j=k.
    # The term generation string is [i,j), so len = j-i
    if type(text) == unicode:
        text = text.encode(config.charset)

    i = 0
    while i < len(text):
        i = _find_p(text, i, notdivider_or_whitespace)
        j = _find_p(text, i, isdivider_or_whitespace)
        k = _find_p(text, j, notplusminus)
        if k == len(text) or not notdivider_or_whitespace(text[k]):
            j = k
        if (j - i) <= MAX_PROB_TERM_LENGTH and j > i:
            real_term = text[i:j].lower()
            term = stemmer(real_term)
            postings.append((term, real_term, pos)) 
            pos += 1
        i = j
    return postings

def _do_postings(doc, text, id, stemmer, request):
    """
    Does positional indexing.
    """
    # unique id.
    # NOTE on unique id: 
    # we assume this is unique and not creatable via the user.
    # We consider 'q:this' to split as q, this, so this shouldn't be
    # exploitable.
    # The reason we use such a unique id is that it's the easiest way to do
    # this using xapian.
    if len(("Q:%s" % id)) > BTREE_SAFE_KEY_LEN:
        return
    doc.add_term(("Q:%s" % id))
    if config.wiki_farm:
        doc.add_term(("F:%s" % request.config.wiki_name).encode('utf-8'))

    doc.add_value(0, id)

    for term, real_term, pos in get_stemmed_text(text, stemmer):
        if len(term) < BTREE_SAFE_KEY_LEN:
            doc.add_posting(term, pos)

def _get_document_words(text, stemmer):
    """
    Gets the list of non-stemmed words that the document contains.

    @return list of words
    """
    return [ real_term for stemmed_term, real_term, pos in
                get_stemmed_text(text, stemmer) ]

def _add_to_spelling(doc, text, database, stemmer):
    """
    Add the given text to the spelling database.
    """
    _delete_from_spelling(doc, database, stemmer)
    doc.set_data(text)
    for word in _get_document_words(text, stemmer):
        database.add_spelling(word)

def _delete_from_spelling(doc, database, stemmer):
    """
    Delete the given text from the spelling database.
    """
    current_document_text = doc.get_data()
    for word in _get_document_words(current_document_text, stemmer):
        database.remove_spelling(word)

def _search_sleep_time():
    """
    Sleep for a bit before trying to hit the db again. 
    """
    sleeptime = 0.1 + random.uniform(0, .05)
    time.sleep(sleeptime)    

def re_init_remote_index():
    server_address, server_port = config.remote_search
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect((server_address, server_port))

    output = s.makefile('w', 0)
    output.write('Is\n')
    output.write('E\n\n') # end
    output.close()

    s.close() 
    del s

def re_init_remote_index_end():
    server_address, server_port = config.remote_search
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect((server_address, server_port))

    output = s.makefile('w', 0)
    output.write('Ie\n')
    output.write('E\n\n') # end
    output.close()

    s.close() 
    del s

def add_to_remote_index(page):
    server_address, server_port = config.remote_search
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect((server_address, server_port))

    output = s.makefile('w', 0)
    output.write('F\n')
    output.write('%s\n\n' % page.wiki_name)
    output.write('A\n')
    output.write('%s\n' % wikiutil.quoteFilename(page.page_name))
    output.write('\n')
    output.write('E\n\n') # end
    output.close()

    s.close() 
    del s

def add_to_index(page, db_location=None, text_db=None, title_db=None,
                 try_remote=True, do_now=False):
    """
    Add page to the search index
    """
    if not config.has_xapian:
        return
    if not db_location:
        db_location = config.search_db_location
    if try_remote and config.remote_search:
        # the search server is in a different transaction than we are,
        # so we want to wait until we commit before telling it to index
        if not do_now:
            page.request.postCommitActions.append(
                (threading.Thread(target=add_to_remote_index,
                                  args=(page,)).start, [])) 
        else:
            add_to_remote_index(page)
    else:
        index(page, db_location=db_location, text_db=text_db, title_db=title_db)

def index(page, db_location=None, text_db=None, title_db=None):
    """
    Don't call this function.  Call add_to_index.
    """
    if not page.exists():
        return
    stemmer = xapian.Stem("english")

    if not title_db:
        while 1:
            try:
                database = xapian.WritableDatabase(
                  os.path.join(db_location, 'title'),
                  xapian.DB_CREATE_OR_OPEN)
            except IOError, err:
                strerr = str(err) 
                if strerr == ('DatabaseLockError: Unable to acquire database '
                              'write lock %s' % os.path.join(os.path.join(
                                db_location, 'title'), 'db_lock')):
                    if config.remote_search:
                        # we shouldn't try again if we're using remote db
                        raise IOError, err 
                    _search_sleep_time()
                else:
                    raise IOError, err
            else:
                break
    else:
        database = title_db

    # we just keep spelling information in one place
    spelling_database = database
    
    text = page.page_name
    pagename = page.page_name
    id = make_id(pagename, page.request.config.wiki_name)
    doc = xapian.Document()
    _do_postings(doc, text, id, stemmer, page.request)
    _add_to_spelling(doc, text, spelling_database, stemmer)
    database.replace_document("Q:%s" % id, doc)

    if not text_db:
        while 1:
            try:
                database = xapian.WritableDatabase(
                  os.path.join(db_location, 'text'),
                  xapian.DB_CREATE_OR_OPEN)
            except IOError, err:
                strerr = str(err) 
                if strerr == ('DatabaseLockError: Unable to acquire database '
                              'write lock %s' % os.path.join(
                                os.path.join(db_location, 'text'), 'db_lock')):
                    if config.remote_search:
                        # we shouldn't try again if we're using remote db
                        raise IOError, err 
                    _search_sleep_time()
                else:
                    raise IOError, err
            else:
                break
    else:
        database = text_db

    text = page.get_raw_body().encode('utf-8')
    doc = xapian.Document()
    _do_postings(doc, text, id, stemmer, page.request)
    _add_to_spelling(doc, text, spelling_database, stemmer)
    database.replace_document("Q:%s" % id, doc)

def remove_from_remote_index(page):
    server_address, server_port = config.remote_search
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect((server_address, server_port))

    output = s.makefile('w', 0)
    output.write('F\n')
    output.write('%s\n\n' % page.request.config.wiki_name)
    output.write('D\n')
    output.write('%s\n' % wikiutil.quoteFilename(page.page_name))
    output.write('\n')
    output.write('E\n\n') # end
    output.close()

    s.close() 

def remove_from_index(page, db_location=None, text_db=None, title_db=None,
                      do_now=False):
    """
    removes the page from the index.  call this on page deletion.
    all other page changes can just call index().
    """
    if not config.has_xapian:
        return
    if not db_location:
        db_location = config.search_db_location
    if config.remote_search:
        # the search server is in a different transaction than we are,
        # so we want to wait until we commit before telling it to index
        if not do_now:
            page.request.postCommitActions.append(
                (threading.Thread(target=remove_from_remote_index,
                                  args=(page,)).start, [])) 
        else:
            remove_from_index(page)
    else:
        remove(page, db_location=db_location, text_db=text_db,
               title_db=title_db)

def remove(page, db_location=None, text_db=None, title_db=None):
    """
    Don't call this function.  Call remove_from_index.
    """
    if not title_db:
        while 1:
            try:
                title_db = xapian.WritableDatabase(
                  os.path.join(db_location, 'title'),
                  xapian.DB_CREATE_OR_OPEN)
            except IOError, err:
                strerr = str(err) 
                if strerr == ('DatabaseLockError: Unable to acquire database '
                              'write lock %s' % os.path.join(
                                os.path.join(db_location, 'title'),
                                             'db_lock')):
                    if config.remote_search:
                        # we shouldn't try again if we're using remote db
                        raise IOError, err 
                    _search_sleep_time()
                else:
                    raise IOError, err
            else:
                break

    pagename = page.page_name
    id = make_id(pagename, page.request.config.wiki_name)

    title_db.delete_document("Q:%s" % id)

    if not text_db:
        while 1:
            try:
                text_db = xapian.WritableDatabase(
                  os.path.join(db_location, 'text'),
                  xapian.DB_CREATE_OR_OPEN)
            except IOError, err:
                strerr = str(err) 
                if strerr == ('DatabaseLockError: Unable to acquire database '
                              'write lock %s' % os.path.join(
                                os.path.join(db_location, 'text'),
                                             'db_lock')):
                    if config.remote_search:
                        # we shouldn't try again if we're using remote db
                        raise IOError, err 
                    _search_sleep_time()
                else:
                    raise IOError, err
            else:
                break

    text_db.delete_document("Q:%s" % id)

def prepare_search_needle(needle):
    """
    Basically just turns a string of "terms like this" and turns it into a form
    usable by Search(), paying attention to "quoted subsections" for exact
    matches.
    """
    if config.has_xapian:
        stemmer = xapian.Stem("english")
    else:
        stemmer = None
      
    new_list = []
    quotes = quotes_re.finditer(needle)
    i = 0
    had_quote = False
    for quote in quotes:
        had_quote = True
        non_quoted_part = needle[i:quote.start()].strip().split()
        if non_quoted_part:
            new_list += non_quoted_part
        i = quote.end()
        new_phrase = []
        phrase = quote.group('phrase').encode('utf-8').split()
        new_list.append(phrase)
    else:
        needles = needle.encode('utf-8').split()
        new_needle = needles

    if had_quote:
        new_needle = new_list

    return new_needle

# Set up Search object
if config.has_xapian:
    if config.remote_search:
        Search = RemoteSearch 
    else:
        Search = XapianSearch
else:
    Search = RegexpSearch
