import sys, os, unittest, random
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])
import __init__

from Sycamore import request, config
from Sycamore.macro import image
_did_rollback = False

class PageACLBasics(unittest.TestCase):
    global _did_rollback
    _did_rollback = False

    def testSet(self):
        """Test behavior of setting the page's acl."""
        pass

    def testSetBackToDefaults(self):
        """Test behavior of setting the page's acl back to the wiki's overall default acl."""
        pass

if __name__ == "__main__":
    unittest.main()
