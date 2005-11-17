# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LocalWiki.util.mail Tests

    @copyright: 2003-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import unittest
from LocalWiki.util import mail

class decodeSpamSafeEmailTestCase(unittest.TestCase):
    TESTS = [
        ('', ''),
        ('AT', '@'),
        ('DOT', '.'),
        ('DASH', '-'),
        ('CAPS', ''),
        ('Mixed', 'Mixed'),
        ('lower', 'lower'),
        ('Firstname DOT Lastname AT example DOT net', 'Firstname.Lastname@example.net'),
        ('Firstname . Lastname AT exa mp le DOT n e t', 'Firstname.Lastname@example.net'),
        ('Firstname I DONT WANT SPAM . Lastname@example DOT net', 'Firstname.Lastname@example.net'),
        ('First name I Lastname DONT AT WANT SPAM example DOT n e t', 'FirstnameLastname@example.net'),
        ('first.last@example.com', 'first.last@example.com'),
        ('first . last @ example . com', 'first.last@example.com'),
    ]

    def runTest(self):
        for coded, plain in self.TESTS:
            self.failUnlessEqual(mail.decodeSpamSafeEmail(coded), plain,
                "Failure to decode %r correctly (result %r, expected %r)!" %
                    (coded, mail.decodeSpamSafeEmail(coded), plain))

