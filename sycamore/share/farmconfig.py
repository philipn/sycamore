# blacklist against wiki spammers

# We use the MT-Blacklist here, you can get it from:  http://www.jayallen.org/blacklist.txt
# You can find out more about MT-Blacklist at  http://www.jayallen.org/projects/mt-blacklist
# Please remove the comments in the list before using it!

blacklist = 'urlyoucantusewouldgohere'

import re, string

blacklist_re = "|".join(map(lambda s: "%s" % s.strip(), blacklist.strip().split("\n")))
blacklist_re = re.compile(blacklist_re)

from Sycamore.security import Permissions
 
class SecurityPolicy(Permissions):
    def save(self, editor, newtext, datestamp, **kw):
        match = blacklist_re.search(newtext)
        if match:
            print "blacklist match: %s" % match.group()
        return match == None
