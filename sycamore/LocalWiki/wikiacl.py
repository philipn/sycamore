# -*- coding: iso-8859-1 -*-
"""
    LocalWiki Access Control Lists

    @copyright: 2003 by Thomas Waldmann, http://linuxwiki.de/ThomasWaldmann
    @copyright: 2003 by Gustavo Niemeyer, http://moin.conectiva.com.br/GustavoNiemeyer
    @license: GNU GPL, see COPYING for details.
"""

from LocalWiki import config, user
import re

GROUPRE = re.compile(config.page_group_regex)

class AccessControlList:
    """
    Access Control List

    Control who may do what on or with a wiki page.

    Syntax of an ACL string:
        [+|-]User[,User,...]:[right[,right,...]] [[+|-]SomeGroup:...] ...
        ... [[+|-]Known:...] [[+|-]All:...]

        "User" is a WikiUsername and triggers only if the user matches.

        "SomeGroup" is a page name matching config.page_group_regex with
         some lines in the form " * Member", defining the group members.

        "Known" is a group containing all valid / known users.

        "All" is a group containing all users (Known and Anonymous users).

        "right" may be an arbitrary word like read, write, delete, admin.
        Only words in config.acl_validrights are accepted, others are
        ignored. It is allowed to specify no rights, which means that no
        rights are given.

        When some user is trying to access some ACL-protected resource,
        the ACLs will be processed in the order they're found. The first
        matching ACL will tell if the user has access to that resource
        or not.

        For example, the following ACL tells that SomeUser is able to
        read and write the resources protected by that ACL, while any
        member of SomeGroup (besides SomeUser, if part of that group)
        may also admin that, and every other user is able to read it.

            SomeUser:read,write SomeGroup:read,write,admin All:read

        To make the system more flexible, there are also two modifiers:
        the prefixes '+' and '-'. When they are used, the given ACL
        entry will *only* match if the user is requesting the given
        rights. As an example, the above ACL could also be written
        as:

            -SomeUser:admin SomeGroup:read,write,admin All:read

        Or even:

            +All:read -SomeUser:admin SomeGroup:read,write,admin

        Notice that you probably won't want to use the second and
        third examples in ACL entries of some page. They're very
        useful on the moin configuration entries though.

   Config:
       config.acl_enabled
           If true will enable ACL support.
           Default: 0

       config.acl_rights_default
           It is is ONLY used when no other ACLs are given.
           Default: "Known:read,write,delete All:read,write",

       config.acl_rights_before
           When the page has ACL entries, this will be inserted BEFORE
           any page entries.
           Default: ""

       config.acl_rights_after
           When the page has ACL entries, this will be inserted AFTER
           any page entries.
           Default: ""
       
       config.acl_rights_valid
           These are the acceptable (known) rights (and the place to
           extend, if necessary).
           Default: ['read','write','delete','admin']
    """

    special_users = ["All", "Known", "Trusted"]

    def __init__(self, lines=[]):
        """Initialize an ACL, starting from <nothing>.
        """
        self.setLines(lines)

    def clean(self):
        self.acl = [] # [ ('User': {"read": 0, ...}), ... ]
        self.acl_lines = []
        self._is_group = {}

    def setLines(self, lines=[]):
        self.clean()
        self.addBefore()
        if not lines:
            self.addDefault()
        else:
            for line in lines:
                self.addLine(line)
        self.addAfter()

    def addDefault(self):
        self.addLine(config.acl_rights_default, remember=0)
    def addBefore(self):
        self.addLine(config.acl_rights_before, remember=0)
    def addAfter(self):
        self.addLine(config.acl_rights_after, remember=0)

    def addLine(self, aclstring, remember=1):
        """Add another ACL line
           This can be used in multiple subsequent calls
           to process longer lists.
        """
        if remember:
            self.acl_lines.append(aclstring)
        for ac in aclstring.strip().split():
            tokens = ac.split(':')
            if len(tokens) == 1:
                if tokens[0] == "Default":
                    self.addDefault()
            elif len(tokens) == 2:
                entries, rights = tokens
                rights = [x for x in rights.split(',')
                             if x in config.acl_rights_valid]
                if entries and entries[0] in ['+','-']:
                    c = entries[0]
                    for entry in entries[1:].split(','):
                        if GROUPRE.search(entry):
                            self._is_group[entry] = 1
                        rightsdict = {}
                        for right in rights:
                            rightsdict[right] = (c == "+")
                        self.acl.append((entry, rightsdict))
                else:
                    for entry in entries.split(','):
                        if GROUPRE.search(entry):
                            self._is_group[entry] = 1
                        rightsdict = {}
                        for right in config.acl_rights_valid:
                            rightsdict[right] = (right in rights)
                        self.acl.append((entry, rightsdict))

    def may(self, request, name, dowhat):
        """May <name> <dowhat>?
           Returns boolean answer.
        """
        if not config.acl_enabled:
            # Preserve default behavior of allowing only valid
            # users to delete.
            if dowhat == "delete" and not request.user.valid:
                return 0
            return 1

        is_group_member = request.dicts.has_member
        allowed = None
        for entry, rightsdict in self.acl:
            if entry in self.special_users:
                handler = getattr(self, "_special_"+entry, None)
                allowed = handler(request, name, dowhat, rightsdict)
            elif self._is_group.get(entry) and is_group_member(entry, name):
                allowed = rightsdict.get(dowhat)
            elif entry == name:
                allowed = rightsdict.get(dowhat)
            if allowed is not None:
                return allowed
        return 0

    def getString(self, b='#acl ', e='\n'):
        """print the acl strings we were fed with"""
        return ''.join(["%s%s%s" % (b,l,e) for l in self.acl_lines])

    def _special_All(self, request, name, dowhat, rightsdict):
        return rightsdict.get(dowhat)

    def _special_Known(self, request, name, dowhat, rightsdict):
        """ check if user <name> is known to us,
            that means that there is a valid user account present.
            works for subscription emails.
        """
        if user.getUserId(name, request): # is a user with this name known?
            return rightsdict.get(dowhat)
        return None

    def _special_Trusted(self, request, name, dowhat, rightsdict):
        """ check if user <name> is known AND even has logged in using a password.
            does not work for subsription emails that should be sent to <user>,
            as he is not logged in in that case.
        """
        if request.user.trusted and name == request.user.name:
            return rightsdict.get(dowhat)
        return None

    def __eq__(self, other):
        return self.acl_lines == other.acl_lines
    def __ne__(self, other):
        return self.acl_lines != other.acl_lines

def parseACL(body):
    if not config.acl_enabled:
        return AccessControlList()

    acl_lines = []
    while body and body[0] == '#':
        # extract first line
        try:
            line, body = body.split('\n', 1)
        except ValueError:
            line = body
            body = ''

        # end parsing on empty (invalid) PI
        if line == "#":
            break

        # skip comments (lines with two hash marks)
        if line[1] == '#':
            continue

        tokens = line.split(None, 1)
        if tokens[0].lower() == "#acl":
            if len(tokens) == 2:
                args = tokens[1].rstrip()
            else:
                args = ""
            acl_lines.append(args)
    return AccessControlList(acl_lines)

