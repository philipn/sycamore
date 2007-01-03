"""
    Sycamore - Wiki Utility Functions

    @copyright: 2000 - 2004 by J?rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, re, urllib, difflib, string
import time, cStringIO
from copy import copy

from Sycamore import config, util, wikidb
from Sycamore.util import pysupport

#import pytz from support
import sys, os.path
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, 'support'))])
import pytz

DAY_IN_SECONDS = 86400

# constants for page names
PARENT_PREFIX = "../" # changing this might work, but it's not tested
CHILD_PREFIX = "/" # changing this will not really work

# Caching for precompiled page type regex
_TEMPLATE_RE = None
_FORM_RE = None
_CATEGORY_RE = None
_GROUP_RE = None

# interwiki types
INTERWIKI_LIST_TYPE = 0
INTERWIKI_FARM_TYPE = 1
INTERWIKI_NONE_TYPE = 2

# The maximum number of random pages to grab from the current page list
MAX_RANDOM_GET = 1000
RAND_EXPIRE_TIME = 60*60

if config.db_type == 'postgres': RAND_FUNCTION = 'random()'
elif config.db_type == 'mysql': RAND_FUNCTION = 'rand()'

def isImage(filename):
  import mimetypes
  from Sycamore.action.Files import f2e
  guess = mimetypes.guess_type(filename)
  if guess[0]:
     return ((guess[0].split('/'))[0] == 'image') and ((guess[0].split('/'))[1]).upper() in f2e
  return False

def prepareAllProperties():
  # sets up the consistent data between requests.  right now, this is just the db connection
  d = {}
  return d

def simpleParse(request, text):
    # this needs to convert all the basic formatting to HTML
    # so the ''text'' stuff, along with [http://myurl.com url] -> a href, and the ["wiki link" link text] -> a href
    # Wiki links

    text = re.sub(r'(\[\"(?P<wikilink>[^\]\"]+)\"\])', r'<a href="%s/\g<wikilink>">\g<wikilink></a>' % request.getScriptname(), text)
    text = re.sub(r'(\[\"(?P<wikilink>([^\]\"]+))\" (?P<txt>([^\]]+))\])', r'<a href="%s/\g<wikilink>">\g<txt></a>' % request.getScriptname(), text)
    # External links
#    text = re.sub(r'(\[(?P<link>([^ ])+) (?P<ltext>([^\]])+)\])', r'<a href="\g<link>">\g<ltext></a>', text)
    text = re.sub(r'(\[(?P<link>[^\]]+(.jpg|.jpeg|.gif|.png))\])', r'<img src="\g<link>">', text)
    text = re.sub(r'(\[(?P<link>[^\] ]+)( )+(?P<txt>([^\]])+)\])', r'<a href="\g<link>">\g<txt></a>', text)
    text = re.sub(r'(\[(?P<link>[^\]]+)\])', r'<a href="\g<link>">\g<link></a>', text)
    # Limited Formatting
    text = re.sub(r'(\'\'\'\'\'(?P<txt>.*?)\'\'\'\'\')', r'<b><i>\g<txt></b></i>', text)
    text = re.sub(r'(\'\'\'(?P<txt>.*?)\'\'\')', r'<b>\g<txt></b>', text)
    text = re.sub(r'(\'\'(?P<txt>.*?)\'\')', r'<i>\g<txt></i>', text) 
    return text

def simpleStrip(request, text):
    # mirror of simpleParse, except it kills all html tags, really, so it's stripping and giving us just 'text'
    text = simpleParse(request, text)
    text = re.sub(r'\<[^\>]+\>', r'', text)
    return text

def getTimeOffset(tz_string):
    def _utcoffset(timezone):
        utc_offset_delta = timezone.utcoffset(timezone)
        return utc_offset_delta.days*DAY_IN_SECONDS + utc_offset_delta.seconds

    tz = pytz.timezone(tz_string)
    return _utcoffset(tz)

def mc_quote(s):
  """ Quoting for memcached use."""
  from Sycamore.wikiaction import NOT_ALLOWED_CHARS
  s = s.replace("_", NOT_ALLOWED_CHARS[0])  # use a character we know can't occur in pagenames
  s = s.replace(" ", "_")
  return s

def mc_unquote(s):
  """ un-does mc_quote() """
  from Sycamore.wikiaction import NOT_ALLOWED_CHARS
  s = s.replace("_", " ")
  s = s.replace(NOT_ALLOWED_CHARS[0], "_")
  return s 

def wikifyString(text, request, page, doCache=True, formatter=None, delays=None, strong=False):
  import cStringIO
  # easy to turng wiki markup string into html
  # only use this in macros, etc.
  
  # find out what type of formatter we're using
  if hasattr(formatter, 'assemble_code'):
    from Sycamore.formatter.text_html import Formatter
    html_formatter = Formatter(request) 
    py_formatter = formatter
  else:
    doCache = False
    from Sycamore.formatter.text_python import Formatter
    if formatter:
      html_formatter = formatter
    else:
      from Sycamore.formatter.text_html import Formatter
      html_formatter = Formatter(request)
    doCache = False
    py_formatter = Formatter(request)

  if strong: Parser = importPlugin("parser", "wiki", "Parser")
  else: Parser = importPlugin("parser", "wiki_simple", "Parser")

  html_formatter.setPage(page)
  buffer = cStringIO.StringIO()
  request.redirect(buffer)
  html_parser = Parser(text, request)
  html_parser.format(html_formatter)
  request.redirect()
  
  if doCache:
    import marshal
    buffer.close()
    buffer = cStringIO.StringIO()
    request.redirect(buffer)
    parser = Parser(text, request)
    py_formatter.delays = delays
    parser.format(py_formatter)
    request.redirect()
    text = buffer.getvalue().decode('utf-8')
    buffer.close()

    return text
  else:
    text = buffer.getvalue()
    buffer.close()
    return text.decode('utf-8')

def macro_delete_checks(page):
    """
    Certain macros, such as [[address]], do things when they are taken out of the page.
    
    This is where locations are added and deleted.
    """
    from Sycamore.Page import Page
    if not page.request.config.has_old_wiki_map:
       # we parse the page text here because we need to in order to infer macro information
       request = page.request
       buffer = cStringIO.StringIO()
       request.redirect(buffer)
       Page(page.page_name, request).send_page(content_only=1)
       request.sent_page_content = buffer.getvalue()
       request.redirect()

       if page.request.addresses or page.hasMapPoints():
           timenow = time.time()
           # get current locations
           current_locations = []
           page.request.cursor.execute("""SELECT x, y, created_time, created_by, created_by_ip, pagename_propercased, address from mapPoints
                where pagename=%(pagename)s and wiki_id=%(wiki_id)s""", {'pagename':page.page_name, 'wiki_id':page.request.config.wiki_id})
           result = page.request.cursor.fetchall()
           if result:
                for x, y, created_time, created_by, created_by_ip, pagename_propercased, address in result:
                    current_locations.append((pagename_propercased.lower(), x, y, address))

           locations_to_remove = copy(current_locations)
           locations_to_add = []
           # filter out locations we have listed as an address but are already in the DB
           for place in page.request.addresses:
               if (place.name.lower(), place.latitude, place.longitude, place.address) in current_locations:
                  locations_to_remove.remove((place.name.lower(), place.latitude, place.longitude, place.address))
               else:
                  locations_to_add.append(place)

           for pagename, x, y, address in locations_to_remove:
               page.request.cursor.execute("INSERT into oldMapPoints (pagename, x, y, created_time, created_by, created_by_ip, deleted_time, deleted_by, deleted_by_ip, pagename_propercased, address, wiki_id) values (%(pagename)s, %(x)s, %(y)s, (select created_time from mapPoints where pagename=%(pagename)s and x=%(x)s and y=%(y)s and address=%(address)s and wiki_id=%(wiki_id)s), (select created_by from mapPoints where pagename=%(pagename)s and x=%(x)s and y=%(y)s and address=%(address)s and wiki_id=%(wiki_id)s), (select created_by_ip from mapPoints where pagename=%(pagename)s and x=%(x)s and y=%(y)s and address=%(address)s and wiki_id=%(wiki_id)s), %(time_now)s, %(deleted_by)s, %(deleted_by_ip)s, (select pagename_propercased from mapPoints where pagename=%(pagename)s and x=%(x)s and y=%(y)s and address=%(address)s and wiki_id=%(wiki_id)s), %(address)s, %(wiki_id)s)", {'pagename':pagename, 'x':x, 'y':y, 'time_now':timenow, 'deleted_by':page.request.user.id, 'deleted_by_ip':page.request.remote_addr, 'address':address, 'wiki_id':page.request.config.wiki_id}, isWrite=True)
               page.request.cursor.execute("DELETE from mapPoints where pagename=%(pagename)s and wiki_id=%(wiki_id)s and x=%(x)s and y=%(y)s and address=%(address)s", {'pagename':pagename, 'x':x, 'y':y, 'address':address, 'wiki_id':page.request.config.wiki_id}, isWrite=True)

           for place in locations_to_add:
               place.addPlace()

def isInFarm(wikiname, request):
    """
    Is wikiname in our wiki farm?
    """
    wiki_settings = config.Config(wikiname, request)
    if wiki_settings.active:
        return True
    return False

def talk_to_article_pagename(talk_pagename):
    """
    Returns the article pagename associated with this talk pagename.
    """
    return talk_pagename[:len(talk_pagename)-5]

def article_to_talk_pagename(article_pagename):
    """
    Returns the talk pagename associated with this article pagename.
    """
    return article_pagename + '/Talk'

def init_logo_sizes(request):
    """
    Gets the wiki logos' sizes and saves them to the wiki config.
    """
    from PIL import Image
    main_logo_file = wikidb.getFile(request, {'filename':'logo.png', 'page_name': '%s/%s' % (config.wiki_settings_page, config.wiki_settings_page_images)})
    if main_logo_file:
        main_logo_file = cStringIO.StringIO(main_logo_file[0])
        main_logo = Image.open(main_logo_file)
        main_logo_size = main_logo.size
        main_logo_file.close()
        request.config.logo_sizes['logo.png'] = main_logo_size

    floater_file = wikidb.getFile(request, {'filename':'logo_backgroun.png', 'page_name': '%s/%s' % (config.wiki_settings_page, config.wiki_settings_page_images)})
    if floater_file:
        floater_file = cStringIO.StringIO(floater_file[0])
    	floater = Image.open(floater_file)
    	floater_size = floater.size
    	floater_file.close()
        request.config.logo_sizes['logo_background.png'] = floater_size

    request.config.set_config(request.config.wiki_name, request.config.get_dict(), request)
    
def getSmiley(text, formatter):
    """
    Get a graphical smiley for a text smiley
    
    @param text: the text smiley
    @param formatter: the formatter to use
    @rtype: string
    @return: formatted output
    """
    req = formatter.request
    # We turn off smilies for now...
    """
    if req.user.show_emoticons:
        w, h, b, img = config.smileys[text.strip()]
        href = img
        if not href.startswith('/'):
            href = req.theme.img_url(img)
        return formatter.image(src=href, alt=text, width=w, height=h)
    else:
        return formatter.text(text)
    """
    return formatter.text(text)

def getWikiList(request):
   """
   Returns a list of the names of all of the wikis.
   """
   request.cursor.execute("SELECT name from wikis")
   results = request.cursor.fetchall()
   if results:  return [ result[0] for result in results ]
   return None

def getCookieDomain(request):
    if config.wiki_base_domain == 'localhost' or config.wiki_base_domain == '127.0.0.1':
          wiki_domain = ''
    else:
        if config.wiki_farm and request.config.domain:
            # custom domain, so we want to bind to this
            wiki_domain = request.config.domain
            if request.http_host and not request.http_host.endswith(wiki_domain):
                # we are on something like wikiname.basefarmname.org for wikiname that has a custom domain
                s_host = request.http_host.split('.')
                if len(s_host) > 2:
                  s_host = s_host[len(s_host)-2:] 
                wiki_domain = '.'.join(s_host)
                wiki_domain = request.http_host
        else:
            wiki_domain = config.wiki_base_domain
    return wiki_domain


def hasFile(pagename, filename, request):
   """
   Does pagename have filename on it?
   """
   d = {'filename': filename, 'page_name': pagename}
   if wikidb.getFile(request, d):
       return True
   return False

suspect_css_start = '/* suspect CSS: '
def is_suspect_css(css):
    """
    We take the provided string of CSS and check it to ensure it does not contain
    malicious javascript or sneaky ways of inserting malicious javascript.
    """
    from popen2 import popen2
    css_cleaner_location = os.path.join(config.sycamore_dir, "support", "css_cleaner", "css_clean.pl")
    css_cleaner_dependencies = os.path.join(config.sycamore_dir, "support", "css_cleaner")
    r, w = popen2('perl -I%s %s' % (css_cleaner_dependencies, css_cleaner_location))
    w.write(css)
    w.close()
    lines = [ line for line in r ]
    r.close()
    if lines[0].startswith(suspect_css_start):
        return lines[0][len(suspect_css_start):-3] # grab the error given to us by the cleaner
    return False

def sanitize_html(html):
    """
    Strips out bad things from HTML.  Namely, strips out javascript and evil ways of inserting javascript.
    """
    from Sycamore.support.feedparser import _sanitizeHTML
    return _sanitizeHTML(html, 'utf-8')

#############################################################################
### Quoting
#############################################################################
always_file_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '.-')

always_cookie_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '-')
_safemaps = {}

def quoteFilename(filename, always_safe=always_file_safe):
    """
    Return a simple encoding of filename in plain ascii.
    
    @param filename: the original filename, maybe containing non-ascii chars
    @rtype: string
    @return: the quoted filename, all special chars encoded in _XX

    (taken from urllib.quote)
    """
    filename = filename.encode(config.charset)
    safe = ''
    cachekey = (safe, always_safe)
    try:
        safe_map = _safemaps[cachekey]
    except KeyError:
        safe += always_safe
        safe_map = {}
        for i in range(256):
            c = chr(i)
            safe_map[c] = (c in safe) and c or ('_%02X' % i)
        _safemaps[cachekey] = safe_map
    res = map(safe_map.__getitem__, filename)
    return ''.join(res)

def quoteCookiename(name):
    return quoteFilename(name, always_safe=always_cookie_safe)

def unquoteFilename(filename):
    """
    Return decoded original filename when given an encoded filename.
    
    @param filename: encoded filename
    @rtype: string
    @return: decoded, original filename
    """
                                    
    return urllib.unquote(filename.replace('_', '%'))


# XXX UNICODE - see above
def quoteWikiname(filename):
    return quoteFilename(filename).replace('_', '%').replace('%20', '_').replace('%2F', '/').replace('%3A', ':')

def unquoteWikiname(filename):
    return string.strip(unquoteFilename(filename.replace('_', '%20').replace('/','%2F').replace(':', '%3A')))


def escape(s, quote=None):
    """
    Replace special characters '&', '<' and '>' by SGML entities.
    (taken from cgi.escape so we don't have to include that, even if we don't use cgi at all)
    
    @param s: string to escape
    @param quote: if given, transform '\"' to '&quot;'
    @rtype: string
    @return: escaped version of string
    """
    if not s: return u''
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
    return s


#############################################################################
### InterWiki
#############################################################################

_interwiki_list = {}

def split_wiki(wikiurl):
    """
    Split a wiki url.
    
    @param wikiurl: the url to split
    @rtype: tuple
    @return: (tag, tail)
    """
    # !!! use a regex here!
    try:
        wikitag, tail = wikiurl.split(":", 1)
    except ValueError:
        try:
            wikitag, tail = wikiurl.split("/", 1)
        except ValueError:
            wikitag = None
            tail = None

    return (wikitag, tail)


def join_wiki(wikiurl, wikitail):
    """
    Add a page name to an interwiki url.
    
    @param wikiurl: wiki url, maybe including a $PAGE placeholder
    @param wikitail: page name
    @rtype: string
    @return: generated URL of the page in the other wiki
    """
    if wikiurl.find('$PAGE') == -1:
        return wikiurl + wikitail
    else:
        return wikiurl.replace('$PAGE', wikitail)

def format_interwiki_words(words, in_farm=False):
    """
    Does things like remove quotes from interwiki links if need be.

    @param in_farm: if True then we run unquote() on non-"quoted" strings.
    """
    original_words = words
    wikiname = original_words[0].split(':')[1]
    words = ' '.join(words) 
    quotes = words.split('"')
    if len(quotes) > 2:
      pagename = quotes[1]
      quotes[2] = quotes[2][1:] # remove space
      texts = quotes[2:]
      text = '"'.join(texts)
      if not text:
        text = pagename
      wikiurl = 'wiki:%s:%s' % (wikiname, pagename)
      return [wikiurl, text]
    else:
      if in_farm:
        split_words = original_words[0].split(':')
        wikiname = split_words[1]
        pagename = ':'.join(split_words[2:])
        pagename = unquoteWikiname(pagename)
        new_word = 'wiki:%s:%s' % (wikiname, pagename)
        original_words = [new_word] + original_words[1:]

      return original_words

def resolve_wiki(request, wikiurl, force_farm=False):
    """
    Resolve an interwiki link.
    
    @param request: the request object
    @param wikiurl: the InterWiki:PageName link
    @param force_farm: whether or not to force a lookup in our own farm
        (if True, this excludes external interwiki lookups)
    @rtype: tuple
    @return: (wikitag, wikiurl, wikitail, wikitag_bad, wikitype)
    """

    from Sycamore import wikidicts, farm

    _interwiki_list = None
    got_memcache = False

    if request.req_cache['interwiki'].has_key(request.config.wiki_id) and not force_farm:
      _interwiki_list = request.req_cache['interwiki'][request.config.wiki_id]
    else:
      if config.memcache:
        interwiki_dict = request.mc.get('interwiki')
        _interwiki_list = interwiki_dict
        if interwiki_dict is not None: got_memcache = True

    if _interwiki_list is None:
      _interwiki_list = wikidicts.Dict(request.config.interwikimap,request,case_insensitive=True)

    # split wiki url
    wikitag, tail = split_wiki(wikiurl)
    wikitag = wikitag.lower()

    request.req_cache['interwiki'][request.config.wiki_id] = _interwiki_list
    if config.memcache and not got_memcache:
      request.mc.add('interwiki', _interwiki_list)

    # return resolved url
    if wikitag and _interwiki_list.has_key(wikitag) and not force_farm:
        return (wikitag, _interwiki_list[wikitag], tail, False, INTERWIKI_LIST_TYPE)
    else:
        if isInFarm(wikitag, request):
            return (wikitag, farm.getWikiURL(wikitag, request), tail, False, INTERWIKI_FARM_TYPE)
        return (wikitag, request.getScriptname(),'/%s' % quoteWikiname(request.config.interwikimap), True, INTERWIKI_NONE_TYPE)


#############################################################################
### Page types (based on page names)
#############################################################################

#def isEditorBackup(pagename):
#    return pagename.endswith('/MoinEditorBackup')

def isTemplatePage(pagename):
    """
    Is this a template page?
    
    @param pagename: the page name
    @rtype: bool
    @return: true if page is a template page
    """
    lpagename = pagename.lower()
    return lpagename.startswith(config.page_template_prefix.lower()) and not lpagename.endswith('/talk')

def isGroupPage(pagename):
    """
    Is this a group page?
    
    @param pagename: the page name
    @rtype: bool
    @return: true if page is a group page
    """
    global _GROUP_RE
    if _GROUP_RE is None:
        _GROUP_RE = re.compile(config.page_group_regex, re.IGNORECASE)
    return _GROUP_RE.search(pagename) is not None


def filterCategoryPages(pagelist):
    """
    Return a copy of `pagelist` that only contains category pages.

    If you pass a list with a single pagename, either that is returned
    or an empty list, thus you can use this function like a `isCategoryPage`
    one.
       
    @param pagelist: a list of (one or some or all) pages
    @rtype: list
    @return: only the category pages of pagelist
    """
    global _CATEGORY_RE
    if _CATEGORY_RE is None:
        _CATEGORY_RE = re.compile(config.page_category_regex)
    return filter(_CATEGORY_RE.search, pagelist)


#############################################################################
### Page storage helpers
#############################################################################

def getPageList(request, alphabetize=False, objects=False, lowercase=False, wiki_global=False):
    """
    List all pages, except for "CVS" directories,
    hidden files (leading '.') and temp files (leading '#')
    @ param alphabetize: if True then, you know, alphabetize the list 
    @rtype: list
    @return: all (unquoted) wiki page names

    """
    if objects: from Sycamore.Page import Page
    cursor = request.cursor

    if lowercase: type_of_name = 'name'
    else: type_of_name = 'propercased_name'

    if not alphabetize: cursor.execute("SELECT %s from curPages where wiki_id=%%(wiki_id)s" % type_of_name, {'wiki_id':request.config.wiki_id})
    else: cursor.execute("SELECT %s from curPages where wiki_id=%%(wiki_id)s order by name" % type_of_name, {'wiki_id':request.config.wiki_id})
    result = []
    p = cursor.fetchone()
    while p:
      if not objects: result.append(p[0])
      else: result.append(Page(p[0], request))
      p = cursor.fetchone()

    return result

def getPageDict(request):
    """
    Return a dictionary of page objects for all pages,
    with the page name as the key.
       
    @param text_dir: path to "text" directory
    @rtype: dict
    @return: all pages {pagename: Page, ...}
    """
    cursor = request.cursor
    from Sycamore.Page import Page
    pages = {}
    pagenames = getPageList(request)
    for name in pagenames:
        pages[name] = Page(name, request)
    return pages

def getRandomPages(request):
   """
   Returns a list of random pages -- cached.  The maximum number of pages is MAX_RANDOM_GET.
   """
   if request.req_cache['random'].has_key(('*', request.config.wiki_id)):
     return request.req_cache['random'][('*', request.config.wiki_id)]
   rand_pages = None
   if config.memcache:
     rand_pages = request.mc.get('random:*')
   if rand_pages is None: 
     rand_pages = []
     query = "SELECT name from curPages where wiki_id=%%(wiki_id)s order by %s limit %s" % (RAND_FUNCTION, MAX_RANDOM_GET)
     request.cursor.execute(query, {'wiki_id':request.config.wiki_id})
     for item in request.cursor.fetchall(): 
       rand_pages.append(item[0])
     if config.memcache:
       request.mc.add("random:*", rand_pages, time=RAND_EXPIRE_TIME)
   request.req_cache['random'][('*', request.config.wiki_id)] = rand_pages
   return rand_pages


def getBackupList(backup_dir, pagename=None):
    """
    Get a filename list of older versions of the page, sorted by date
    in descending order (last change first).

    @param backup_dir: the path of the "backup" directory
    @param pagename: the (unquoted) page name or None, when all backup
                     versions shall be returned
    @rtype: list
    @return: backup file names (quoted!)
    """
    if os.path.isdir(backup_dir):
        if pagename:
            pagename = quoteFilename(pagename)
        else:
            pagename = ".*?"
        # XXX UNICODE - do we match pagenames in unicode?
        backup_re = re.compile(r'^%s\.\d+(\.\d+)?$' % (pagename,))
        oldversions = []
        for file in os.listdir(backup_dir):
            if not backup_re.match(file): continue
            data = file.split('.', 1)
            oldversions.append(((data[0], float(data[1])), file))
        oldversions.sort()
        oldversions.reverse()

        oldversions = [x[1] for x in oldversions]
    else:
        oldversions = []

    return oldversions


def getSysPage(request, pagename):
    """
    Get a system page according to user settings and available translations.
    
    @param request: the request object
    @param pagename: the name of the page
    @rtype: string
    @return: the (possibly translated) name of that system page
    """
    from Sycamore.Page import Page

    i18n_name = request.getText(pagename)
    if i18n_name != pagename:
        i18n_page = Page(i18n_name)
        if i18n_page.exists():
            return i18n_page
    return Page(pagename, request)


def getHomePage(request, username=None):
    """
    Get a user's homepage, or return None for anon users and
    those who have not created a homepage.
    
    @param request: the request object
    @param username: the user's name
    @rtype: Page
    @return: user's homepage object - or None
    """
    # default to current user
    if username is None and request.user.valid:
        username = request.user.name

    # known user?
    if username:
        from Sycamore.Page import Page

        # plain homepage?
        pg = Page(username, request)
        if pg.exists(): return pg

    return None


def AbsPageName(context, pagename):
    """
    Return the absolute pagename for a (possibly) relative pagename.

    @param context: name of the page where "pagename" appears on
    @param pagename: the (possibly relative) page name
    @rtype: string
    @return: the absolute page name
    """
    if config.allow_subpages:
        if pagename.startswith(PARENT_PREFIX):
            pagename = '/'.join(filter(None, context.split('/')[:-1] + [pagename[3:]]))
        elif pagename.startswith(CHILD_PREFIX):
            pagename = context + pagename

    return pagename


#############################################################################
### Plugins
#############################################################################

def importPlugin(kind, name, function="execute"):
    """
    Returns an object from a plugin module or None if module or 'function' is not found
    kind may be one of 'action', 'formatter', 'macro', 'processor', 'parser'
    or any other directory that exist in Sycamore or data/plugin
    
    @param kind: what kind of module we want to import
    @param name: the name of the module
    @param function: the function name
    @rtype: callable
    @return: "function" of module "name" of kind "kind"
    """
    # First try data/plugins
    result = pysupport.importName("plugin." + kind + "." + name, function)
    if not result:
      # then Sycamore
      result = pysupport.importName("Sycamore." + kind + "." + name, function)
    return result

def builtinPlugins(kind):
    """
    Gets a list of modules in Sycamore.'kind'
    
    @param kind: what kind of modules we look for
    @rtype: list
    @return: module names
    """
    plugins =  pysupport.importName("Sycamore." + kind, "modules")
    if plugins == None:
        return []
    else:
        return plugins

def extensionPlugins(kind):
    """
    Gets a list of modules in data/plugin/'kind'
    
    @param kind: what kind of modules we look for
    @rtype: list
    @return: module names
    """
    plugins =  pysupport.importName("plugin." + kind, "modules")
    if plugins == None:
        return []
    else:
        return plugins


def getPlugins(kind):
    """
    Gets a list of module names.
    
    @param kind: what kind of modules we look for
    @rtype: list
    @return: module names
    """
    builtin_plugins = builtinPlugins(kind)
    extension_plugins = extensionPlugins(kind)[:] # use a copy to not destroy the value
    for module in builtin_plugins:
        if module not in extension_plugins:
            extension_plugins.append(module)
    return extension_plugins

#############################################################################
### Misc
#############################################################################

def parseAttributes(request, attrstring, endtoken=None, extension=None):
    """
    Parse a list of attributes and return a dict plus a possible
    error message.
    If extension is passed, it has to be a callable that returns
    None when it was not interested into the token, '' when all was OK
    and it did eat the token, and any other string to return an error
    message.
    
    @param request: the request object
    @param attrstring: string containing the attributes to be parsed
    @param endtoken: token terminating parsing
    @param extension: extension function -
                      gets called with the current token, the parser and the dict
    @rtype: dict, msg
    @return: a dict plus a possible error message
    """
    import shlex, cStringIO

    _ = request.getText

    parser = shlex.shlex(cStringIO.StringIO(attrstring.encode('utf-8')))
    parser.commenters = ''
    msg = None
    attrs = {}

    while not msg:
        key = parser.get_token()
        if not key: break
        if endtoken and key == endtoken: break

        # call extension function with the current token, the parser, and the dict
        if extension:
            msg = extension(key, parser, attrs)
            if msg == '': continue
            if msg: break

        eq = parser.get_token()
        if eq != "=":
            msg = _('Expected "=" to follow "%(token)s"') % {'token': key}
            break

        val = parser.get_token()
        if not val:
            msg = _('Expected a value for key "%(token)s"') % {'token': key}
            break

        key = escape(key) # make sure nobody cheats

        # safely escape and quote value
        if val[0] in ["'", '"']:
            val = escape(val)
        else:
            val = '"%s"' % escape(val, 1)

        attrs[key.lower()] = val

    return attrs, msg or ''


def taintfilename(basename):
    """
    Make a filename that is supposed to be a plain name secure, i.e.
    remove any possible path components that compromise our system.
    
    @param basename: (possibly unsafe) filename
    @rtype: string
    @return: (safer) filename
    """
    basename = basename.replace(os.pardir, '_')
    basename = basename.replace(':', '_')
    basename = basename.replace('/', '_')
    basename = basename.replace('\\', '_')
    return basename


def mapURL(url):
    """
    Map URLs according to 'config.url_mappings'.
    
    @param url: a URL
    @rtype: string
    @return: mapped URL
    """
    # check whether we have to map URLs
    if config.url_mappings:
        # check URL for the configured prefixes
        for prefix in config.url_mappings.keys():
            if url.startswith(prefix):
                # substitute prefix with replacement value
                return config.url_mappings[prefix] + url[len(prefix):]

    # return unchanged url
    return url


def getUnicodeIndexGroup(name):
    """
    Return a group letter for `name`, which must be a unicode string.
    Currently supported: Hangul Syllables (U+AC00 - U+D7AF)
    
    @param name: a string
    @rtype: string
    @return: group letter or None
    """
    if u'\uAC00' <= name[0] <= u'\uD7AF': # Hangul Syllables
        return unichr(0xac00 + (int(ord(name[0]) - 0xac00) / 588) * 588)
    else:
        return None


def isUnicodeName(name):
    """
    Try to determine if the quoted wikiname is a special, pure unicode name.
    
    @param name: a string
    @rtype: bool
    @return: true if name is a pure unicode name
    """
    # escape name if not escaped
    text = name
    if not name.count('_'):
        text = quoteWikiname(name)

    # check if every character is escaped
    return len(text.replace('_','')) == len(text) * 2/3
    # XXX UNICODE 

def isStrictWikiname(name, word_re=re.compile(r"^(?:[%(u)s][%(l)s]+){2,}$" % {'u':config.upperletters, 'l':config.lowerletters})):
    """
    Check whether this is NOT an extended name.
    
    @param name: the wikiname in question
    @rtype: bool
    @return: true if name matches the word_re
    """
    return word_re.match(name)


def isPicture(url):
    """
    Is this a picture's url?
    
    @param url: the url in question
    @rtype: bool
    @return: true if url points to a picture
    """
    extpos = url.rfind(".")
    return extpos > 0 and url[extpos:].lower() in ['.gif', '.jpg', '.jpeg', '.png']

def attach_link_tag(request, params, text=None, formatter=None, **kw):
    """
    Create a link.

    @param request: the request object
    @param params: parameter string appended to the URL after the scriptname/
    @param text: text / inner part of the <a>...</a> link
    @param formatter: the formatter object to use
    @keyword attrs: additional attrs (HTMLified string)
    @rtype: string
    @return: formatted link tag
    """
    css_class = kw.get('css_class', None)
    if text is None:
        text = params # default
    if formatter:
        if kw.has_key('absolute'):
            return formatter.url("%s/%s" % (farm.getWikiURL(request.config.wiki_name, request), params), text, css_class, **kw)
        else:
            return formatter.url("%s/%s" % (request.getScriptname(), params), text, css_class, **kw)

    attrs = []
    if kw.has_key('attrs'):
        attrs.append(' %s' % kw['attrs'])
    if css_class:
        attrs.append(' class="%s"' % css_class)
    return ('<a%s class="nonexistent" onclick="%s%s/%s%s">%s</a>' % (''.join(attrs), "window.open('", request.getScriptname(), params, "', 'attachments', 'width=800,height=600,scrollbars=1');", text))

def link_tag(request, params, text=None, formatter=None, **kw):
    """
    Create a link.

    @param request: the request object
    @param params: parameter string appended to the URL after the scriptname/
    @param text: text / inner part of the <a>...</a> link
    @param formatter: the formatter object to use
    @keyword attrs: additional attrs (HTMLified string)
    @keyword absolute: render absolute url
    @rtype: string
    @return: formatted link tag
    """
    from Sycamore import farm
    css_class = kw.get('css_class', None)
    if text is None:
        text = params # default
    if formatter:
        if kw.has_key('absolute'):
            return formatter.url("%s%s" % (farm.getWikiURL(request.config.wiki_name, request), params), text, css_class, **kw)
        else:
            return formatter.url("%s/%s" % (request.getScriptname(), params), text, css_class, **kw)
    attrs = []
    if kw.has_key('attrs'):
        attrs.append(' %s' % kw['attrs'])
    if css_class:
        attrs.append(' class="%s"' % css_class)
    if kw.has_key('absolute'):
        return ('<a%s href="%s%s">%s</a>' % (''.join(attrs), farm.getWikiURL(request.config.wiki_name, request), params, text))
    else:
        return ('<a%s href="%s/%s">%s</a>' % (''.join(attrs), request.getScriptname(), params, text))
    
def link_tag_explicit(inbetween, request, params, text=None, formatter=None, **kw):
    """
    Create a link.
    But let me tell it what i want between the 'a' and the 'href'!

    @param request: the request object
    @param params: parameter string appended to the URL after the scriptname/
    @param text: text / inner part of the <a>...</a> link
    @param formatter: the formatter object to use
    @keyword attrs: additional attrs (HTMLified string)
    @rtype: string
    @return: formatted link tag
    """
    css_class = kw.get('css_class', None)
    if text is None:
        text = params # default
    if formatter:
        return formatter.url("%s/%s" % (request.getScriptname(), params), text, css_class, **kw)
    attrs = []
    if kw.has_key('attrs'):
        attrs.append(' %s' % kw['attrs'])
    if css_class:
        attrs.append(' class="%s"' % css_class)
    return ('<a%s %s href="%s/%s">%s</a>' % (''.join(attrs), inbetween, request.getScriptname(), params, text))



def linediff(oldlines, newlines, **kw):
    """
    Find changes between oldlines and newlines.
    
    @param oldlines: list of old text lines
    @param newlines: list of new text lines
    @keyword ignorews: if 1: ignore whitespace
    @rtype: list
    @return: lines like diff tool does output.
    """
    false = lambda s: None 
    if kw.get('ignorews', 0):
        d = difflib.Differ(false)
    else:
        d = difflib.Differ(false, false)

    lines = list(d.compare(oldlines,newlines))
 
    # return empty list if there were no changes
    changed = 0
    for l in lines:
        if l[0] != ' ':
            changed = 1
            break
    if not changed: return []

    if not "we want the unchanged lines, too":
        if "no questionmark lines":
            lines = filter(lambda line : line[0]!='?', lines)
        return lines


    # calculate the hunks and remove the unchanged lines between them
    i = 0              # actual index in lines
    count = 0          # number of unchanged lines
    lcount_old = 0     # line count old file
    lcount_new = 0     # line count new file
    while i < len(lines):
        marker = lines[i][0]
        if marker == ' ':
            count = count + 1
            i = i + 1
            lcount_old = lcount_old + 1
            lcount_new = lcount_new + 1
        elif marker in ['-', '+']:
            if (count == i) and count > 3:
                lines[:i-3] = []
                i = 4
                count = 0
            elif count > 6:
                # remove lines and insert new hunk indicator
                lines[i-count+3:i-3] = ['@@ -%i, +%i @@\n' %
                                        (lcount_old, lcount_new)]
                i = i - count + 8
                count = 0
            else:
                count = 0
                i = i + 1                            
            if marker == '-': lcount_old = lcount_old + 1
            else: lcount_new = lcount_new + 1
        elif marker == '?':
            lines[i:i+1] = []

    # remove unchanged lines a the end
    if count > 3:
        lines[-count+3:] = []
    
    return lines


def pagediff(page1, page2, **kw):
    """
    Calculate the "diff" between `page1` and `page2`.

    @param page1: first page
    @param page2: second page
    @keyword ignorews: if 1: ignore pure-whitespace changes.
    @rtype: tuple
    @return: (diff return code, page file name,
             backup page file name, list of lines of diff output)
    """
    lines1 = None
    lines2 = None
    # XXX UNICODE fix needed, decode from config.charset
    try:
        fd = open(page1)
        lines1 = fd.readlines()
        fd.close()
    except IOError: # Page was deleted?
        lines1 = None
    try:
        fd = open(page2)
        lines2 = fd.readlines()
        fd.close()
    except IOError: # Page was deleted?
        lines2 = None

    if lines1 == None or lines2 == None:
        return -1, page1, page2, []
    
    lines = linediff(lines1,lines2,**kw)
    return 0, page1, page2, lines
 

#############################################################################
### Page header / footer
#############################################################################

def simple_send_title(request, pagename, msg='', strict_title=''):
   """
   requires only pagename and request object and prepares the usual page title.
   """
   page_needle = pagename
   if config.allow_subpages and page_needle.count('/'):
     page_needle = '/' + page_needle.split('/')[-1]
   has_link = True

   send_title(request, pagename, pagename=pagename, has_link=has_link, msg=msg, strict_title=strict_title)


def send_title(request, text, **keywords):
    """
    Output the page header (and title).
    
    @param request: the request object
    @param text: the title text, in general
    @keyword link: URL for the title
    @keyword msg: additional message (after saving)
    @keyword pagename: 'PageName'
    @keyword print_mode: 1 (or 0)
    @keyword allow_doubleclick: 1 (or 0)
    @keyword html_head: additional <head> code
    @keyword body_attr: additional <body> attributes
    @keyword body_onload: additional "onload" JavaScript code
    @keyword strict_title: _just_ the html <title> specified
    """
    from Sycamore import i18n, farm
    from Sycamore.Page import Page
    from Sycamore.action.Files import getAttachUrl

    _ = request.getText
    pagename = keywords.get('pagename', '')
    page = Page(pagename, request)

    # Print the HTML <head> element
    user_head = [config.html_head] + request.html_head
    
    # search engine precautions / optimization:
    # if it is an action or edit/search, send query headers (noindex,nofollow):
    crawl = True # by default, we want search engines to crawl us
    if request.query_string:
        crawl = False
        if request.query_string == 'action=show':
          crawl = True
        elif request.form.has_key('action'):
          # index the files attached to pages
          if request.form['action'][0] == 'Files':
            if request.form.has_key('do'):
              if request.form['do'][0] == 'view':
                crawl = True

    user_head.append("""<meta http-equiv="Content-Type" content="text/html; charset=%s">\n""" % config.charset)

    if request.config.noindex_everywhere:
        user_head.append("""<meta name="robots" content="noindex,nofollow">\n""")
    elif (not crawl) or (request.request_method == 'POST') or not request.user.may.read(page):
        user_head.append("""<meta name="robots" content="noindex,nofollow">\n""")
    elif not page.exists():
        user_head.append("""<meta name="robots" content="noindex,nofollow">\n""")
    # if it is a special page, index it and follow the links:
    elif pagename in ['Front Page', 'Title Index',]:
        user_head.append("""<meta name="robots" content="index,follow">\n""")
    # if it is a normal page, index it, but do not follow the links, because
    else:
        user_head.append("""<meta name="robots" content="index,follow">\n""")

    # do we show an icon for the wiki?
    tiny_logo_url = None
    image_pagename = '%s/%s' % (config.wiki_settings_page, config.wiki_settings_page_images)
    if hasFile(image_pagename, 'tinylogo.png', request):
        tiny_logo_url = getAttachUrl(image_pagename, 'tinylogo.png', request)
    else:
        if config.wiki_farm:
            on_wiki = request.config.wiki_name
            request.switch_wiki(farm.getBaseWikiName(request))
            if hasFile(image_pagename, 'tinylogo.png', request):
                tiny_logo_url = getAttachUrl(image_pagename, 'tinylogo.png', request)
            request.switch_wiki(on_wiki)

    if tiny_logo_url:
        user_head.append("""<link rel="shortcut icon" href="%s" type="image/png">
<link rel="icon" href="%s" type="image/png">""" % (tiny_logo_url, tiny_logo_url))
        
    if keywords.has_key('pi_refresh') and keywords['pi_refresh']:
        user_head.append('<meta http-equiv="refresh" content="%(delay)d;URL=%(url)s">' % keywords['pi_refresh'])

    # global javascript variable needed by edit.js
    user_head.append("""<script type="text/javascript">var urlPrefix = '%s';</script>""" % (config.url_prefix))

    if keywords.has_key('strict_title') and keywords['strict_title']: strict_title = keywords['strict_title']
    else: strict_title = text

    # add the rss link for per-page rss
    lower_pagename = pagename.lower()

    if lower_pagename == 'bookmarks' or lower_pagename == 'interwiki bookmarks':
      rss_html = ''
    else: 
      if lower_pagename == 'recent changes':
        rss_html = '<link rel=alternate type="application/rss+xml" href="%s/%s?action=rss_rc" title="Recent Changes RSS Feed">' % (request.getScriptname(), quoteWikiname(pagename))
      elif lower_pagename == 'interwiki recent changes':
        rss_html = '<link rel=alternate type="application/rss+xml" href="%s/%s?action=rss_rc&amp;user=%s" title="Interwiki Recent Changes RSS Feed for %s">' % (request.getScriptname(), quoteWikiname(pagename), request.user.name, request.user.propercased_name)
      else:
        rss_html = '<link rel=alternate type="application/rss+xml" href="%s/%s?action=rss_rc" title="Recent Changes RSS Feed for %s">' % (request.getScriptname(), quoteWikiname(pagename), pagename)

    request.write("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
%s
%s
%s
%s
""" % (
        ''.join(user_head),
        keywords.get('html_head', ''),
        rss_html,
        request.theme.html_head({
            'title': escape(strict_title),
            'sitename': escape(config.html_pagetitle or request.config.sitename),
            'print_mode': keywords.get('print_mode', False),
            'page': page
        })
    ))

    request.write("</head>\n")

    # start the <body>
    bodyattr = []

    if keywords.has_key('body_attr'):
        bodyattr.append(' %s' % keywords['body_attr'])
    if keywords.get('allow_doubleclick', 0) and not keywords.get('print_mode', 0) \
            and pagename and request.user.may.edit(page) \
            and request.user.edit_on_doubleclick:
        bodyattr.append(''' ondblclick="location.href='%s'"''' % (
            page.url("action=edit")))

    # Set body to the user interface language and direction
    bodyattr.append(' %s' % request.theme.ui_lang_attr())
    
    body_onload = keywords.get('body_onload', '')
    if body_onload:
        bodyattr.append(''' onload="%s"''' % body_onload)
    request.write('\n<body %s>\n' % ''.join(bodyattr))

    # if the wiki is disabled then we print out a message telling them so
    if request.config.is_disabled:
        request.write('<div style="border: 1px solid gray; margin: 1em; padding: 1em; background-color: #ffff99;">This wiki is <strong>marked as deleted</strong> and will be erased permanently in no more than 30 days.  If you made a mistake deleting this wiki, immediately un-check the "delete this wiki" check box at %s.</div>' % 
            Page('%s/%s' % (config.wiki_settings_page, config.wiki_settings_page_general), request).link_to())

    # if in Print mode, emit the title and return immediately
    if keywords.get('print_mode', 0):
        ## print '<h1>%s</h1><hr>\n' % (escape(text),)
        return

    form = keywords.get('form', None)
    icon = request.theme.get_icon('searchbutton')
    searchfield = (
        '<input class="formfields" type="text" name="inline_string" value="%%(value)s" size="15" maxlength="50">'
        '&nbsp;<input type="image" src="%(src)s" alt="%(alt)s">'
        ) % {
            'alt': icon[0],
            'src': icon[1],
        }
    textsearch = searchfield %  {
        'type': 'normal',
        'value': escape(form and form.get('search', [''])[0] or '', 1),
    }

    # prepare dict for theme code:
    d = {
        'theme': request.theme.name,
        'script_name': request.getScriptname(),
        'title_text': text,
        'title_link': keywords.get('has_link', ''),
        'script_name': request.getScriptname(),
        'site_name': config.sitename,
        'page': page,             # necessary???
        'page_name': page.proper_name(),
        'lower_page_name': page.page_name.lower(),
        'page_user_prefs': config.page_user_preferences,
        'polite_msg': keywords.get('polite_msg', ''),
        'user_name': request.user.name,
        'user_valid': request.user.valid,
        'msg': keywords.get('msg', ''),
        'trail': keywords.get('trail', None),
        'textsearch': textsearch,
    }

    # add quoted versions of pagenames
    newdict = {}
    for key in d:
        if key.startswith('page_'):
            if d[key]:
                newdict['q_'+key] = quoteWikiname(d[key])
            else:
                newdict['q_'+key] = ''
    d.update(newdict)

    request.themedict = d # remember it for footer

    # now call the theming code to do the rendering
    request.write(request.theme.header(d))

def send_after_content(request):
    """
    Called after content is sent but before the footer is sent.
    """
    request.write(request.theme.after_content())
    

def send_footer(request, pagename, **keywords):
    """
    Output the page footer.

    @param request: the request object
    @param pagename: WikiName of the page
    @keyword editable: true, when page is editable (default: true)
    @keyword showpage: true, when link back to page is wanted (default: false)
    @keyword print_mode: true, when page is displayed in Print mode
    """
    d = request.themedict # prepared in send_header function
    d.update({
        'footer_fragments': request._footer_fragments,
    })
    # I guess this is probably the best place for this now
    #request.user.checkFavorites(d['page_name'])

    request.write('\n\n') # the content does not always end with a newline
    request.write(request.theme.footer(d, **keywords))

