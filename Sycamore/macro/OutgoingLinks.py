# -*- coding: iso-8859-1 -*-

from Sycamore import wikiutil, wikiform, config, wikidb
from Sycamore.Page import Page

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter

    cursor = macro.request.cursor
    cursor.execute("SELECT c.name, count(c.source_pagename) as cnt from (SELECT curPages.name, links.source_pagename from curPages left join links on links.source_pagename=curPages.name) as c group by c.name order by cnt;")
    results = cursor.fetchall()
   
    old_count = -1
    for entry in results:
      name = entry[0] 
      new_count = entry[1]
      page = Page(name, macro.request)
      if new_count == 0:
       if page.isRedirect(): continue

      if new_count != old_count:
        old_count = new_count
	macro.request.write(macro.formatter.heading(2, str(new_count)))
      else: macro.request.write(", ")
      macro.request.write(page.link_to(know_status=True, know_status_exists=True))

    return ''
