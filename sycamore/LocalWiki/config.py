# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Configuration defaults and handling

    Load localwiki_config.py and add any missing values with their defaults.
    
    !!! DO NOT EDIT THIS EXCEPT IF YOU ARE A MOIN DEVELOPER !!!
    
    This file is moinmoin code (it sets the default values for all
    config values) and NOT a configuration file.
    
    Please use localwiki_config.py to configure your wiki.

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Try to import localwiki_config. If it fails, either someone forgot localwiki_config,
# or someone who doesn't know localwiki_config might be required, tried to import
# us or something (Page, for example) which imports us. One example of such
# a non-Moin-aware importer is pydoc, as shipped with Python 2.1. Continuing
# with reasonable defaults is a friendly way of letting people browse the
# LocalWiki class library with pydoc, and is also friendly to people who for
# some reason forgot they need localwiki_config. 
default_config = 0
try:
    from localwiki_config import *
except ImportError, e:
    default_config = 1
    msg = 'import of localwiki_config failed due to "%s";' \
          ' default configuration used instead.' % e
    import warnings
    warnings.warn(msg)
    del warnings
    del msg

if not vars().has_key('url_prefix'):
    url_prefix = '.'

# this is a trick to mark some text for the gettext tools so that they dont
# get orphaned. See http://www.python.org/doc/current/lib/node278.html.
def _(text): return text

import time

# default config values
_cfg_defaults = {
    'acl_enabled': 0,
    'acl_rights_default': "Trusted:read,write,delete,revert Known:read,write,delete,revert All:read,write",
    'acl_rights_before': "",
    'acl_rights_after': "",
    'acl_rights_valid': ['read', 'write', 'delete', 'revert', 'admin'],
    'allow_extended_names': 1,
    'allow_subpages': 1,
    'allow_numeric_entities': 1,
    'allowed_actions': [],
    # extensions that are allowed in user uploads
    'allowed_extensions': ['.jpg', '.jpeg', '.png', '.gif'],
    # mimetypes allowed in uploads, this list will automagically have the 
    # mimetype values corresponding to allowed extensions added to it.
    'allowed_mimetypes': [],
    'allow_xslt': 0,
    'app_dir': '/home/dwiki',
    'attachments': None, # {'dir': path, 'url': url-prefix, 'img_script': name of the image getting script}
    'auth_http_enabled': 0,
    'bang_meta': 0,
    'backtick_meta': 1,
    'caching_formats' : ['text_html'],
    'catchphrase': 'The definitive resource for Davis, California',
    'changed_time_fmt': '%H:%M',
    'charset': 'iso-8859-1',
    # if you have gdchart, add something like
    # chart_options = {'width': 720, 'height': 540}
    'chart_options': None,
    'cookie_lifetime': 12, # 12 hours from now
    'data_dir': './wiki/data/',
    'date_fmt': '%Y-%m-%d',
    'datetime_fmt': '%Y-%m-%d %H:%M:%S',
    'db_name': 'wiki',
    'db_host': 'localhost',
    'db_user': 'root',
    'db_user_password': '',
    'default_lang': 'en',
    'default_logo': 'defaultlogo.png',
    'default_markup': 'wiki',
    'domain': 'localhost',
    'edit_locking': 'warn 10', # None, 'warn <timeout mins>', 'lock <timeout mins>'
    'edit_rows': 30,
    'hosts_deny': [],
    'html_head': '',
    'html_pagetitle': None,
    'httpd_host': 'localhost',
    'httpd_port': 8080,
    'httpd_user': 'nobody',
    'httpd_docs': './wiki-moinmoin',
    'interwikiname': None,
    'logo_string': '<img src="/wiki/classic/img/moinmoin.png" alt="LocalWiki">',
    # XXX UNICODE fix
    'lowerletters': '0-9a-z\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf2\xf3\xf4\xf5\xf6\xf8\xf9\xfa\xfb\xfc\xfd\xff\xb5\xdf\xe7\xf0\xf1\xfe',
    'mail_login': None, # or "user pwd" if you need to use SMTP AUTH
    'mail_smarthost': None,
    'mail_from': None,
    'max_macro_size': 50,
    'navi_bar': [
        'Front Page',
        'Recent Changes',
        'Find Page',
        'Wiki Guide',
    ],
    'nonexist_qm': 0,

    'page_credits': """<a href="http://dev.daviswiki.org">LocalWiki Powered</a><br>
    <a href="http://www.python.org/">
        <img src="%s/classic/img/PythonPowered.png" width="55" height="22" alt="PythonPowered">
    </a>""" % (url_prefix,),
    
    'page_footer1': '',
    'page_footer2': '',

    'page_header1': '',
    'page_header2': '',
    
    'page_front_page': 'Front Page',
    'page_user_prefernces': 'User Preferences',
    'page_local_spelling_words': 'LocalSpellingWords',
    'page_category_regex': '^Category[A-Z]',
    'page_dict_regex': '[a-z]Dict$',
    'page_form_regex': '[a-z]Form$',
    'page_group_regex': '[a-z]Group$',
    'page_template_regex': 'Template$',

    'page_license_enabled': 0,
    'page_license_page': 'WikiLicense',

    # These icons will show in this order in the iconbar, unless they
    # are not relevant, e.g email icon when the wiki is not configured
    # for email.
    'page_iconbar': ["edit", "view", "diff", "info", "raw", "print"],

    # Standard buttons in the iconbar
    'page_icons_table': {
        # key           last part of url, title, icon-key
        'diff':        ("%(q_page_name)s?action=diff", _("Diffs"), "diff"),
        'info':        ("%(q_page_name)s?action=info", _("Info"), "info"),
        'edit':        ("%(q_page_name)s?action=edit", _("Edit"), "edit"),
        'raw':         ("%(q_page_name)s?action=raw", _("Raw"), "raw"),
        'xml':         ("%(q_page_name)s?action=format&amp;mimetype=text/xml", _("XML"), "xml"),
        'print':       ("%(q_page_name)s?action=print", _("Print"), "print"),
        'view':        ("%(q_page_name)s", _("View"), "view"),
        },
    # this is for prevention of hotlinking.  leave blank if you don't care about people leeching images.
    # to match against any url from any subdomain of daviswiki we would write:
    # 'http\:\/\/(([^\/]*\.)|())daviswiki\.org\/.*'
    'referer_regexp': '',
    'refresh': None, # (minimum_delay, type), e.g.: (2, 'internal')
    'relative_dir': 'index.cgi',
    'shared_intermap': None, # can be string or list of strings (filenames)
    'show_hosts': 1,
    'show_section_numbers': 1,
    'show_timings': 0,
    'show_version': 0,
    'sitename': 'Davis Wiki',
    'smileys': {},
    'talk_pages': 1,
    'theme_default': 'classic',
    'theme_force': False,
    'trail_size': 5,
    'trust_x_forwarded_for': True, # use X_FORWARDED_FOR for request.remote_addr if provided.
    'tz_offset': -28800, # default time zone offset in unix time from UTC.  e.g. 3600 = 1 hour. 
    # a regex of HTTP_USER_AGENTS that should be excluded from logging,
    # and receive a FORBIDDEN for anything except viewing a page
    'ua_spiders': 'archiver|crawler|google|htdig|httrack|jeeves|larbin|leech|linkbot' +
                  '|linkmap|linkwalk|mercator|mirror|robot|scooter|search|sitecheck|spider|wget',
    'umask': 0775, # with 0777 ACLs are rather pointless!
    # XXX UNICODE fix
    'upperletters': 'A-Z\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd2\xd3\xd4\xd5\xd6\xd8\xd9\xda\xdb\xdc\xdd\xc7\xd0\xd1\xde',
    'url_prefix': '/wiki',
    'url_schemas': [],
    'url_mappings': {},
    'web_dir' : '',
    'web_root': '/var/www/html',
    'LogStore': 'text:editlog',
    'SecurityPolicy': None,
}



smiley_defaults = {
    "X-(":  (15, 15, 0, "angry.png"),
    ":D":   (15, 15, 0, "biggrin.png"),
    "<:(":  (15, 15, 0, "frown.png"),
    ":o":   (15, 15, 0, "redface.png"),
    ":(":   (15, 15, 0, "sad.png"),
    ":)":   (15, 15, 0, "smile.png"),
    "B)":   (15, 15, 0, "smile2.png"),
    ":))":  (15, 15, 0, "smile3.png"),
    ";)":   (15, 15, 0, "smile4.png"),
    "/!\\": (15, 15, 0, "alert.png"),
    "<!>":  (15, 15, 0, "attention.png"),
    "(!)":  (15, 15, 0, "idea.png"),

    # copied 2001-11-16 from http://pikie.darktech.org/cgi/pikie.py?EmotIcon
    ":-?":  (15, 15, 0, "tongue.png"),
    ":\\":  (15, 15, 0, "ohwell.png"),
    ">:>":  (15, 15, 0, "devil.png"),
    "|)":   (15, 15, 0, "tired.png"),
    
    # some folks use noses in their emoticons
    ":-(":  (15, 15, 0, "sad.png"),
    ":-)":  (15, 15, 0, "smile.png"),
    "B-)":  (15, 15, 0, "smile2.png"),
    ":-))": (15, 15, 0, "smile3.png"),
    ";-)":  (15, 15, 0, "smile4.png"),
    "|-)":  (15, 15, 0, "tired.png"),
    
    # version 1.0
    "(./)":  (20, 15, 0, "checkmark.png"),
    "{OK}":  (14, 12, 0, "thumbs-up.png"),
    "{X}":   (16, 16, 0, "icon-error.png"),
    "{i}":   (16, 16, 0, "icon-info.png"),
    "{1}":   (15, 13, 0, "prio1.png"),
    "{2}":   (15, 13, 0, "prio2.png"),
    "{3}":   (15, 13, 0, "prio3.png"),

    # version 1.1 (flags)
    # flags for the languages in LocalWiki.i18n
    "{da}":  (18, 12, 1, "flag-da.png"),
    "{de}":  (18, 12, 1, "flag-de.png"),
    "{en}":  (24, 12, 0, "flag-en.png"),
    "{es}":  (18, 12, 0, "flag-es.png"),
    "{fi}":  (18, 12, 1, "flag-fi.png"),
    "{fr}":  (18, 12, 1, "flag-fr.png"),
    "{it}":  (18, 12, 1, "flag-it.png"),
    "{ja}":  (18, 12, 1, "flag-ja.png"),
    "{ko}":  (18, 12, 1, "flag-ko.png"),
    "{nl}":  (18, 12, 1, "flag-nl.png"),
    "{pt}":  (18, 12, 0, "flag-pt.png"),
    "{sv}":  (18, 12, 0, "flag-sv.png"),
    "{us}":  (20, 12, 0, "flag-us.png"),
    "{zh}":  (18, 12, 0, "flag-zh.png"),
}

# remove that hack again
del _

# Iterate through defaults, setting any absent variables
for key, val in _cfg_defaults.items():
    if not vars().has_key(key):
        vars()[key] = val

# Validate configuration - in case of admin errors
# Set charset and language code to lowercase
charset = charset.lower()
default_lang = default_lang.lower()

# Mix in std smileys
smileys.update(smiley_defaults)

del smiley_defaults
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
moinmoin_dir = os.path.abspath(os.path.dirname(__file__))

for _dirname in ('text', 'user', 'cache', 'backup', 'plugin'):
    _varname = _dirname + '_dir'
    if not vars().has_key(_varname):
        vars()[_varname] = os.path.join(data_dir, _dirname)

sys.path.append(data_dir)

del os, sys, _dirname, _varname

