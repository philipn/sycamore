# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Wiki Security Interface

    This implements the basic interface for user permissions and
    system policy. If you want to define your own policy, inherit
    from the base class 'Permissions', so that when new permissions
    are defined, you get the defaults.

    Then assign your new class to "SecurityPolicy" in moin_config;
    and I mean the class, not an instance of it!

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

#############################################################################
### Basic Permissions Interface -- most features enabled by default
#############################################################################


class Permissions:
    """ Basic interface for user permissions and system policy.

        Note that you still need to allow some of the related actions, this
        just controls their behaviour, not their activation.
    """

    def __init__(self, user):
        """ Calculate the permissons `user` has.
        """
        from LocalWiki.Page import Page
        self.Page = Page
        self.name = user.name
        self.request = user.request

    def read(self, pagename, **kw):
        """ Check whether user may read this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(pagename).may(self.request, self.name, "read")

    def edit(self, pagename, **kw):
        """ Check whether user may edit this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(pagename).may(self.request, self.name, "write")

    def save(self, editor, newtext, datestamp, **kw):
        """ Check whether user may save a page.

            `editor` is the PageEditor instance, the other arguments are
            those of the `PageEditor.saveText` method.

            The current msg presented to the user ("You are not allowed
            to edit any pages.") is a bit misleading, this will be fixed
            if we add policy-specific msgs.
        """
        return self.edit(editor.page_name)

    def delete(self, pagename, **kw):
        """ Check whether user may delete this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(pagename).may(self.request, self.name, "delete")

    def revert(self, pagename, **kw):
        """ Check whether user may revert this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(pagename).may(self.request, self.name, "revert")

    def admin(self, pagename, **kw):
        """ Check whether user may administrate this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(pagename).may(self.request, self.name, "admin")

    def getACL(self, pagename, **kw):
        return self.Page(pagename).getACL()

# make an alias for the default policy
Default = Permissions

