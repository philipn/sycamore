# -*- coding: iso-8859-1 -*-
"""
    Sycamore classic theme

    This class can also be used as base class for other themes -
    if you make an empty child class, you will get classic behaviour.

    If you want modified behaviour, just override the stuff you
    want to change in the child class.

    @copyright: 2003 by ThomasWaldmann (LinuxWiki:ThomasWaldmann)
    @license: GNU GPL, see COPYING for details.
"""

import urllib
from Sycamore import config, i18n, wikiutil
from Sycamore.Page import Page

class Theme(object):
    """ here are the functions generating the html responsible for
        the look and feel of your wiki site
    """

    name = "classic"

    icons = {
        # key         alt                        icon filename      w   h
        # ------------------------------------------------------------------
        # navibar
        'help':       ("%(page_help_contents)s", "moin-help.png",   12, 11),
        'find':       ("%(page_find_page)s",     "moin-search.png", 12, 12),
        'diff':       ("Diffs",                  "moin-diff.png",   47, 15),
        'info':       ("Info",                   "info.png",   24, 24),
        'edit':       ("Edit",                   "edit.png",   24, 24),
        'talk':       ("Talk",                   "talk.png",   24, 24),
        'article':    ("Article",             "article.png",   24, 24),
        'unsubscribe':("Unsubscribe",            "moin-unsubscribe.png",  14, 10),
        'subscribe':  ("Subscribe",              "moin-subscribe.png",14, 10),
        'raw':        ("Raw",                    "moin-raw.png",    12, 13),
        'xml':        ("XML",                    "moin-xml.png",    20, 13),
        'print':      ("Print",                  "moin-print.png",  16, 14),
        'view':       ("View",                   "moin-show.png",   12, 13),
        # FileAttach (is this used?)
        'attach':     ("%(attach_count)s",       "moin-attach.png",  7, 15),
        # RecentChanges
	'event':      ("New Event",              "devil.png", 15, 15),
        'rss':        ("[RSS]",                  "moin-rss.png",    36, 14),
        'deleted':    ("[DELETED]",              "sycamore-deleted.png",59, 13),
        'updated':    ("[UPDATED]",              "sycamore-updated.png",59, 13),
        'new':        ("[NEW]",                  "sycamore-new.png",    59, 13),
        'diffrc':     ("[DIFF]",                 "sycamore-diff.png",   59, 13),
        # General
        'bottom':     ("[BOTTOM]",               "moin-bottom.png", 14, 10),
        'top':        ("[TOP]",                  "moin-top.png",    14, 10),
        'www':        ("[WWW]",                  "sycamore-www.png",    14, 11),
        'mailto':     ("[MAILTO]",               "moin-email.png",  14, 10),
        'news':       ("[NEWS]",                 "moin-news.png",   10, 11),
        'telnet':     ("[TELNET]",               "moin-telnet.png", 10, 11),
        'ftp':        ("[FTP]",                  "moin-ftp.png",    11, 11),
        'file':       ("[FILE]",                 "moin-ftp.png",    11, 11),
        # search forms
        'searchbutton': ("[?]",                  "moin-search.png", 12, 12),
        'interwiki':  ("[%(wikitag)s]",          "moin-inter.png",  16, 16),
    }

    # ??? Why do we need stylesheet_print? the standard stylesheets
    # provide a print version?

    stylesheets_print = (
        # theme charset         media       basename
        (name,  'iso-8859-1',   'all',      'common'),
        (name,  'iso-8859-1',   'all',      'print'),
        )
    
    stylesheets = (
        # theme charset         media       basename
        (name,  'iso-8859-1',   'all',      'common'),
        (name,  'iso-8859-1',   'screen',   'screen'),
        (name,  'iso-8859-1',   'print',    'print'),
        )

    def __init__(self, request):
        """
        Initialize the theme object.
        
        @param request: the request object
        """
        self.request = request

    def img_url(self, img):
        """
        generate an img url

        @param img: the image filename
        @rtype: string
        @return: the image url
        """
        return "%s/%s/img/%s" % (config.url_prefix, self.name, img)

    def css_url(self, basename, theme = None):
        """
        generate the css url

        @param basename: the css media type (base filename w/o .css)
        @param theme: theme name
        @rtype: string
        @return: the css url
        """
        if not theme:
            theme = self.name
        return "%s/%s/css/%s.css" % (config.url_prefix, theme, basename)

    def emit_custom_html(self, html):
        """
        generate custom HTML code in `html`
        
        @param html: a string or a callable object, in which case
                     it is called and its return value is used
        @rtype: string
        @return: string with html
        """
        if html:
            if callable(html): html = html(self.request)
        return html

    # Header stuff #######################################################

    def logo(self, d):
        """
        Assemble the logo
        
        @param d: parameter dictionary
        @rtype: string
        @return: logo html
        """
        if d['logo_string']:
            html = '<div id="logo">%s</div>' % wikiutil.link_tag(
                self.request, wikiutil.quoteWikiname(d['page_front_page']), d['logo_string'])
        else:
            html = ''
        return html

    def title(self, d):
        """
        Assemble the title
        
        @param d: parameter dictionary
        @rtype: string
        @return: title html
        """
        _ = self.request.getText
        html = ['<div id="title">']
        if d['title_link']:
            html.append('<h1><a title="%s" href="%s">%s</a></h1>' % (
                _('Click here to get more information about this page'),
                d['title_link'],
                wikiutil.escape(d['title_text'])))
        else:
            html.append('<h1>%s</h1>' % wikiutil.escape(d['title_text']))
        html.append('</div>')
        return ''.join(html)

    def username(self, d):
        """
        Assemble the username / userprefs link
        
        @param d: parameter dictionary
        @rtype: string
        @return: username html
        """
        html = '<div id="username">%s</div>' % wikiutil.link_tag(
            self.request, wikiutil.quoteWikiname(d['page_user_prefs']),
            wikiutil.escape(d['user_prefs']))
        return html

    def navibar(self, d):
        """
        Assemble the navibar
        
        @param d: parameter dictionary
        @rtype: string
        @return: navibar html
        """
        html = []
        html.append('<ul id="navibar">\n')
        if d['navibar']:
            # Print site name in first field of navibar
            # html.append(('<li>%(site_name)s</li>\n') % d)
            for (link, navi_link) in d['navibar']:
                html.append((
                    '<li><a href="%(link)s">%(navi_link)s</a></li>\n') % {
                        'link': link,
                        'navi_link': navi_link,
                    })
        html.append('</ul>')
        return ''.join(html)

    def get_icon(self, icon):
        try:
            ret = self.icons[icon]
        except KeyError: # if called from [[Icon(file)]] we have a filename, not a key
            # using filenames is deprecated, but for now, we simulate old behaviour!
            # please use only the icon *key* in future, not the filename any more.
            icon = icon.replace('.gif','.png') # no gifs any more!
            for i in self.icons.keys():
                ret = self.icons[i]
                if ret[1] == icon: # found the file name?
                    break
            else:
                ret = ("", icon, "", "")
        return (ret[0], self.img_url(ret[1])) + ret[2:]
   
    def make_icon(self, icon, vars=None, actionButton=False, style=None):
        """
        This is the central routine for making <img> tags for icons!
        All icons stuff except the top left logo, smileys and search
        field icons are handled here.
        
        @param icon: icon id (dict key)
        @param vars: ...
        @rtype: string
        @return: icon html (img tag)
        """
        if vars is None:
            vars = {}
        alt, img, w, h = self.get_icon(icon)
        try:
            alt = alt % vars
        except KeyError, err:
            alt = 'KeyError: %s' % str(err)
        if self.request:
            alt = self.request.getText(alt)
        try:
	    if actionButton: 
              tag = self.request.formatter.image(html_class="actionButton", src=img, alt=alt, width=w, height=h)
	    else:
    	      if style:
                tag = self.request.formatter.image(html_class="borderless", src=img, alt=alt, width=w, height=h, style=style)
	      else: 
                tag = self.request.formatter.image(html_class="borderless", src=img, alt=alt, width=w, height=h)
        except AttributeError: # XXX FIXME if we have no formatter or no request 
            if actionButton:
	      tag = '<img class="actionButton" src="%s" alt="%s" width="%s" height="%s">' % (
                img, alt, w, h)
	    else: 
              if style:
	        tag = '<img class="borderless" src="%s" alt="%s" width="%s" height="%s" style="%s">' % (
                  img, alt, w, h, style)
	      else:
	        tag = '<img class="borderless" src="%s" alt="%s" width="%s" height="%s" style="%s">' % (
                  img, alt, w, h, style)

        return tag

    def make_iconlink(self, which, d, actionButton=False):
        """
        Make a link with an icon

        @param which: icon id (dictionary key)
        @param d: parameter dictionary
        @rtype: string
        @return: html link tag
        """
        page_params, title, icon = config.page_icons_table[which]
        d['title'] = title % d
        d['i18ntitle'] = self.request.getText(d['title'])
        img_src = self.make_icon(icon, d, actionButton)
        return wikiutil.link_tag(self.request, page_params % d, img_src, attrs='title="%(i18ntitle)s"' % d)

    def iconbar(self, d):
        """
        Assemble the iconbar
        
        @param d: parameter dictionary
        @rtype: string
        @return: iconbar html
        """
        iconbar = []
        if config.page_iconbar and d['page_name']:
            iconbar.append('<ul id="iconbar">\n')
            icons = config.page_iconbar[:]
            for icon in icons:
                iconbar.append('<li>%s</li>\n' % self.make_iconlink(icon, d))
            iconbar.append('</ul>\n')
        return ''.join(iconbar)

    def msg(self, d):
        """
        Assemble the msg display
        
        @param d: parameter dictionary
        @rtype: string
        @return: msg display html
        """
        html = ''
        if d['msg']:
            _ = self.request.getText
            d.update({'link_text': _('Clear message'),})
            clear_msg_link = """<a onClick="return hideMessage('message');" href="%(script_name)s/%(q_page_name)s?action=show">%(link_text)s</a>""" % d
            d.update({'clear_msg_link': clear_msg_link,})
            html = ('\n<div id="message">\n'
                    '<p>%(msg)s</p><p>%(clear_msg_link)s</p></div>') % d
        return html
    
    #def trail(self, d):
    #    """
    #    Assemble page trail
    #    
    #    @param d: parameter dictionary
    #    @rtype: string
    #    @return: trail html
    #    """
    #    html = []
    #    if d['trail']:
    #        pagetrail = d['trail']
    #        html.append('<ul id="pagetrail">\n')
    #        for p in pagetrail[:-1]:
    #            html.append('<li><span>%s</span></li>\n' % (Page(p, self.request.cursor).link_to(self.request),))
    #        html.append('<li><span>%s</span></li>\n' % wikiutil.escape(pagetrail[-1]))
    #        html.append('</ul>\n')
    #    else:
    #        html.append('<hr id="pagetrail">\n')
    #    return ''.join(html)

    def html_stylesheet_link(self, charset, media, href):
        return ('<link rel="stylesheet" type="text/css" charset="%s" '
                'media="%s" href="%s">\n') % (charset, media, href)

    def html_stylesheets(self, d):
        """
        Assemble stylesheet links
        
        @param d: parameter dictionary
        @rtype: string
        @return: links
        """
        html = []
        if d.get('print_mode', False):
            stylesheets = self.stylesheets_print
        else:
            stylesheets = self.stylesheets
        user_css_url = self.request.user.valid and self.request.user.css_url

        # Create stylesheets links
        for theme, charset, media, name in stylesheets:
            href = self.css_url(name, theme)
            html.append(self.html_stylesheet_link(charset, media, href))

            # workaround for old user settings
            # Dont add user css url if it matches one of ours
            if user_css_url and user_css_url == href:
                user_css_url = None

        # Add user css url (assuming that user css uses iso-8859-1)
        # ???  Maybe move to utf-8?
        # TODO: Document this in the Help system
        if user_css_url and user_css_url.lower() != "none":
            html.append(
                self.html_stylesheet_link('iso-8859-1', 'all', user_css_url))

        return ''.join(html)

    def html_head(self, d):
        """
        Assemble html head
        
        @param d: parameter dictionary
        @rtype: string
        @return: html head
        """
        dict = {
            'stylesheets_html': self.html_stylesheets(d),
        }
        dict.update(d)

        html = """
<title>%(title)s - %(sitename)s</title>
%(stylesheets_html)s
""" % dict

        return html

    def header(self, d):
        """
        Assemble page header
        
        @param d: parameter dictionary
        @rtype: string
        @return: page header html
        """
        dict = {
            'config_header1_html': self.emit_custom_html(config.page_header1),
            'config_header2_html': self.emit_custom_html(config.page_header2),
            'logo_html':  self.logo(d),
            'title_html':  self.title(d),
            'username_html':  self.username(d),
            'navibar_html': self.navibar(d),
            'iconbar_html': self.iconbar(d),
            'msg_html': self.msg(d),
            'trail_html': self.trail(d),
        }
        dict.update(d)

        html = """
%(config_header1_html)s
%(logo_html)s
%(username_html)s
%(title_html)s
%(iconbar_html)s
%(navibar_html)s
%(trail_html)s
%(config_header2_html)s
%(msg_html)s
""" % dict

        # Next parts will use config.default_lang direction, as set in the <body>
        return html

    # Footer stuff #######################################################
    
    def showtext_link(self, d, **keywords):
        """
        Assemble ShowText link (on action pages)
        
        @param d: parameter dictionary
        @rtype: string
        @return: edittext link html
        """
        _ = self.request.getText
        html = ''
        if keywords.get('showpage', 0):
            html = "<p>%s %s</p>\n" % (
               wikiutil.link_tag(self.request, d['q_page_name'], _("ShowText")),
                _('of this page'),
            )
        return html

    def edittext_link(self, d, **keywords):
        """
        Assemble EditText link (or indication that page cannot be edited)
        
        @param d: parameter dictionary
        @rtype: string
        @return: edittext link html
        """
        _ = self.request.getText
        html = []
        html.append('<p>')
        if keywords.get('editable', 1):
            editable = self.request.user.may.edit(d['page_name']) and d['page'].isWritable()
            if editable:
                html.append("%s %s" % (
                    wikiutil.link_tag(self.request, d['q_page_name']+'?action=edit', _('EditText')),
                    _('of this page'),
                ))
            else:
                html.append("%s" % _('Immutable page'))
            html.append(' %(last_edit_info)s' % d)
            html.append('</p>')
        return ''.join(html)

    def footer_fragments(self, d, **keywords):
        """
        assemble HTML code fragments added by the page formatters
        
        @param d: parameter dictionary
        @rtype: string
        @return: footer fragments html
        """
        html = ''
        if d['footer_fragments']:
            html = ''.join(d['footer_fragments'].values())
        return html

    def searchform(self, d):
        """
        assemble HTML code for the search forms
        
        @param d: parameter dictionary
        @rtype: string
        @return: search form html
        """
        _ = self.request.getText
        sitenav_pagename = wikiutil.getSysPage(self.request, 'SiteNavigation').page_name
        dict = {
            'find_page_html': wikiutil.link_tag(self.request, d['page_find_page']+'?value='+urllib.quote_plus(d['page_name'], ''), _('FindPage')),
            'navi_page_html': wikiutil.link_tag(self.request, sitenav_pagename, sitenav_pagename),
            'search_html': _("or search titles %(titlesearch)s, full text %(textsearch)s or") % d,
        }
        dict.update(d)
        
        html = """
<form method="POST" action="%(script_name)s/%(q_page_name)s">
<p>
<input type="hidden" name="action" value="inlinesearch">
%(find_page_html)s %(search_html)s %(navi_page_html)s
</p>
</form>
""" % dict

        return html

    def availableactions(self, d):    
        """
        assemble HTML code for the available actions
        
        @param d: parameter dictionary
        @rtype: string
        @return: available actions html
        """
        _ = self.request.getText
        html = []
        html.append('<p>')
        first = 1
        for action in d['available_actions']:
            html.append("%s %s" % (
                (',', _('Or try one of these actions:'))[first],
                wikiutil.link_tag(self.request, '%s?action=%s' % (d['q_page_name'], action), action),
            ))
            first = 0
        html.append('</p>')
        return ''.join(html)

    def showversion(self, d, **keywords):
        """
        assemble HTML code for copyright and version display
        
        @param d: parameter dictionary
        @rtype: string
        @return: copyright and version display html
        """
        html = ''
        if config.show_version and not keywords.get('print_mode', 0):
            html = ('<p>'
                    'Sycamore %s, Copyright \xa9 2000-2004 by Jürgen Hermann'
                    '</p>' % (version.revision,))
        return html

    def footer(self, d, **keywords):
        """
        Assemble page footer
        
        @param d: parameter dictionary
        @keyword ...:...
        @rtype: string
        @return: page footer html
        """
        dict = {
            'config_page_footer1_html': self.emit_custom_html(config.page_footer1),
            'config_page_footer2_html': self.emit_custom_html(config.page_footer2),
            'showtext_html': self.showtext_link(d, **keywords),
            'edittext_html': self.edittext_link(d, **keywords),
            'search_form_html': self.searchform(d),
            'credits_html': self.emit_custom_html(config.page_credits),
            'version_html': self.showversion(d, **keywords),
            'footer_fragments_html': self.footer_fragments(d, **keywords),
        }
        dict.update(d)
        
        html = """
<div id="footer">
<div id="credits">
%(credits_html)s
</div>
%(config_page_footer1_html)s
%(showtext_html)s
%(footer_fragments_html)s
%(edittext_html)s
%(search_form_html)s
%(config_page_footer2_html)s
</div>
%(version_html)s
""" % dict

        return html

    # RecentChanges ######################################################

    def recentchanges_entry(self, d):
        """
        Assemble a single recentchanges entry (table row)
        
        @param d: parameter dictionary
        @rtype: string
        @return: recentchanges entry html
        """
        _ = self.request.getText
        html = []
        html.append('<tr height="10"></tr><tr>\n')
        
        html.append('<td width="100" class="rcicon1">%(icon_html)s</td>\n' % d)
        
        html.append('<td valign="center" class="rcpagelink">%(pagelink_html)s' % d)
         
        html.append('&nbsp;<span align="right" class="rctime">')
        if d['time_html']:
            html.append("last modified %(time_html)s" % d)
        showcomments = 1
        if d['show_comments'] == 0:
            showcomments = 0
            com = d['comments'][0]
            if not com:
              com = ''
            else:
              com = '(' + com + ')'
            html.append(' by </span><span class="rceditor" title=%s>%s</span> <span class="rccomment">%s' % (d['editors'][0][1], d['editors'][0][0],com ))
        html.append('</span></td>\n')
        html.append('</tr>')

        #html.append('<td class="rcicon2">%(info_html)s</td>\n' % d)
        num = 0
        if d['editors'] and d['show_comments'] == 1:
            for editor, ip in d['editors']:
                  com = d['comments'][num]
                  if not com:
                    com = '(No comment)'
                  html.append('<tr><td>&nbsp;</td><td class="rccomment" title="%s">%s&nbsp;&nbsp;<span class="rceditor">%s</span></td></tr>' % (ip, com, editor))
                  num = num + 1

       # html.append('<td class="rceditor">')
       # if d['editors']:
       #     html.append('<br>'.join(d['editors']))
       # html.append('</td>\n')
            
       # html.append('<td class="rccomment">')
       # if d['comments']:
       #     if d['changecount'] > 1:
       #         notfirst = 0
       #         for comment in d['comments']:
       #             html.append('%s<tt>#%02d</tt>&nbsp;%s' % (
       #                 notfirst and '<br>' or '' , comment[0], comment[1]))
       #             notfirst = 1
       #     else:
       #         comment = d['comments'][0]
       #         html.append('%s' % comment[1])
       # html.append('</td>\n')
           
       # html.append('</tr>\n')
        
        return ''.join(html)
    
    def recentchanges_daybreak(self, d):
        """
        Assemble a rc daybreak indication (table row)
        
        @param d: parameter dictionary
        @rtype: string
        @return: recentchanges daybreak html
        """
        if d['bookmark_link_html']:
            set_bm = '&nbsp;<span style="font-size: 13px;">[%(bookmark_link_html)s]</span>' % d
        else:
            set_bm = ''
        return ('<tr class="rcdaybreak"><td colspan="%d">'
                '<h2>%s'
                '%s</h2>'
                '</td></tr>\n') % (2, d['date'], set_bm)

    def recentchanges_header(self, d):
        """
        Assemble the recentchanges header (intro + open table)
        
        @param d: parameter dictionary
        @rtype: string
        @return: recentchanges header html
        """
        _ = self.request.getText

        html = ['<div class="recentchanges" %s>\n<table cellspacing="0" width="100%%"><tr>\n<td>' % self.ui_lang_attr()]

        if d['rc_update_bookmark']:
            html.append("%(rc_update_bookmark)s %(rc_curr_bookmark)s<br>" % d)
        if d['rc_days']:
            days = []
            for day in d['rc_days']:
                if day == d['rc_max_days']:
                    days.append('<strong>%d</strong>' % day)
                else:
                    days.append(
                        wikiutil.link_tag(self.request,
                            '%s?max_days=%d' % (d['q_page_name'], day),
                            str(day)))
            days = ' | '.join(days)
            html.append((_("Show all changes in the last %s days.") % (days,)))
        if self.request.user.valid and d['show_comments_html']:
            html.append(' ' + d['show_comments_html'])
        if d['rc_rss_link']:
            html.append('<td><td align="right" width="30">%s\n' % d['rc_rss_link'])

        html.append('</td></tr>\n</div>\n<table>\n')
        return ''.join(html)

    def recentchanges_footer(self, d):
        """
        Assemble the recentchanges footer (close table)
        
        @param d: parameter dictionary
        @rtype: string
        @return: recentchanges footer html
        """
        _ = self.request.getText
        html = ''
        html += '</table>\n'
        if d['rc_msg']:
            html += "<br>%(rc_msg)s\n" % d
        html += '</div>\n'
        return html

    #
    # Language stuff
    #
    
    def ui_lang_attr(self):
        """Generate language attributes for user interface elements

        User interface elements use the user language (if any), kept in
        request.lang.

        @rtype: string
        @return: lang and dir html attributes
        """
        lang = self.request.lang
        dir = i18n.getDirection(lang)
        return 'lang="%(lang)s" dir="%(dir)s"' % locals()

    def content_lang_attr(self):
        """Generate language attributes for wiki page content

        Page content uses the wiki default language

        @rtype: string
        @return: lang and dir html attributes
        """
        lang = config.default_lang
        dir = i18n.getDirection(lang)
        return 'lang="%(lang)s" dir="%(dir)s"' % locals()

        
def execute(request):
    """
    Generate and return a theme object
        
    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)
