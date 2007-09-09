""" Captcha.Numbers
"""
#
# PyCAPTCHA Package
# Copyright (C) 2004 Micah Dowty <micah@navi.cx>
#

import random, os
import File

minLength = 4
maxLength = 8

def pick():
     """Pick a set of numbers, return as a string."""
     length = random.randint(minLength, maxLength)
     nums = []
     for i in range(0, length):
       num = random.randint(0,9)
       nums.append(str(num))
     return ''.join(nums)
