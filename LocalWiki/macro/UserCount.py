# -*- coding: iso-8859-1 -*-
from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page
import xml.dom.minidom

def execute(macro, args):
       dom = xml.dom.minidom.parse(config.app_dir + "/userstats.xml")
       users = dom.getElementsByTagName("user")
       return str(users.length)
