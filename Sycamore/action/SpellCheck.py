# -*- coding: iso-8859-1 -*-
"""  
    Sycamore - Spelling Action
     
    Word adding based on code by Christian Bird <chris.bird@lineo.com> 

    This action checks for spelling errors in a page using one or several
    word lists.

    Sycamore looks for dictionary files in the directory "dict" within the
    Sycamore package directory. To load the default UNIX word files, you
    have to manually create symbolic links to those files (usually
    '/usr/dict/words' or '/usr/share/dict/words').

    Additionally, all words on the page "LocalSpellingWords" are added to
    the list of valid words, if that page exists.

    @copyright: 2001 by Richard Jones <richard@bizarsoftware.com.au>  
    @copyright: 2001, 2002 by Jürgen Hermann <jh@web.de>  
    @license: GNU GPL, see COPYING for details.  
"""

# Imports
import os, re
from Sycamore import config, wikiutil
from Sycamore.Page import Page


# Functions
def _getWordsFiles():
    """Check a list of possible word files"""
    candidates = []

    # load a list of possible word files
    localdict = os.path.join(config.moinmoin_dir, 'dict')
    if os.path.isdir(localdict):
        candidates.extend(map(
            lambda f, d=localdict: os.path.join(d, f), os.listdir(localdict)))

    # validate candidate list (leave out directories!)
    wordsfiles = []
    for file in candidates:
        if os.path.isfile(file) and os.access(file, os.F_OK | os.R_OK):
            wordsfiles.append(file)

    # return validated file list
    return wordsfiles


def _loadWordsFile(request, dict, filename):
    #request.clock.start('spellread')
    # XXX UNICODE fix needed. the dictionaries should be encoded in config.charset.
    # if they are not, we can recode them before use.
    file = open(filename, 'rt')
    try:
        while 1:
            lines = file.readlines(32768)
            if not lines: break
            for line in lines:
                words = line.split()
                for word in words: dict[word] = ''
    finally:
        file.close()
    #request.clock.stop('spellread')


def _loadDict(request):
    """ Load words from words files or cached dict """
    # check for "dbhash" module
    try:
        import dbhash
    except ImportError:
        dbhash = None

    # load the words
    cachename = os.path.join(config.data_dir, 'dict.cache')
    if dbhash and os.path.exists(cachename):
        wordsdict = dbhash.open(cachename, "r")
    else:
        #request.clock.start('dict.cache')
        wordsfiles = _getWordsFiles()
        if dbhash:
            wordsdict = dbhash.open(cachename, 'n', 0666 & config.umask)
        else:
            wordsdict = {}

        for wordsfile in wordsfiles:
            _loadWordsFile(request, wordsdict, wordsfile)

        if dbhash: wordsdict.sync()
        #request.clock.stop('dict.cache')

    return wordsdict


def _addLocalWords(request):
    import types
    from Sycamore.PageEditor import PageEditor

    # get the new words as a string (if any are marked at all)
    try:
        newwords = request.form['newwords']
    except KeyError:
        # no new words checked
        return
    newwords = ' '.join(newwords)

    # get the page contents
    lsw_page = PageEditor(config.page_local_spelling_words, request)
    words = lsw_page.get_raw_body()

    # add the words to the page and save it
    if words and words[-1] != '\n':
        words = words + '\n'
    lsw_page.saveText(words + '\n' + newwords, '0')


def checkSpelling(page, request, own_form=1):
    """ Do spell checking, return a tuple with the result.
    """
    _ = request.getText

    # first check to see if we we're called with a "newwords" parameter
    if request.form.has_key('button_newwords'): _addLocalWords(request)

    # load words
    wordsdict = _loadDict(request)

    localwords = {}
    lsw_page = Page(config.page_local_spelling_words, request)
    if lsw_page.exists(): _loadWordsFile(request, localwords, lsw_page._text_filename())

    # init status vars & load page
    #request.clock.start('spellcheck')
    badwords = {}
    text = page.get_raw_body()

    # checker regex and matching substitute function
    word_re = re.compile(r'([%s]?[%s]+)' % (
        config.upperletters, config.lowerletters))

    def checkword(match, wordsdict=wordsdict, badwords=badwords,
            localwords=localwords, num_re=re.compile(r'^\d+$')):
        word = match.group(1)
        if len(word) == 1:
            return ""
        if not (wordsdict.has_key(word) or
                wordsdict.has_key(word.lower()) or
                localwords.has_key(word) or
                localwords.has_key(word.lower()) ):
            if not num_re.match(word):
                badwords[word] = 1
        return ""

    # do the checking
    for line in text.split('\n'):
        if line == '' or line[0] == '#': continue
        word_re.sub(checkword, line)

    if badwords:
        badwords = badwords.keys()
        badwords.sort(lambda x,y: cmp(x.lower(), y.lower()))

        # build regex recognizing the bad words
        badwords_re = r'(^|(?<!\w))(%s)(?!\w)'
        badwords_re = badwords_re % ("|".join(map(re.escape, badwords)),)
        # XXX UNICODE re.UNICODE !?
        badwords_re = re.compile(badwords_re)

        lsw_msg = ''
        if localwords:
            lsw_msg = ' ' + _('(including %(localwords)d %(pagelink)s)') % {
                'localwords': len(localwords), 'pagelink': lsw_page.link_to(request)}
        msg = _('The following %(badwords)d words could not be found in the dictionary of '
                '%(totalwords)d words%(localwords)s and are highlighted below:') % {
            'badwords': len(badwords),
            'totalwords': len(wordsdict)+len(localwords),
            'localwords': lsw_msg} + "<br>"

        # figure out what this action is called
        action_name = os.path.splitext(os.path.basename(__file__))[0]

        # add a form containing the bad words
        if own_form:
            msg = msg + (
                '<form method="POST" action="%s">'
                '<input type="hidden" name="action" value="%s">'
                % (page.url(request), action_name,))
        checkbox = '<input type="checkbox" name="newwords" value="%(word)s">%(word)s&nbsp;&nbsp;'
        msg = msg + (
            " ".join(map(lambda w, cb=checkbox: cb % {'word': wikiutil.escape(w),}, badwords)) +
            '<p><input type="submit" name="button_newwords" value="%s"></p>' %
                _('Add checked words to dictionary')
        )
        if own_form:
            msg = msg + '</form>'
    else:
        badwords_re = None
        msg = _("No spelling errors found!")

    #request.clock.stop('spellcheck')

    return badwords, badwords_re, msg


def execute(pagename, request):
    _ = request.getText
    page = Page(pagename, request.cursor)
    if request.user.may.read(pagename):
        badwords, badwords_re, msg = checkSpelling(page, request)
    else:
        badwords = []
        msg = _("You can't check spelling on a page you can't read.")

    if badwords:
        page.send_page(request, msg=msg, hilite_re=badwords_re)
    else:
        page.send_page(request, msg=msg)

