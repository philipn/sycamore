# -*- coding: utf-8 -*- """
"""
    Sycamore - Security action

    This action allows you set specific security settings on an
    individual page.

    @copyright: 2006 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import config
from Sycamore import user
from Sycamore import wikiacl

from Sycamore.Page import Page
from Sycamore.wikiutil import quoteWikiname, unquoteWikiname
from Sycamore.wikiacl import ACL_RIGHTS_TABLE

def execute(pagename, request):
    _ = request.getText
    page = Page(pagename, request)
    actname = __name__.split('.')[-1] 
    if not request.user.may.admin(page):
        msg = _("You don't have admin permissions on this page, "
                "so you cannot change security settings.")
        return page.send_page(msg)
    
    if request.form.has_key('button'):
        # process save
        groups = [] 
        groups_dict = {}
        for key in request.form:
            if key.endswith('_groupname'):
                groups.append(unquoteWikiname(key[:-10]))
          else:
            if key.endswith('_may_read'):
                dowhat = 'read'
                groupname = unquoteWikiname(key[:-9])
            elif key.endswith('_may_edit'):
                dowhat = 'edit'
                groupname = unquoteWikiname(key[:-9])
            elif key.endswith('_may_delete'):
                dowhat = 'delete'
                groupname = unquoteWikiname(key[:-11])
            elif key.endswith('_may_admin'):
                dowhat = 'admin'
                groupname = unquoteWikiname(key[:-10])
            else:
                continue

            if not groups_dict.has_key(groupname):
                groups_dict[groupname] = [False, False, False, False]

            groups_dict[groupname][ACL_RIGHTS_TABLE[dowhat]] = True

        # set groups we weren't sent any checkboxes for to
        # all false (nothing checked)
        groups_no_checks = filter(lambda(groupname): (
            groupname not in groups_dict), groups)
        for groupname in groups_no_checks:
            groups_dict[groupname] = [False, False, False, False]
 
        wikiacl.setACL(pagename, groups_dict, request)
        return page.send_page(
            msg = _("Security settings sucessfully changed!"))

    formhtml = ['<h3>Security settings for "%s":</h3>' % pagename]

    button = _("Save")
    url = page.url()
    d = {'url': url, 'actname': actname, 'button': button}
    formhtml.append('<form method="POST" action="%(url)s">\n'
                    '<input type="hidden" name="action" value="%(actname)s">\n'
                    % d)

    custom_groups = user.getGroupList(request, exclude_special_groups=True)
    grouplist = ['All', 'Known'] + custom_groups
    for groupname in grouplist:
        # "All" and "Known" are a bit condense
        if groupname == 'All':
            written_groupname = 'Everybody'
        elif groupname == 'Known':
            written_groupname = 'Logged in people'
        else:
            written_groupname = groupname

        group = wikiacl.Group(groupname, request, fresh=True)

        # we want to show the 'change security' option only if
        # it makes some sense
        show_admin = groupname in custom_groups

        formhtml.append('<h6>%s</h6>' % written_groupname)
        formhtml.append('<input type="hidden" name="%s_groupname" '
                                  'value="1">' % quoteWikiname(groupname))
        if group.may(page, 'read'):
            formhtml.append('<input type="checkbox" checked '
                                    'name="%s_may_read" value="1">' %
                            quoteWikiname(groupname))
        else:
            formhtml.append('<input type="checkbox" name="%s_may_read" '
                                   'value="1">' % quoteWikiname(groupname))
        formhtml.append(' read ')

        if group.may(page, 'edit'):
            formhtml.append('<input type="checkbox" checked '
                                   'name="%s_may_edit" value="1">' %
                            quoteWikiname(groupname))
        else:
            formhtml.append('<input type="checkbox" name="%s_may_edit" '
                                   'value="1">' % quoteWikiname(groupname))
        formhtml.append(' edit ') 

        if group.may(page, 'delete'):
            formhtml.append('<input type="checkbox" checked '
                                   'name="%s_may_delete" value="1">' %
                            quoteWikiname(groupname))
        else:
            formhtml.append('<input type="checkbox" name="%s_may_delete" '
                                   'value="1">' % quoteWikiname(groupname))
        formhtml.append(' delete ')

        if show_admin:
            if group.may(page, 'admin'):
                formhtml.append('<input type="checkbox" checked '
                                       'name="%s_may_admin" value="1">' %
                                quoteWikiname(groupname))
            else:
                formhtml.append('<input type="checkbox" name="%s_may_admin" '
                                       'value="1">' % quoteWikiname(groupname))
            formhtml.append(' change security ')

    formhtml.append(
        '<p><input type="submit" name="button" value="%(button)s">\n'
        '</p>\n'
        '</form>' % d)

    page.send_page(msg=''.join(formhtml))
