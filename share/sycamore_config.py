# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Configuration

    Note that there are more config options than you'll find in
    the version of this file that is installed by default; see
    the module Scyamore.config for a full list of names and their
    default values.

    @copyright: 2005-2006 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2000-2003 by J?rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""
import os.path
__directory__ = os.path.dirname(os.path.abspath(__file__))

# this file is used for the blacklist (which, by, default, has nothing in it)..just leave it uncommented and it won't cause any problems, promise.
from blacklist import *

# basic options (you normally need to change these)
wiki_name = 'wikispot'
sitename = 'Our Untitled Wiki'
interwikiname = None
interwiki_map = 'Interwiki Map'

# You probably don't need to change this.
#no slashes at the end on these guys !!
data_dir = os.path.join(__directory__, 'data')

# You probably don't need to change this.
# this is the root where, say, a href="/" resolves to (considering whether or not you have a domain)
web_root = os.path.join(__directory__, 'web')

# roughly, this is what's after the url if your wiki is in a directory
# no trailing slash
# examples: web_dir = '' # (not in a directory)
#           web_dir = '/mywiki' # (sits in mywiki directory)
web_dir = ''

# this is the directory where the images and javascript for wiki stuff is stored
#  this is relative to the web server's root
# no trailing slash
url_prefix = '/wiki'

#displayed logo. If you don't want an image logo, comment this out and the sitename will be used as a text-based logo.
#image_logo = 'syclogo.png'

# the phrase displayed in the title on the front page
#catchphrase = 'The definitive resource for Davis, California'
catchphrase = 'Your phrase here..'

#if the main files are placed somewhere inside of a directory such as http://daviswiki.org/dev/index.cgi as opposed to http://daviswiki.org/index.cgi
#then this var lets us figure out the proper relative link
# so if you have ~/public_html/wiki/index.cgi as your wiki executable then this would be "wiki/index.cgi"
# if there is no index.cgi then it would be "wiki"
# this is anything after the root of where your web stuff is installed
relative_dir = ''
# DYNAMIC relative_dir:
# relative_dir can also be of the form (string, quoted parameters), e.g ("wikis/%s", "wiki_name")
#relative_dir = ("wikis/%s", "wiki_name")

# uncomment only if you've got a domain:
# your domain (used for cookies, etc)
#wiki_base_domain = 'topsikiw.org'

# turn to 0 if you want to disable the built-in talk-page theme stuff
talk_pages = 1

# This is the license text that appears in the page footer.  If you don't want a license, comment this out.  You'll want to make the <a href="copyrightpage"> yourself.
license_text = """<!-- Creative Commons License -->Except where otherwise noted, this content is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/3.0/">Creative Commons Attribution License</a>.  See <a href="/Copyrights">Copyrights</a>.<!-- /Creative Commons License --><!--  <rdf:RDF xmlns="http://web.resource.org/cc/" xmlns:dc="http://purl.org/dc/elements/1.1/"     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"> <Work rdf:about=""><dc:type rdf:resource="http://purl.org/dc/dcmitype/Text" /><license rdf:resource="http://creativecommons.org/licenses/by/3.0/" /> </Work>  <License rdf:about="http://creativecommons.org/licenses/by/3.0/"> <permits rdf:resource="http://web.resource.org/cc/Reproduction" /> <permits rdf:resource="http://web.resource.org/cc/Distribution" /> <requires rdf:resource="http://web.resource.org/cc/Notice" /> <requires rdf:resource="http://web.resource.org/cc/Attribution" /> <permits rdf:resource="http://web.resource.org/cc/DerivativeWorks" /> </License>  </rdf:RDF>  -->"""

# This will be shown under "save changes" in the wiki editor.  If you're going to use a license then it's good to have a small snippet of text that they see when saving.
edit_agreement_text = """By clicking "Save Changes" you are agreeing to release your contribution under the <a href="http://creativecommons.org/licenses/by/3.0/">Creative Commons-By license</a>, unless noted otherwise. <b>Do not submit copyrighted work (including images) without permission.</b>  For more information, see <a href="/Copyrights">Copyrights</a>."""


# These are the buttons that appear to the right in the footer.
footer_buttons = ["""<a href="http://creativecommons.org/licenses/by/3.0/"><img alt="Creative Commons License" border="0" src="/wiki/eggheadbeta/img/cc.png" /></a>""", """<a href="http://wikispot.org/Donate"><img src="/wiki/eggheadbeta/img/donate.png" border="0" alt="donate"/></a>"""]

# tabs at the top of the browser for people who aren't logged in
tabs_nonuser = ['Front Page', 'People', 'Recent Changes']
# tabs at teh top of the browser for people who are logged in
tabs_user = ['Front Page', 'People', 'Bookmarks', 'Recent Changes']

# Change this to a google maps API key that *you* generate
# Don't bother with this if you don't plan on using the google maps.
gmaps_api_key = 'thisIsNotARealKey!'

wiki_farm_from_wiki_msg = """<div style="float: right; width: 12em; padding: 1em; border: 1px dashed gray; background-color: #ccddff;">%(wiki_name)s is a member of the %(base_wiki_sitename)s community, a nonprofit effort that allows people everywhere to easily collaborate on wikis.<br/><br/>Your account here will work on %(wiki_name)s, the %(base_wiki_name)s hub, and all the other wikis that are part of the %(base_wiki_sitename_link)s community.</div>"""

# database settings.
db_type = 'postgres'  # can be 'mysql' or 'postgres'
db_name = 'wiki'
db_user = 'wiki'
db_user_password = 'wiki'
# The IP address or hostname of the database.  Leave empty for local non-networked connection (usually works)
# (setting db_host = 'localhost' usually makes a local networked connection ;)
db_host = '' 

# location of the GNU Diff3 application.
diff3_location = '/usr/bin/diff3'

# == CAPTCHAS ==
# location of the festival applicatiion
festival_location = '/projects/festival/bin/festival'

# location of the sox application
#sox_location = '/usr/local/bin/sox'

# == End Captcha stuff ==

#Memcache settings.  This is if you want a high-performance wiki.
memcache = False
#memcache_servers = ['127.0.0.1:11211']
# memcache_servers can be either ['server1:port', 'server2:port'] or given with weights as in
#  [('server1:port', 1), ('server2:port', 3)]  (say that server2 has 3x the memory as server1)

has_xapian = False
#location of the search dbs.  you probably shouldn't have to change this.
search_db_location = os.path.join(data_dir, 'search')

# do we want to use the remote sycamore-xapian databse?
#remote_search = ('127.0.0.1', 33432)

# do we want SSL for authentication?  do we have an HTTPS running, too?
# Note: before turning this on you need to be running an https pointed
# at a sycamore instance
use_ssl = False

# farm settings
# leave blank unless you want a wiki farm
#wiki_farm = True
#wiki_farm_dir = ''
#wiki_farm_subdomains = True
# turn on web based wiki creation to allow _anyone_ that can access your site to create a wiki
# don't turn this on unless you know what you're doing, 'mate!
#allow_web_based_wiki_creation = True

page_footer1 = '<div class="wikiSpotFooter">This is a <a href="http://wikispot.org/">Wiki Spot</a> wiki.  Wiki Spot is a non-profit organization that helps communities collaborate via wikis.</div>'

# encoding and WikiName char sets
# (change only for outside America or Western Europe)
charset = 'utf-8'
upperletters = "A-Z??????????????????????????????"
lowerletters = "0-9a-z?????????????????????????????????"

allowed_actions = ['DeletePage','AttachFile']

# for standalone http server (see installhtml/index)
httpd_host = "127.0.0.1"
httpd_port = 80
httpd_user = "root"

theme_default = 'eggheadbeta'

allow_all_mimetypes = True
max_file_size = 5000

mail_smarthost = "localhost"
#mail_smarthost_auth = ('username', 'password')
# This should be an email address you own
mail_from = "dont_respond@example.org"
mail_port = 25
# TLS is for SSL email
use_tls = False

paypal_address = 'daviswiki@gmail.com'
paypal_name = 'Wiki Spot'
