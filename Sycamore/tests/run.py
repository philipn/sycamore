# -*- coding: utf-8 -*-

# Imports
import sys
import os
import unittest
import random

__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..'))])
import __init__

from Sycamore import request
from Sycamore import config
_did_rollback = False

# import the tests
from basics import *
from macro.image import *
from page.page import *
from security.usergroups import *
from widgets.subpagelinks import *

if __name__ == "__main__":
   unittest.main()
