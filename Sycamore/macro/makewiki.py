# -*- coding: utf-8 -*-

# Imports
from Sycamore import config
from Sycamore import farm
from Sycamore import wikiutil

Dependencies = ['time']

def execute(macro, args, formatter=None):
    request = macro.request
    if not formatter:
        formatter = macro.formatter
    if not config.allow_web_based_wiki_creation:
        return ('<i>This wiki farm does not have web-based wiki creation '
                'enabled.</i>')
    if request.user.valid:
            d = {'form_action': wikiutil.quoteWikiname(
                    macro.formatter.page.proper_name()),
                'wikiname_length': farm.WIKINAME_MAX_LENGTH,
                'create_wiki_button': 'send_email'}
            wiki_create_form = (
                '<form action="%(form_action)s" method="POST">\n'
                '<input type="hidden" name="action" value="new_wiki">\n'
                '<input type="text" name="wikiname" size="20" '
                       'maxlength="%(wikiname_length)s">\n'
                '<input type="hidden" name="%(create_wiki_button)s" '
                       'value="1">\n'
                '<input type="submit" value="Create wiki">\n'
                '</form>\n' % d)
    else:
        new_user_link = ('%s%s?new_user=1' %
                         (farm.getBaseFarmURL(request),
                          wikiutil.quoteWikiname(
                              config.page_user_preferences)))
        wiki_create_form = ('You must be logged in to create a wiki!  '
                            'To create an account, go '
                            '<a href="%s">here</a>.' % new_user_link)
    return formatter.rawHTML(wiki_create_form) 
