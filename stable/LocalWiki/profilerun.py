 import re, time
from LocalWiki import action, config, macro, util
from LocalWiki import version, wikiutil, wikiaction, i18n
from LocalWiki.Page import Page
from LocalWiki.util import pysupport
from LocalWiki.logfile import editlog, eventlog

   
def _macro_WordIndex(self, args):
        index_letters = []
        s = ''
        pages = list(wikiutil.getPageList(config.text_dir))
        pages = filter(self.request.user.may.read, pages)
        map = {}
        # XXX UNICODE re.UNICODE ?
        word_re = re.compile('[%s][%s]+' % (config.upperletters, config.lowerletters))
         for word in all_words:
            # XXX UNICODE - sense????
            if wikiutil.isUnicodeName(word): continue

            letter = word[0]
            if letter <> last_letter:
                #html.append(self.formatter.anchordef()) # XXX no text param available!
                html.append('<a name="%s">\n<h3>%s</h3>\n' % (wikiutil.quoteWikiname(letter), letter))
                last_letter = letter
            if letter not in index_letters:
                index_letters.append(letter)

            html.append(self.formatter.strong(1))
            html.append(word)
            html.append(self.formatter.strong(0))
            html.append(self.formatter.bullet_list(1))
            links = map[word]
            links.sort()
            last_page = None
            for name in links:
                if name == last_page: continue
                html.append(self.formatter.listitem(1))
                html.append(Page(name).link_to(self.request))
                html.append(self.formatter.listitem(0))
            html.append(self.formatter.bullet_list(0))
        return '%s%s' % (_make_index_key(index_letters), ''.join(html))


