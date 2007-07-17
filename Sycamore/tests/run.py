import sys, os, unittest, random
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))])
import __init__

from Sycamore import request, config
_did_rollback = False

# import the tests
from basics import *
from macro.image import *
from page.page import *
from security.usergroups import *
from security.acl import *
from widgets.subpagelinks import *

if __name__ == "__main__":
   unittest.main()
