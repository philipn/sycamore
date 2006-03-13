# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Internationalization

    This subpackage controls the access to the language modules
    contained in it. Each language is in a module with a dictionary
    storing the original texts as keys and their translation in the
    values. Other supporting modules start with an underscore.

    Public attributes:
    languages -- languages that Sycamore knows about
    NAME, ENCODING, DIRECTION, MAINTAINER -- named indexes

    Public functions:
    charset() -- return the charset of this source
    filename(lang) -- return the filename of lang
    loadLanguage(request, lang) -- load text dictionary for a specific language
    requestLanguage(request, usecache=1) -- return the request language
    wikiLanguages() -- return the available wiki user languages
    browserLanguages() -- return the browser accepted languages
    getDirection(lang) -- return the lang direction either 'ltr' or 'rtl'
    getText(str, request) -- return str translation
    canRecode(input, output, strict) -- check recode ability
    recode(text, input, output, errors) -- change text encoding
    
    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import config

NAME, ENCODING, DIRECTION, MAINTAINER = range(0,4)
# we do not generate this on the fly due to performance reasons -
# importing N languages would be slow for CGI...
from meta import languages

# This is a global for a reason: in persistent environments all
# languages in use will be cached; Note: you have to restart if you
# update language data in such environments.  
_text_cache = {}

def charset():
    """
    Return the charset of meta.py file

    Since the language data there is encoded, clients might want to recode the data.

    """
    return 'iso-8859-1'

def filename(lang):
    """
    Return the filename for lang

    This is not always the same as the language name. This function hides
    the naming details from the clients.
    """
    filename = lang.replace('-', '_')
    filename = filename.lower()
    return filename
   
def loadLanguage(request, lang):
    """
    Load text dictionary for a specific language.

    Note that while ISO language coded use a dash, like 'en-us', our
    languages files use '_' like 'en_us' because they are saved as
    Python source files.

    """
    from Sycamore.util import pysupport
    lang_module = "Sycamore.i18n." + filename(lang)
    texts = pysupport.importName(lang_module, "text") 
    meta = pysupport.importName(lang_module, "meta") 

    # FIXME this doesnt work, leads to &amp;amp;amp;...
    # maybe parser.wiki._do_ent_repl is the problem?
    
    # please help finding this bug. I want to get rid of html in i18n texts
    # and a nice way to do is to replace them by wiki markup. so we wont have
    # to change them every time we go to a new html standard (like html 4.01
    # now and soon maybe xhtml).
    
    # use the wiki parser now to replace some wiki markup with html
    # maybe this is the better implementation, less overhead
    if 0:
        from Sycamore.Page import Page
        from Sycamore.parser.wiki import Parser
        from Sycamore.formatter.text_html import Formatter
        import cStringIO
        for key in texts:
            text = texts[key]
            out = cStringIO.StringIO()
            request.redirect(out)
            print "making parser ..."
            parser = Parser(text, request)
            formatter = Formatter(request)
            p = Page("$$$$i18n$$$$")
            formatter.setPage(p)
            print "formatting ..."
            parser.format(formatter)
            print "formatting finished ..."
            text = out.getvalue()
            request.redirect()
            #if text.startswith("<p>\n"):
            #    text = text[4:]
            #if text.endswith("</p>\n"):
            #    text = text[:-5]
            #print text
            
            # XXX catch problem early:
            if "&amp;amp;" in text:
                raise str(key)+str(text)
            
            texts[key] = text
        
    #alternative implementation, also doesnt work:
    if 0:
        import cStringIO
        from Sycamore.Page import Page
        page = Page("$$$i18n$$$")
        #key = "xxx"
        for key in texts:
            text = texts[key]
            page.set_raw_body(text, 1)
            out = cStringIO.StringIO()
            request.redirect(out)
            page.send_page(request, content_only=1)
            text = out.getvalue()
            if text.startswith("<p>\n"):
                text = text[4:]
            if text.endswith("</p>\n"):
                text = text[:-5]
            #print text
            request.redirect()
            texts[key] = text
        
    # TODO caching for CGI or performance will suck
    # pickle texts dict to caching area

    # XXX UNICODE
    # convert to unicode
    #encoding = meta['encoding']
    #for t in texts:
    #    texts[t] = texts[t].decode(encoding)
    return texts


def requestLanguage(request):
    """ 
    Return the user interface language for this request.
    
    The user interface language is taken from the user preferences for
    registered users, or request environment, or the default language of
    the wiki, or English.

    This should be called once per request, then you should get the
    value from request object lang attribute.
    
    Unclear what this means: "Until the code for get
    text is fixed, we are caching the request language locally."

    @param request: the request object
    @keyword usecache: whether to get the value form the local cache or
                       actually look for it. This will update the cache data.
    @rtype: string
    @return: ISO language code, e.g. 'en'
    """

    # Return the user language preferences for registered users
    if request.user.valid and request.user.language:
        return request.user.language

    if config.default_lang:
      return config.default_lang

    # Or try to return one of the user browser accepted languages, if it
    # is available on this wiki...
    available = wikiLanguages()
    for lang in browserLanguages(request):
        if available.has_key(lang):
            return lang
    
    # Or return the wiki default language...
    if available.has_key(config.default_lang):
        lang = config.default_lang

    # If eveything else fails, read the manual... or return 'en'
    else:
        lang = 'en'

    return lang


def wikiLanguages():
    """
    Return the available user languages in this wiki.

    Since the wiki has only one charset set by the admin, and the user
    interface files could have another charset, not all languages are
    available on every wiki - unless we move to Unicode for all
    languages translations. Even then, Python still can't recode some
    charsets.

    !!! Note: we use strict = 1 to choose only language that we can
    recode strictly from the language encodings to the wiki
    encoding. This preference could be left to the wiki admin instead.

    Return a dict containing a subset of Sycamore languages ISO codes.
    """
    
    available = {}
    for lang in languages.keys():
        encoding = languages[lang][ENCODING].lower()
        if (lang == 'en' or
            encoding == config.charset or
            canRecode(encoding, config.charset, strict=1)):
            available[lang] = languages[lang]
        
    return available


def browserLanguages(request):
    """
    Return the accepted languages as set in the user browser.
    
    Parse the HTTP headers and extract the accepted languages,
    according to
    http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.4

    Return a list of languages and base languages - as they are
    specified in the request, normalizing to lower case.
    """
    
    fallback = []
    
    accepted = request.http_accept_language
    if accepted:
        # Extract the languages names from the string
        accepted = accepted.split(',')
        accepted = map(lambda x: x.split(';')[0], accepted)
    
        # Add base language for each sub language. If the user specified
        # a sub language like "en-us", we will try to to provide it or
        # a least the base language "en" in this case.
        for lang in accepted:
            lang = lang.lower()
            fallback.append(lang)
            if '-' in lang:
                baselang = lang.split('-')[0]
                fallback.append(baselang)
        
    return fallback


def getDirection(lang):
    """Return the text direction for a language, either 'ltr' or 'rtl'."""
    return ('ltr', 'rtl')[languages[lang][DIRECTION]]


def getText(str, request, lang):
    """
    Return a translation of text in the user's language.

    TODO: Should move this into a language instance. request.lang
    should be a language instance.
    
    """
    # quick handling for english texts - no recoding needed!
    if lang == "en": return str
    
    # load texts if needed
    global _text_cache
    if not _text_cache.has_key(lang):
        texts = loadLanguage(request, lang)
        if not texts:
            # Return english text in case of problems
            # ??? Do we really need to recode from ascii? we don't need
            # this for utf-8 wikis, but what about chinese wiki? 
            return recode(str, 'ascii', config.charset) or str
            # XXX UNICODE fix needed, we want to use unicode internally, not
            # config.charset or utf-8
            
        _text_cache[lang] = texts

    # get the matching entry in the mapping table
    translation = _text_cache[lang].get(str, None)
    if translation is None:
        return recode(str, 'ascii', config.charset) or str
        # XXX UNICODE fix needed, we want to use unicode internally, not
        # config.charset or utf-8

    encoding = languages[lang][ENCODING]
    return recode(translation, encoding, config.charset) or translation
    # XXX UNICODE fix needed. We dont want utf-8 internally, we want unicode strings!
    # Later (on output), we will encode it again to whatever needed (including utf-8).

########################################################################
# Encoding
########################################################################

def canRecode(input, output, strict=1):
    """
    Check if we can recode text from input to output.

    Return 1 if we can probablly recode from one charset to
    another, or 0 if the charset are not known or compatible.

    arguments:
    input -- the input encoding codec name or alias
    output -- the output encoding codec name or alias
    strict -- Are you going to recode using errors='strict' or you can
    get with 'ignore', 'replace' or other error levels?
    """

    import codecs

    # First normalize case - our client could have funny ideas about case
    input = input.lower()
    output = output.lower()

    # Check for known encodings
    try:
        encoder = codecs.getencoder(output)
        decoder = codecs.getdecoder(input)          
    except LookupError:
        # Unknown encoding - forget about it!
        return 0
    
    # We assume that any charset that Python knows about, can be recoded
    # into any Unicode charset. Because codecs have many aliases, we
    # check the codec name itself
    if encoder.__name__.startswith('utf'):
        # This is a unicode encoding, so input could be anything.
        return 1

    # We know both encodings but we don't know if we can actually recode
    # any text from one to another. For example, we can recode from
    # iso-8859-8 to cp1255, because the first is a subset of the last,
    # but not the other way around.
    # We choose our answer according to the strict keyword argument
    if strict:
        # We are not sure, so NO
        return 0
    else:
        # Probably you can recode using 'replace' or 'ignore' or other
        # encodings error level and be happy with the results, so YES
        return 1
    
# XXX UNICODE this is maybe not needed if we use unicode strings internally.
# TODO check that...
def recode(text, input, output, errors='strict'):
    """
    Recode string from input to output encoding

    Return the recoded text or None if it can not be recoded

    """

    # Don't try to encode already encoded. 
    if input == output: return text

    try:
        # Decode text unless it is a unicode string, then encode
        if not isinstance(text, type(u'')):
            text = unicode(text, input, errors)
        return text.encode(output, errors)
        
    except (ValueError, UnicodeError, LookupError):
        # Unkown encodings or encoding failure 
        return None
            

