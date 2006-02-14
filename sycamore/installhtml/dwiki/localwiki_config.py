# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Configuration

    Note that there are more config options than you'll find in
    the version of this file that is installed by default; see
    the module LocalWiki.config for a full list of names and their
    default values.

    Also, the URL http://purl.net/wiki/moin/HelpOnConfiguration has
    a list of config options.
            (for MoinMoin)

    @copyright: 2000-2003 by J?rgen Hermann <jh@web.de>
    @copyright: 2005-2006 by Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""
from os.path import abspath

# If you run several wikis on one host (commonly called a wiki farm),
# uncommenting the following allows you to load global settings for
# all your wikis. You will then have to create "farm_config.py" in
# the MoinMoin package directory.
# this file is also used for the blacklist (which, by, default, has nothing in it)..just leave it uncommented and it won't cause any problems, promise.
from farmconfig import *

# basic options (you normally need to change these)
sitename = 'Local Wiki Default Install'
interwikiname = None

#no slashes at the end on these guys !!
data_dir = abspath('data')

# this is the root where, say, a href="/" resolves to (considering whther or not you have a domain)
web_root = abspath('..')

# this is what's after the url if your wiki is in a directory
# e.g. '' for the root, and '/mywiki' if it's in directory mywiki
web_dir = ''

# where the indexing applications are installed, etc
app_dir = abspath('../../util_apps')

# this is where the theme css is stored
#  this is relative to the web server's root
url_prefix = '/wiki'

#displayed logo in our theme !!!! WOOO!!! Change this for a DIFFERENT LOGO!!
default_logo = 'syclogo.png'

# the phrase displayed in the title on the front page
#catchphrase = 'The definitive resource for Davis, California'
catchphrase = 'Your phrase here..'

#if the main files are placed somewhere inside of a directory such as http://daviswiki.org/dev/index.cgi as opposed to http://daviswiki.org/index.cgi
#then this var lets us figure out the proper relative link
#as of 12-29-04 we aren't yet using this, but we should use this once we have an independent dev database
# this is where the main code is installed -- in your web server documents' directory
# so if you have ~/public_html/wiki/index.cgi as your wiki executable then this would be "wiki/index.cgi"
# if there is no index.cgi then it would be "wiki"
# this is anything after the root of where your web stuff is installed
relative_dir = 'index.scgi'

#your domain (used for cookies, etc)
# uncomment only if you've got a domain and want cookies to work across subdomains
domain = 'localhost'

# turn to 0 if you want to disable the built-in talk-page theme stuff
talk_pages = 1

# MySQL database settings.
db_type = 'mysql'
db_name = 'wiki'
db_user = 'root'
db_user_password = ''
db_host = 'localhost'

#Memcache settings.  This is if you want a high-performance wiki.
memcache = True 
memcache_servers = ['127.0.0.1:11211']
# memcache_servers can be either ['server1:port', 'server2:port'] or given with weights as in
#  [('server1:port', 1), ('server2:port', 3)]  (say that server2 has 3x the memory as server1)

# Referer regular expression is used to filter out http referers from image viewing.
# It's for stopping image hotlinking, basically.
# leave blank if you don't care about people leeching images.
# to match against any url from any subdomain of daviswiki we would write:
# referer_regexp = 'http\:\/\/(([^\/]*\.)|())daviswiki\.org\/.*'
#referer_regexp = 'http\:\/\/(([^\/]*\.)|())localhost\/.*'

# encoding and WikiName char sets
# (change only for outside America or Western Europe)
charset = 'iso-8859-1'
upperletters = "A-Z??????????????????????????????"
lowerletters = "0-9a-z?????????????????????????????????"

# options people are likely to change due to personal taste
show_hosts = 1                          # show hostnames?
nonexist_qm = 0                         # show '?' for nonexistent?
backtick_meta = 1                       # allow `inline typewriter`?
allow_extended_names = 1                # allow ["..."] markup?
edit_rows = 20                          # editor size
max_macro_size = 50                     # max size of RecentChanges in KB (0=unlimited)
bang_meta = 1                           # use ! to escape WikiNames?
show_section_numbers = 0                # enumerate headlines?

allowed_actions = ['DeletePage','AttachFile']

# for standalone http server (see installhtml/index)
httpd_host = "localhost"
httpd_port = 80
httpd_user = "nobody"

theme_default = 'eggheadbeta'
theme_force = True
acl_enabled = 1
acl_rights_default = "AdminGroup:admin,read,write,delete,revert TestMe:admin,read,write,delete,revert BannedGroup:read Trusted:read,write,revert,delete Known:read,write,delete,revert All:read"

#attachments = {
# dir and url are depricated
#    'dir': '/Library/Webserver/Documents/installhtml/wiki/data/pages',
#    'url': '/installhtml/wiki/data/pages',
#    'img_script': 'img.cgi'
#}

mail_smarthost = "localhost"
mail_from = "dont_respond@daviswiki.org"
