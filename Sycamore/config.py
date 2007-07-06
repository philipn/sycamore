# -*- coding: utf-8 -*-
"""
    Sycamore - Configuration defaults and handling

    Load sycamore_config.py and add any missing values with their defaults.
    
    !!! DO NOT EDIT THIS EXCEPT IF YOU ARE A SYCAMORE DEVELOPER !!!
    
    This file is sycamore code (it sets the default values for all
    config values) and NOT a configuration file.
    
    Please use sycamore_config.py to configure your wiki.

    @copyright: 2005-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import time
import cPickle
from copy import copy

# Try to import sycamore_config.
# If it fails, either someone forgot sycamore_config,
# or someone who doesn't know sycamore_config might be required,
# tried to import us or something (Page, for example) which imports us.
default_config = 0
try:
    from sycamore_config import *
except ImportError, e:
    default_config = 1
    msg = ('import of sycamore_config failed due to "%s";'
          ' default configuration used instead.' % e)
    import warnings
    warnings.warn(msg)
    del warnings
    del msg

if not vars().has_key('url_prefix'):
    url_prefix = '.'

# this is a trick to mark some text for the gettext tools so that they dont
# get orphaned. See http://www.python.org/doc/current/lib/node278.html.
def _(text):
    return text

def reduce_to_local_config(d):
    """
    Takes dict d and removes all elements that aren't local
    configuation options.
    """
    new_d = {}
    for name in _cfg_defaults_local:
        new_d[name] = d[name]
    return new_d


class Config(object):
    def __init__(self, wiki_name, request, process_config=True, fresh=False):
        from wikiutil import getTimeOffset
        self.wiki_id = None
        self.__dict__.update(
            self._get_config(wiki_name, request, process_config, fresh=fresh))
        self.tz_offset = getTimeOffset(self.tz)
        if stop_hotlinking:
            # Referer regular expression is used to filter out http
            # referers from image viewing.
            # It's for stopping image hotlinking, basically.
            self.referer_regexp = '^%s((\/.*)|())$' % (
                re.escape(request.getQualifiedURL()))
        else:
            self.referer_regexp = ''

    def get_dict(self):
        essentials = {}
        for key in _cfg_defaults_local:
            if self.__dict__.has_key(key):
                essentials[key] = self.__dict__[key]
            else:
                essentials[key] = _cfg_defaults_local[key]
    
        return essentials

    def _get_config(self, wiki_name, request, process_config, fresh=False):
        from Sycamore.wikiutil import mc_quote
        if not fresh and request.req_cache['wiki_config'].has_key(wiki_name):
            return request.req_cache['wiki_config'][wiki_name]
        d = { 'name': wiki_name , 'wiki_name': wiki_name }
        settings_dict = None

        # set each config object to have the same basic configuration variables
        d.update(reduce_to_local_config(CONFIG_VARS))  

        if process_config:
            if not fresh and memcache:
                settings_dict = request.mc.get("settings:%s" % (
                    mc_quote(wiki_name)), wiki_global=True)
            if settings_dict is None:
                request.cursor.execute("""SELECT id, is_disabled, sitename,
                                                 domain, other_settings
                                                 from wikis
                                                 where name=%(name)s""", d)
                result = request.cursor.fetchone()
                if result:
                    (id, is_disabled, sitename, domain,
                     other_settings_pickled) = result
                    other_settings = cPickle.loads(
                        _binaryToString(other_settings_pickled))
                    d.update(other_settings)
                    d['wiki_id'] = id
                    d['is_disabled'] = is_disabled
                    d['sitename'] = sitename
                    d['domain'] = domain
                    d['wiki_name'] = wiki_name
                    d['name'] = wiki_name
                    settings_dict = d
                else:
                    settings_dict = {}
                if memcache:
                    request.mc.add("settings:%s" % mc_quote(wiki_name),
                                   settings_dict, wiki_global=True)
            else:
                d.update(settings_dict)

        request.req_cache['wiki_config'][wiki_name] = d
        return d

    def zap_config(self, request):
        """
        Because of the way we store some of our configuration options,
        it makes sense to 'zap' the configuration back into place on a wiki
        after we've added a new configuration option in config.py.

        Generally, don't mess with this unless you're a Sycamore developer.
        """
        # grab the basic configuration options
        local_vars = reduce_to_local_config(CONFIG_VARS)  
        d = copy(local_vars)
        d.update(self.get_dict()) # ensure we get new options
        for k in d:
            if k not in local_vars:
                # ensure we remove old config options
                del d[k]

        self.set_config(self.wiki_name, d, request)

    def set_config(self, wiki_name, d, request):
        from wikidb import Binary
        d['name'] = wiki_name
        request.cursor.execute("SELECT name from wikis where name=%(name)s", d)
        result = request.cursor.fetchall()
        d['other_settings'] = Binary(cPickle.dumps(d, True))
        original_domain = request.config.domain

        if result and result[0]:
            new_wiki = False
            request.cursor.execute("""UPDATE wikis set
                is_disabled=%(is_disabled)s, sitename=%(sitename)s,
                domain=%(domain)s, other_settings=%(other_settings)s
                where name=%(name)s""", d, isWrite=True)
        else: 
            if d.has_key('wiki_id') and d['wiki_id']:
                # we are giving a wiki id..assume it's valid
                request.cursor.execute("""INSERT into wikis
                    (name, id, is_disabled, sitename, domain, other_settings)
                    values (%(name)s, %(wiki_id)s, %(is_disabled)s,
                            %(sitename)s, %(domain)s, %(other_settings)s)""",
                    d, isWrite=True)
            else:
                # new wiki id
                if db_type == 'mysql':
                    request.cursor.execute("""INSERT into wikis (name, id,
                        is_disabled, sitename, domain, other_settings)
                        values (%(name)s, NULL, %(is_disabled)s, %(sitename)s,
                                %(domain)s, %(other_settings)s)""",
                        d, isWrite=True)
                else:
                    request.cursor.execute("""INSERT into wikis (name, id,
                        is_disabled, sitename, domain, other_settings)
                        values (%(name)s, NEXTVAL('wikis_seq'),
                                %(is_disabled)s, %(sitename)s, %(domain)s,
                                %(other_settings)s)""", d, isWrite=True)
                request.cursor.execute("""SELECT id from wikis where
                    name=%(name)s""", d)
                d['wiki_id'] = request.cursor.fetchone()[0]

        del d['other_settings']
        if original_domain != d['domain'] and d['domain']:
            request.req_cache['wiki_domains'][d['domain']] = d['wiki_name']
        if memcache:
            request.mc.set("settings:%s" % wiki_name, d, wiki_global=True) 
            if original_domain != d['domain'] and d['domain']:
                request.mc.set("wiki_domains:%s" % d['domain'],
                    d['wiki_name'], wiki_global=True)

        request.config.__dict__.update(d)
        request.req_cache['wiki_config'][d['wiki_name']] = \
            request.config.__dict__

# default config values
# to change the way these are displayed/what is displayed in the wiki,
# see sitesettings.py 

_cfg_defaults_global = {
    'acl_rights_valid': ['read', 'edit', 'delete', 'admin'],
    'allow_numeric_entities': 1,
    'allow_web_based_wiki_creation': False,
    'allowed_actions': [],
    'allow_xslt': 0,
    'auth_http_enabled': 0,
    'bang_meta': 0,
    'caching_formats' : ['text_html'],
    'captcha_support': 1,
    'changed_time_fmt': '%H:%M',
    'charset': 'utf-8',
    # if you have gdchart, add something like
    # chart_options = {'width': 720, 'height': 540}
    'chart_options': None,
    'cookie_lifetime': 12, # 12 hours from now
    'data_dir': './wiki/data/',
    'date_fmt': '%Y-%m-%d',
    'datetime_fmt': '%Y-%m-%d %H:%M:%S',
    'diff3_location': '/usr/bin/diff3',
    'db_name': 'wiki',
    'db_charset': 'utf-8',
    'db_host': 'localhost',
    'db_type': 'postgres',
    'db_user': 'root',
    'db_user_password': '',
    'db_socket': '',
    'db_pool': False,
    'db_pool_size': 50,
    'db_max_overflow': -1,
    'default_lang': 'en',
    'do_gzip': True,
    'default_markup': 'wiki',
    'edit_rows': 24,
    'gmaps_api_key': None,
    'has_xapian': False,
    'hosts_deny': [],
    'html_head': '',
    'html_pagetitle': None,
    'httpd_host': 'localhost',
    'httpd_port': 8080,
    'httpd_user': None,
    # XXX UNICODE fix
    'lowerletters': ('0-9a-z\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe8\xe9\xea\xeb\xec'
                     '\xed\xee\xef\xf2\xf3\xf4\xf5\xf6'
                     '\xf8\xf9\xfa\xfb\xfc\xfd\xff\xb5\xdf\xe7\xf0\xf1\xfe'),
    'mail_login': None, # or "user pwd" if you need to use SMTP AUTH
    'mail_smarthost': None,
    'mail_smarthost_auth': None,
    'mail_from': None,
    'max_macro_size': 50,
    'max_page_size': 320, # max page size in Kb
    'max_file_size': 500,  # max file size in Kb
    'memcache': False,
    'memcache_servers': [],
    'nonexist_qm': 0,

    'page_credits': ('<a href="http://projectsycamore.org">'
                     'Sycamore Powered</a><br>'),
    'page_footer1': '',
    'page_footer2': '',

    'page_header1': '',
    'page_header2': '',
    
    'page_template_prefix': 'Templates/',

    'page_user_preferences': 'User Settings',

    # These icons will show in this order in the iconbar, unless they
    # are not relevant, e.g email icon when the wiki is not configured
    # for email.
    'page_iconbar': ["edit", "view", "diff", "info", "raw", "print"],

    # Standard buttons in the iconbar
    'page_icons_table': {
        # key           last part of url, title, icon-key
        'diff':("%(q_page_name)s?action=diff", _("Diffs"), "diff"),
        'info':("%(q_page_name)s?action=info", _("Info"), "info"),
        'edit':("%(q_page_name)s?action=edit", _("Edit"), "edit"),
        'raw': ("%(q_page_name)s?action=raw", _("Raw"), "raw"),
        'xml': ("%(q_page_name)s?action=format&amp;mimetype=text/xml",
            _("XML"), "xml"),
        'print':("%(q_page_name)s?action=print", _("Print"), "print"),
        'view':("%(q_page_name)s", _("View"), "view"),
        },
    'paypal_address': 'donate@example.com',
    'paypal_name': 'Wiki Spot',
    'processors': False,
    'refresh': None, # (minimum_delay, type), e.g.: (2, 'internal')
    'relative_dir': 'index.cgi',
    'remote_search': False,
    'search_db_location': None,
    'shared_intermap': None, # can be string or list of strings (filenames)
    'show_hosts': 1,
    'show_section_numbers': 0,
    'show_timings': 0,
    'show_version': 0,
    'sox_location': '/usr/local/bin/sox',
    'stop_hotlinking': True,
    'tmp_dir': 'tmp',
    'theme_force': True,
    'trail_size': 5,
    # use X_FORWARDED_FOR for request.remote_addr if provided.
    'trust_x_forwarded_for': False, 
    # a regex of HTTP_USER_AGENTS that should be excluded from logging,
    # and receive a FORBIDDEN for anything except viewing a page
    'ua_spiders': ('archiver|crawler|google|htdig|httrack|jeeves|larbin|'
        'leech|linkbot') +
        ('|linkmap|linkwalk|mercator|mirror|robot|scooter|search|sitecheck'
        '|spider|wget'),
    'umask': 0775, # with 0777 ACLs are rather pointless!
    # XXX UNICODE fix
    'upperletters': ('A-Z\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc8\xc9'
                    '\xca\xcb\xcc\xcd\xce\xcf\xd2\xd3\xd4\xd5\xd6\xd8'
                    '\xd9\xda\xdb\xdc\xdd\xc7\xd0\xd1\xde'),
    'url_prefix': '/wiki',
    'url_schemas': [],
    'url_mappings': {},
    'user_page_prefix': 'Users/',
    'use_ssl': False,
    'valid_image_extensions': ['.gif', '.jpe', '.jpeg', '.jpg', '.png'],
    'web_dir' : '',
    'web_root': '/var/www/html',
    'wiki_farm': False,
    'wiki_farm_from_wiki_msg': ('<div style="float: right; width: 12em; '
                                'padding: 1em; border: 1px dashed gray; '
                                'background-color: #ccddff;">%(wiki_name)s '
                                'is a part of %(base_wiki_sitename)s.  '
                                'Your account here '
                                'will work on %(wiki_name)s, the '
                                '%(base_wiki_name)s hub, and all the other '
                                'wikis that are part of '
                                'the %(base_wiki_sitename_link)s network.'
                                '</div>'),
    'wiki_farm_dir': 'wikis',
    'wiki_base_domain': 'localhost',
    'wiki_farm_subdomains': False,
    'wiki_farm_clean_uploaded_code': True,
    'wiki_farm_no_exist_msg': ('<p>The wiki %s does not exist!</p>',
        'wiki_name'),
    'wiki_settings_page': 'Wiki Settings',
    'wiki_settings_page_images': 'Images',
    'wiki_settings_page_css': 'CSS',
    'wiki_settings_page_general': 'General',
    'wiki_settings_page_security_defaults': 'Security',
    'wiki_settings_page_user_groups': 'User Groups',
    'SecurityPolicy': None,
}

# remove that hack again
del _

for key, val in _cfg_defaults_global.items():
    if not vars().has_key(key):
        vars()[key] = val

_cfg_defaults_local = {
    'active': False,
    'acl_rights_default': {'Admin': (True, True, True, True),
                           'Known': (True, True, True, False),
                           'Banned': (True, False, False, False),
                           'All': (True, True, False, False)},
    'address_locale': '',
    'allow_subpages': 1,
    # extensions that are allowed in user uploads
    'allowed_extensions': ['.jpg', '.jpeg', '.png', '.gif'],
    # mimetypes allowed in uploads, this list will automagically have the 
    # mimetype values corresponding to allowed extensions added to it.
    'allowed_mimetypes': [],
    # set to True to allow any extension / mimetype of uploaded files
    'allow_all_mimetypes': False, 
    'catchphrase': 'Your phrase here...',
    'theme_files_last_modified': {},
    'edit_agreement_text': '',
    'gmaps_api_key': None,
    'interwikimap': 'Interwiki Map',
    'is_disabled': False,
    'logo_sizes': {},
    'license_text': '',
    'noindex_everywhere': False,
    'has_old_wiki_map': False,
    'page_front_page': 'Front Page',
    'page_local_spelling_words': 'Local Spelling Words',
    'sitename': 'Sycamore default install',
    'talk_pages': True,
    'theme_default': 'egghead',
    'tz': 'UTC',
    'tabs_nonuser': ['Front Page', 'People', 'Recent Changes'],
    'tabs_user': ['Front Page', 'People', 'Bookmarks', 'Recent Changes'],
    'footer_buttons': [],
    'wiki_name': 'sycamore',
    'wiki_id': 1,
    'domain': None,
}

local_config_checkbox_fields = [
         ('noindex_everywhere', lambda _: _('Don\'t let search engines index '
                                            'this wiki')),
         ('talk_pages', lambda _: _('Use "Talk" pages on this wiki')),
         ('is_disabled', lambda _: _('Delete this wiki')),
]

# Iterate through defaults, setting any absent variables
for key, val in _cfg_defaults_local.items():
    if not vars().has_key(key):
        vars()[key] = val


CONFIG_VARS = vars()

# Validate configuration - in case of admin errors
# Set charset and language code to lowercase
charset = charset.lower()
default_lang = default_lang.lower()

del key
del val

# create list of excluded actions by first listing all "dangerous"
# actions, and then selectively remove those the user allows
excluded_actions = ['DeletePage', 'AttachFile', 'RenamePage',]
for _action in allowed_actions:
    try:
        excluded_actions.remove(_action)
    except ValueError:
        pass

# define directories
import os, sys
data_dir = os.path.normpath(data_dir)

sycamore_dir = os.path.abspath(os.path.dirname(__file__))

for _dirname in ('plugin'):
    _varname = _dirname + '_dir'
    if not vars().has_key(_varname):
        vars()[_varname] = os.path.join(data_dir, _dirname)

sys.path.append(data_dir)

del os, sys, _dirname, _varname

def _binaryToString(b):
  """Just like binaryToString in wikidb.py..."""
  if db_type == 'postgres':
    return str(b)
  elif db_type == 'mysql':
    if not hasattr(b, 'tostring'): return b
    return b.tostring()
