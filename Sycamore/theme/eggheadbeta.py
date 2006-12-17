# -*- coding: iso-8859-1 -*-
"""
    Sycamore default theme.  Base code copied from rightsidebar MoinMoin theme.
"""
from Sycamore.Page import Page
from Sycamore import config, wikiutil, farm, user
from classic import Theme as ThemeBase
from Sycamore.widget import subpagelinks
import string, urllib

png_behavior = "behavior: url('%s%s/pngbehavior.htc');" % (config.web_dir, config.url_prefix)

class Theme(ThemeBase):
    """ here are the functions generating the html responsible for
        the look and feel of your wiki site
    """

    name = "eggheadbeta"
    showapplet = 0

    stylesheets_print = (
        # theme charset         media       basename
        (name,  'iso-8859-1',   'all',      'common'),
        (name,  'iso-8859-1',   'print',      'screen'),
        )
    
    stylesheets = (
        # theme charset         media       basename
        (name,  'iso-8859-1',   'all',      'common'),
        (name,  'iso-8859-1',   'screen',   'screen'),
        (name,  'iso-8859-1',   'print',    'screen'),
        )
    
    def __init__(self, request):
      ThemeBase.__init__(self, request)
      self.icons['www'] = ("[WWW]", "sycamore-www.png", 14, 11)

    # Header stuff #######################################################

    def banner(self,d):
        """
        Assemble the banner

        @rtype: string
        @return: banner html
        """
        from Sycamore.action.Files import has_file, getAttachUrl
        if d['script_name']:
            html = ['&nbsp;<a class="nostyle" href="%(script_name)s">' % d]
        else:
            html = ['&nbsp;<a class="nostyle" href="%s/Front_Page">' % self.request.getScriptname()]

        images_pagename = "%s/%s" % (config.wiki_settings_page, config.wiki_settings_page_images)
        if has_file(self.request, images_pagename, 'logo.png'):
	  if not self.request.config.logo_sizes.has_key('logo.png'):
	     wikiutil.init_logo_sizes(self.request)
	  width, height = self.request.config.logo_sizes['logo.png']
          html.append('<img align="middle" src="%s" alt="wiki logo" style="%s" height="%s" width="%s"></a>' % (getAttachUrl(images_pagename, 'logo.png', self.request), png_behavior, height, width))
        else: html.append('<div id="logo_text">%s</div></a>' % self.request.config.sitename)

        return ''.join(html)

    def new_iconbar(self, d):
      return """<td valign="bottom">&nbsp;&nbsp;&nbsp;&nbsp;</td>
             %s
             %s
             %s
             %s
             """ % (self.editicon(d), self.infoicon(d), self.talkicon(d), self.mapicon(d))

    def editicon(self,d):
      editable = self.request.user.may.edit(d['page'])
      if editable:
        if self.isEdit():
    		return """<td class="pageIconSelected">%s</td>""" % (
					'%s<br/>Edit' % self.make_icon('edit', style=png_behavior)
				  )
        else:
            return """<td class="pageIcon">%s</td>""" % (wikiutil.link_tag_explicit('style="text-decoration: none;"', self.request, wikiutil.quoteWikiname(d['page_name'])+'?action=edit',
              '%s<br/>Edit' % self.make_icon('edit', style=png_behavior)))
      else:
	      return ''

    def infoicon(self, d):
       if self.isInfo(): status = 'Selected' 
       else: status = ''
       return """<td class="pageIcon%s">%s</td>""" % (status, wikiutil.link_tag_explicit('style="text-decoration: none;"', self.request, wikiutil.quoteWikiname(d['page_name'])+'?action=info',
           '%s<br/>Info' % self.make_icon('info', style=png_behavior)))

    def talkicon(self, d):
      if not self.request.config.talk_pages: return ''

      if d['page'].isTalkPage():
         article_name = wikiutil.talk_to_article_pagename(d['page_name'])
         return """<td class="pageIcon">%s</td>""" % (wikiutil.link_tag_explicit('style="text-decoration: none;"', self.request, wikiutil.quoteWikiname(article_name),
         '%s<br/>Article' % self.make_icon('article', style=png_behavior)))
      else:
        talk_page = Page(wikiutil.article_to_talk_pagename(d['page_name']), self.request)
        if talk_page.exists():
          return """<td class="pageIcon">%s</td>""" % (wikiutil.link_tag_explicit('style="text-decoration: none;"', self.request, wikiutil.quoteWikiname(d['page_name'])+'/Talk',
         '%s<br/>Talk' % self.make_icon('talk', style=png_behavior)))
        else:
          # if the viewer can't edit the talk page, let's spare them from looking at a useless link to an empty page:
          if not self.request.user.may.edit(talk_page):
            return ''
          return """<td class="pageIcon">%s</td>""" % (wikiutil.link_tag_explicit('class="tinyNonexistent"', self.request, wikiutil.quoteWikiname(d['page_name'])+'/Talk',
         '%s<br/>Talk' % self.make_icon('talk', style=png_behavior)))


    def mapicon(self, d):
      if not config.has_old_wiki_map:
          action = 'doshow();loadMap();'
      else:
          action = 'doshow();';

      if self.showapplet:
        return """<td class="pageIcon" id="show"><a href="#" style="text-decoration: none;" onclick="%s">%s<br/>Map</a></td>
                  <td style="display: none;" class="pageIcon" id="hide"><a href="#" style="text-decoration: none;" onclick="dohide();">%s<br/>Map</a></td>""" % (action,self.make_icon('viewmap', style="behavior: url('%s/pngbehavior.htc');" % config.url_prefix), self.make_icon('hidemap', style="behavior: url('%s/pngbehavior.htc');" % config.url_prefix))
      else: return ''


    def title(self, d):
        """
        Assemble the title
        
        @param d: parameter dictionary
        @rtype: string
        @return: title html
        """
        _ = self.request.getText
        html = []
        if d['title_link']:
            if d['polite_msg']:
                polite_html = '<div style="font-size: 10px; color: #404040; clear:both;">\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(%s)\
</div>' % d['polite_msg']
            else:
                polite_html = ''

            # deal with subpages and links to them
            page_title_links = subpagelinks.SubpageLinks(self.request, d['title_text']).render()  # cut it up for subpage display
            subpage_title = []
            for pagename, display_pagename in page_title_links:
                subpage_title.append(Page(pagename, self.request).link_to(know_status=True, know_status_exists=True, text=display_pagename))

            pagename_html = '/'.join(subpage_title)

            html.append('<td id="title_text"><h1>%s</h1>%s</td>' % (
                pagename_html, polite_html))
            html.append(self.new_iconbar(d))
            
        else:
            html.append('<td id="title_text"><h1>%s</h1></td>' % wikiutil.escape(d['title_text']))
        return ''.join(html)

    def username(self, d):
        """
        Assemble the username / userprefs link
        
        @param d: parameter dictionary
        @rtype: string
        @return: username html
        """
        _ = self.request.getText
        if self.request.user.valid:
            watch_wiki = ''
            if config.wiki_farm:
                if not self.request.user.isWatchingWiki(self.request.config.wiki_name):
                    watch_wiki = """| %s """ % Page(d['page_name'], self.request).link_to(
                        know_status=True, know_status_exists=True,
                        text='watch this wiki',
                        querystr='action=watch_wiki&wikiname=%s' % self.request.config.wiki_name)

            if config.wiki_farm:
                wiki_base_url = farm.getBaseFarmURL(self.request)
            else:
                wiki_base_url = '%s/' % self.request.getScriptname()
            html = """
<div class="user_area">
<div class="welcome">Welcome, %s</div><div class="user_items">(<a href="%sUser_Preferences">settings</a> %s| <a href="%s/%s?action=userform&amp;logout=Logout">logout</a>)</div></div>""" % (user.getUserLink(self.request, self.request.user), wiki_base_url, watch_wiki, self.request.getScriptname(), d['q_page_name'])
        else:
            if config.wiki_farm:
                post_url = farm.getBaseFarmURL(self.request)
                our_wiki_url = '%s/%s' % (self.request.getBaseURL(), d['q_page_name'])
                base_wiki = post_url
                farm_params = """
<input type="hidden" name="backto_wiki" value="%s">
<input type="hidden" name="backto_page" value="%s">
<input type="hidden" name="qs" value="%s">
""" % (self.request.config.wiki_name, urllib.quote(our_wiki_url), urllib.quote(self.request.query_string))
            else:
                farm_params = ''
                post_url = '%s/%s' % (self.request.getScriptname(), d['q_page_name'])
                base_wiki = '%s/' % self.request.getScriptname()
            html = """<form action="%s" method="POST" onsubmit="if (!canSetCookies()) { alert('You need cookies enabled to log in.'); return false;}">
<input type="hidden" name="action" value="userform">
<div class="login_area">
<table>
<tr><td width="50%%" align="right" nowrap>User name:</td>
<td colspan="2" align="left" nowrap><input class="formfields" size="22" name="username" type="text"></td> </tr> <tr>
<td align="right">Password:</td>
<td colspan="2" align="left" nowrap> <input class="formfields" size="22" type="password" name="password"> 
<input type="hidden" name="login" value="Login">%s
</td></tr><tr><td></td><td align="left" nowrap>(<a href="%sUser_Preferences?new_user=1">new user</a>)</td><td align="right"><input type="submit" name="login" value="Login" alt="login"></td></tr></table></div></form>""" % (post_url, farm_params, base_wiki)
            
        return html

    def isEdit(self):
        """
        Are we in the page editing interface?
        """
        if (self.request.form.has_key('action') and self.request.form['action'][0] == 'edit') or (self.request.form.has_key('action') and self.request.form['action'][0] == 'savepage' and self.request.form.has_key('button_preview')):
          return True
        else:
          return False

    def isInfo(self):
        """
        Are we in the info interface?
        """
        if self.request.form.has_key('action') and (self.request.form['action'][0] == 'info' or self.request.form['action'][0] == 'Files' or self.request.form['action'][0] == 'userinfo'):
          return True
        else:
          return False
        
    def navbar(self, d):
        """
        Assemble the new nav bar
        
        @param d: parameter dictionary
        @rtype: string
        @return: navibar html
        """
        _ = self.request.getText

        lower_page_name = d['page_name'].lower()
        
        if self.request.user.valid:
            html = ['<div class="tabArea">']
            in_preset_tab = False
            for tab in self.request.config.tabs_user:
              tabclass = 'tab'
              lower_tab = tab.lower()
              if lower_tab == lower_page_name:
                tabclass = '%s activeTab' % tabclass
                in_preset_tab = True
              if lower_tab == 'bookmarks' and  self.request.user.hasUnseenFavorite():
                tabclass = '%s notice' % tabclass

              html.append('<a href="%%(script_name)s/%s" class="%s">%s</a> ' % (wikiutil.quoteWikiname(tab), tabclass, tab))

            if not in_preset_tab and d['page_name']:
              html.append('<a href="%(script_name)s/%(q_page_name)s" class="tab activeTab">%(page_name)s</a> ')
        else:
            html = ['<div class="tabArea">']
            in_preset_tab = False
            for tab in self.request.config.tabs_nonuser:
              tabclass = 'tab'
              lower_tab = tab.lower()
              if lower_tab == lower_page_name:
                tabclass = '%s activeTab' % tabclass
                in_preset_tab = True

              html.append('<a href="%%(script_name)s/%s" class="%s">%s</a> ' % (wikiutil.quoteWikiname(tab), tabclass, tab))

            if not in_preset_tab and d['page_name']:
              html.append('<a href="%(script_name)s/%(q_page_name)s" class="tab activeTab">%(page_name)s</a> ')


        html.append('</div>')
        html = ''.join(html) % d

        return html


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
        return wikiutil.link_tag(self.request, page_params % d, d['i18ntitle'], attrs='title="%(title)s"' % d)


    def edittext_link(self, d, **keywords):
        """
        Assemble EditText link (or indication that page cannot be edited)
        
        @param d: parameter dictionary
        @rtype: string
        @return: edittext link html
        """
        _ = self.request.getText
        html = []
        actions_in_footer = False
        if keywords.get('editable', 1):
            editable = self.request.user.may.edit(d['page'])
            if editable:
              d['last_edit_info'] = d['page'].last_modified_str()
            else: d['last_edit_info'] = ''

            html.append('<script language="JavaScript" type="text/javascript">\nvar donate2=new Image();donate2.src="%s";var donate=new Image();donate.src="%s";</script><div id="footer"><table width="100%%" border="0" cellspacing="0" cellpadding="0"><tr>' % (self.img_url('donate2.png'), self.img_url('donate.png')))
            # noedit is a keyword that tells us if we are in an area where an edit link just logically makes no sense, such as the info tab.
            leftwidth = '10'
            if not keywords.get('noedit'):
                if editable:
                  if d['last_edit_info']:
                    leftwidth = '50'
                  else:
                    leftwidth = '24'
                else:
                    if not self.request.user.isFavoritedTo(d['page']):
                      leftwidth = '20'
                    else:
                      leftwidth = '10'
            html.append('<td align="left" width="%s%%">' % leftwidth)

            if not keywords.get('noedit'):
                if editable:
                    actions_in_footer = True
                    html.append("%s" % (
                        wikiutil.link_tag(self.request, d['q_page_name']+'?action=edit', _('Edit'))))

                if not self.request.user.anonymous:
                    if not self.request.user.isFavoritedTo(d['page']):
                      actions_in_footer = True
                      if editable:
                        html.append(" or %s" % (
                            wikiutil.link_tag(self.request, d['q_page_name']+'?action=favorite', _('Bookmark'))))
                      else: 
                        html.append("%s" % (
                            wikiutil.link_tag(self.request, d['q_page_name']+'?action=favorite', _('Bookmark'))))

                if actions_in_footer: html.append(' this page')

                if d['last_edit_info']:
                    html.append(' %(last_edit_info)s' % d)
        
            cc_button = '<a href="http://creativecommons.org/licenses/by/2.0/"><img alt="Creative Commons License" border="0" src="%s"/></a>' % self.img_url('cc.png')
            if self.request.config.license_text:
              html.append('<td align="center" valign="middle"><div class="license">%s</div></td>' % self.request.config.license_text)
              if self.request.config.footer_buttons:
                html.append('<td align="right" valign="middle" width="%spx" style="padding-right: 5px;">%s</td></tr></table></div>' % (len(self.request.config.footer_buttons)*100, ' '.join(self.request.config.footer_buttons)))
              else:
                if not actions_in_footer:
                    html.append('<td align="right" valign="middle" width="%s%%" style="padding-right: 5px;"> </td></tr></table></div>' % leftwidth)
                else:
                    html.append('<td align="right" valign="middle" width="20px" style="padding-right: 5px;"> </td></tr></table></div>')
            else:
              if self.request.config.footer_buttons:
                html.append('<td align="right" valign="middle" width="%spx" style="padding-right: 5px;">%s</td></tr></table></div>' % (len(self.request.config.footer_buttons)*100, ' '.join(self.request.config.footer_buttons)))
              else:
                html.append('</tr></table></div>')

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
        dict['newtitle'] = None
        dict['newtitle'] = dict['title']
        if dict['title'] == 'Front Page':
            dict['newtitle'] = self.request.config.catchphrase
        
        dict['web_dir'] = config.web_dir

        if d['page'].hasMapPoints() and not self.request.config.has_old_wiki_map:
            dict['wiki_name'] = self.request.config.wiki_name
            if config.wiki_farm:
                dict['map_base'] = farm.getBaseFarmURL(self.request)
            else:
                dict['map_base'] = self.request.getBaseURL()
            dict['gmaps_api_key'] = self.request.config.gmaps_api_key or config.gmaps_api_key
            dict['map_html'] = """<script src="http://maps.google.com/maps?file=api&v=2&key=%(gmaps_api_key)s" type="text/javascript"></script>
<script src="%(web_dir)s/wiki/gmap.js" type="text/javascript"></script>
<script type="text/javascript">var map_url="%(map_base)s?action=gmaps&wiki=%(wiki_name)s";var point_count=1;</script>""" % dict
        else:
            dict['map_html']  = ''

        if dict['newtitle'] is self.request.config.catchphrase: 
          if self.request.config.catchphrase:
                html = """
<title>%(sitename)s - %(newtitle)s</title><script
src="%(web_dir)s/wiki/utils.js" type="text/javascript"></script>
%(map_html)s
%(stylesheets_html)s
                """ % dict
          else:
                html = """
<title>%(sitename)s</title><script
src="%(web_dir)s/wiki/utils.js" type="text/javascript"></script>
%(map_html)s
%(stylesheets_html)s
                """ % dict

        else:
                html = """
<title>%(newtitle)s - %(sitename)s</title><script
src="%(web_dir)s/wiki/utils.js" type="text/javascript"></script>
%(map_html)s
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
        title_str = '"%s"' %  d['title_text']
        if d['page_name'] and d['page'].hasMapPoints() and not self.isEdit():
           self.showapplet = True
        apphtml = ''
        if self.showapplet:
           if config.has_old_wiki_map:
               map_html = """<applet code="WikiMap.class" archive="%s/wiki/map.jar" height=460 width=810 border="1"><param name="map" value="%s/wiki/map.xml"><param name="points" value="%s/Map?action=mapPointsXML"><param name="highlight" value="%s"><param name="wiki" value="%s">You do not have Java enabled.</applet>"""% (config.web_dir, config.web_dir, d['script_name'], d['page_name'], d['script_name'])
               apphtml = '<div id="map" style="width: 810px; height: 460px; display: none; margin-top: -1px;">%s</div>' % map_html 
           else:
                apphtml = '<div id="mapContainer" style="width: 478px; height: 330px; display: none;"><div id="map" style="width: 450px; height: 300px; position: relative; display: none;"></div></div>'

        dict = {
            'config_header1_html': self.emit_custom_html(config.page_header1),
            'config_header2_html': self.emit_custom_html(config.page_header2),
            # 'logo_html':  self.logo(d),
            'banner_html': self.banner(d),
            'title_html':  self.title(d),
            'username_html':  self.username(d),
            'navbar_html': self.navbar(d),
            'iconbar_html': self.iconbar(d),
            'msg_html': self.msg(d),
            'search_form_html': self.searchform(d),
            'applet_html': apphtml,
        }

# %(logo_html)s ### from...
        html = """
%(config_header1_html)s
<div id="banner">
<table class="logo">
<tr>
<td class="logo_banner">
%(banner_html)s
</td>
<td class="user_banner" align="right" valign="top">
%(username_html)s
</td>
</tr>
</table>
%(navbar_html)s
</div>
<div id="title">
<table id="title_area_table">
<tr>
<td>
<table id="title_table">
<tr id="iconRow">
%(title_html)s
</tr></table>
</td>
<td id="search_form">
%(search_form_html)s
</td>
</tr></table></div>
%(config_header2_html)s
%(applet_html)s
%(msg_html)s
""" % dict
        # Next parts will use config.default_lang direction, as set in the <body>
        return html

    # Footer stuff #######################################################
    
    def searchform(self, d, wiki_global=False):
        """
        assemble HTML code for the search forms
        
        @param d: parameter dictionary
        @rtype: string
        @return: search form html
        """
        _ = self.request.getText
        dict = {
            'search_title': _("Search"),
            'search_html': _("Search: %(textsearch)s&nbsp;&nbsp;") % d,
        }
        if wiki_global:
            dict['search_action'] = 'global_search'
        else:
            dict['search_action'] = 'search'
        dict.update(d)
        
        html = """
<form method="GET" action="%(script_name)s/%(q_page_name)s">
<input type="hidden" name="action" value="%(search_action)s">
%(search_html)s
</form>
""" % dict

        return html


    def footer(self, d, **keywords):
        """
        Assemble page footer
        
        @param d: parameter dictionary
        @keyword ...:...
        @rtype: string
        @return: page footer html
        """

        return """%s<div class="wikiGlobalFooter" align="center">%s</div>""" % (self.edittext_link(d, **keywords), config.page_footer1)
        
def execute(request):
    """
    Generate and return a theme object
        
    @param request: the request object
    @rtype: MoinTheme
    @return: Theme object
    """
    return Theme(request)
    
def is_word_in_file(file, word):
      """
      Pass me a file location and i tell you if word is in that file
      """
      f = open(file)
      lines = f.readlines()
      f.close()
      for line in lines:
         if string.find(line, word) >= 0:
            return 1
      return 0

