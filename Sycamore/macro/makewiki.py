# -*- coding: utf-8 -*-

# Imports
from Sycamore import config
from Sycamore import farm
from Sycamore import wikiutil

Dependencies = ['time']

def execute(macro, args, formatter=None):
    request = macro.request
    before_form, after_form = '', ''
    if args and len(args.split(',')) == 2:
        before_form, after_form = args.split(',')
    if not formatter:
        formatter = macro.formatter
    if not config.allow_web_based_wiki_creation:
        return ('<i>This wiki farm does not have web-based wiki creation '
                'enabled.</i>')
    if request.user.valid:
            d = {'form_action': formatter.page.url(),
                'wikiname_length': farm.WIKINAME_MAX_LENGTH,
                'create_wiki_button': 'send_email',
                'after_form': after_form,
                'before_form': before_form,
            }
            wiki_create_form = (
                '<form action="%(form_action)s" method="POST">\n'
                '<span class="wikiNameArea">'
                '<input type="hidden" name="action" value="new_wiki">\n'
                '%(before_form)s'
                '<input type="text" class="wikiname" name="wikiname" '
                       'size="15" value="shortname" '
                       'maxlength="%(wikiname_length)s" '
                       'onFocus="this.value=\'\';this.style.color=\'black\';return false;">\n'
                '<input type="hidden" name="%(create_wiki_button)s" '
                       'value="1">\n'
                '<span class="description">%(after_form)s</span>'
                '</span>'
                '<span class="submit"><input type="submit" value="Create wiki"></span>\n'
                '</form>\n' % d)
    else:
        new_user_link = ('%s%s?new_user=1' %
                         (farm.getBaseFarmURL(request),
                          wikiutil.quoteWikiname(
                              config.page_user_preferences)))
        wiki_create_form = ('You must be logged in to create a wiki!  '
                            'To create an account, go '
                            '<a href="%s">here</a>.' % new_user_link)
    return formatter.rawHTML('<span id="wikiCreateForm">%s</span>' %
                             wiki_create_form) 
