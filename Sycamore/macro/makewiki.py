from Sycamore import config, farm, wikiutil
Dependencies = ['time']

def execute(macro, args, formatter=None):
    request = macro.request
    if not formatter: formatter = macro.formatter
    if config.allow_web_based_wiki_creation:
        if request.user.valid:
            d = { 'form_action': wikiutil.quoteWikiname(macro.formatter.page.proper_name()), 'wikiname_length': farm.WIKINAME_MAX_LENGTH, 'create_wiki_button': 'send_email' }
            wiki_create_form = """<form action="%(form_action)s" method="POST">
<input type="hidden" name="action" value="new_wiki">
<input type="text" name="wikiname" size="20" maxlength="%(wikiname_length)s">
<input type="hidden" name="%(create_wiki_button)s" value="1">
<input type="submit" value="Create wiki">
</form>""" % d
        else:
            new_user_link = '%s%s?new_user=1' % (wikiutil.quoteWikiname(config.page_user_preferences), farm.getBaseFarmURL(request))
            wiki_create_form = """You must be logged in to create a wiki!  To create an account, go <a href="%s">here</a>.""" % new_user_link
        return formatter.rawHTML(wiki_create_form) 
    else:
        return '<i>This wiki farm does not have web-based wiki creation enabled.</i>'
