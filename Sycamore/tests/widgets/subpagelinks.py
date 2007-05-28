import sys, os, unittest, random
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..'))])
import __init__

from basics import RequestBasics

from Sycamore import request, config, wikiutil
from Sycamore.widget import subpagelinks
_did_rollback = False

def make_random_string(length, alphanum_only=True):
  import random, string
  chars = string.letters + string.digits # not everything, but good nuff for now
  rand_char_loc = random.randint(0, len(chars)-1)
  random_string = ''
  for j in xrange(0, random.randint(0, length)):
      random_string += random.choice(chars)
  return random_string


def make_impossible_pages(request, numpages, max_length):
    """
    Make a list of numpages pagenames that can't exist (aren't in the list of all pages).
    """
    import random
    all_pages = [ pagename.lower() for pagename in wikiutil.getPageList(request) ]
    impossible = []
    for i in xrange(0, numpages):
       random_string = None
       random_string_lower = None
       while random_string_lower not in all_pages and random_string is None:
          random_string = make_random_string(max_length)
          random_string_lower = random_string.lower()
       impossible.append(random_string)
    return impossible


class SubPageDisplayTest(RequestBasics):
    """
    We assume, in this test, that the basic pages exist in the wiki.
    """
    args_and_values = [
        #([(u'Templates', u'Templates'), (u'Templates/Test/Talk', u'Test/Talk')]),
        (u'Front Page', [(u'Front Page', u'Front Page')]),
        (u'Front Page/Talk', [(u'Front Page', u'Front Page'), (u'Front Page/Talk', u'Talk')]),
        (u'Templates', [(u'Templates', u'Templates')]),
        (u'Templates/Business', [(u'Templates', u'Templates'), (u'Templates/Business', u'Business')]),
        (u'Templates/Business/Talk', [(u'Templates', u'Templates'), (u'Templates/Business', u'Business'), (u'Templates/Business/Talk', 'Talk')]),
        ]

    def testSubpageRender(self):
        """Tests the subpage display splitting"""
        # prep work -- make new tests
        impossible_pagenames = make_impossible_pages(self.request, 20, 40)
        for pagename in impossible_pagenames:
            self.args_and_values.append(((pagename), ([(pagename, pagename)])))
        for pagename in impossible_pagenames:
            self.args_and_values.append((('Front Page/%s' % pagename), ([('Front Page', 'Front Page'), ('Front Page/%s' % pagename, pagename)])))
        for pagename in impossible_pagenames:
            self.args_and_values.append((('Front Page/%s/Talk' % pagename), ([('Front Page', 'Front Page'), ('Front Page/%s/Talk' % pagename, '%s/Talk' % pagename)])))
        for pagename in impossible_pagenames:
            self.args_and_values.append((('Templates/Business/%s' % pagename), ([('Templates', 'Templates'), ('Templates/Business', 'Business'), ('Templates/Business/%s' % pagename, pagename)])))
        for pagename in impossible_pagenames:
            self.args_and_values.append((('Templates/Business/%s/Talk' % pagename), ([('Templates', 'Templates'), ('Templates/Business', 'Business'), ('Templates/Business/%s/Talk' % pagename, '%s/Talk' % pagename)])))

        # actual asserting
        for pagename, values in self.args_and_values:
            self.assertEqual(subpagelinks.SubpageLinks(self.request, pagename).render(), values)

if __name__ == "__main__":
    unittest.main()
