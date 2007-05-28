# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Wiki Security Interface

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
        self.name = user.name
        self.request = user.request

    def read(self, page, **kw):
        """ Check whether user may read this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(page, **kw).may(self.request, self.name, "read")

    def edit(self, page, **kw):
        """ Check whether user may edit this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(page, **kw).may(self.request, self.name, "edit")

    def delete(self, page, **kw):
        """ Check whether user may delete this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(page, **kw).may(self.request, self.name, "delete")

    def admin(self, page, **kw):
        """ Check whether user may administrate this page.

            `kw` allows passing more information without breaking user
            policies and is not used currently.
        """
        return self.getACL(page, **kw).may(self.request, self.name, "admin")

    def getACL(self, page, **kw):
        return page.getACL(**kw)

# make an alias for the default policy
Default = Permissions

