""" Captcha.Visual.Backgrounds

Background layers for visual CAPTCHAs
"""
#
# PyCAPTCHA Package
# Copyright (C) 2004 Micah Dowty <micah@navi.cx>
#

import random, os

def RandomColors(num_colors=5):
    colors = []
    for i in range(0, num_colors):
        colors.append(RandomColor())
    return colors

def RandomColor():
   return (random.randint(0,255), random.randint(0,255), random.randint(0,255))

### The End ###
