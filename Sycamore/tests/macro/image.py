# -*- coding: utf-8 -*-

# Imports
import sys
import os
import unittest
import random

__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])
import __init__

from Sycamore import request
from Sycamore import config

from Sycamore.macro import image
_did_rollback = False

class ImageBasics(unittest.TestCase):
    global _did_rollback
    _did_rollback = False
    args_and_values = [
        ('imagename.jpg, 200, "Hi mom!"',
         ('imagename.jpg', 'Hi mom!', False, 200, '', True)),
        ('himom.jpg, "Hi dude!"',
         ('himom.jpg', 'Hi dude!', False, 0, '', True)),
        ('duders.jpg, thumbnail',
         ('duders.jpg', '', True, 0, '', True)),
        ('duders.jpg, thumbnail, noborder',
         ('duders.jpg', '', True, 0, '', False)),
        ('duders.jpg,thumbnail,noborder',
         ('duders.jpg', '', True, 0, '', False)),
        ('Filename, has, commas.jpg, "This is the caption", 455',
         ('Filename, has, commas.jpg', 'This is the caption', False, 455, '',
          True)),
        ('Filename, has, commas.jpg,"This is the caption",455',
         ('Filename, has, commas.jpg', 'This is the caption', False, 455, '',
          True)),
	    ('PhilipNeustrom.jpg, "Philip is an avid photographer", thumbnail',
         ('PhilipNeustrom.jpg', 'Philip is an avid photographer', True, 0, '',
          True)),
	    (('PhilipNeustrom.jpg, "Philip is an avid photographer", thumbnail, '
          'right'),
         ('PhilipNeustrom.jpg', 'Philip is an avid photographer', True, 0,
          'right', True)),
	    (('PhilipNeustrom.jpg, "Philip is an avid photographer", thumbnail, '
          'right, 350'),
         ('PhilipNeustrom.jpg', 'Philip is an avid photographer', True, 350,
          'right', True)),
        (('PhilipNeustrom.jpg, " Philip is an avid photographer", thumbnail, '
          'right, 350'),
         ('PhilipNeustrom.jpg', 'Philip is an avid photographer', True, 350,
          'right', True))
        ]

    def testGetArguments(self):
        """Tests image's getArguments()"""
        for arg, values in self.args_and_values:
            self.assertEqual(image.getArguments(arg), values)

if __name__ == "__main__":
    unittest.main()
