# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Wiki mapping support functions

    @copyright: 2005 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""
# Imports
import xml.dom.minidom, time
from LocalWiki.wikiutil import quoteFilename

def convert_xml(dom):
  pages = dom.getElementsByTagName("page")
  mapPoints = []
  for page in pages:
    id = page.getAttribute("id")
    name = page.getAttribute("name")
    location = page.getElementsByTagName("location")[0]
    x = location.getAttribute("x")
    y = location.getAttribute("y")
    cats = page.getElementsByTagName("cat")
    categories = [cat.getAttribute("id") for cat in cats]
    mapPoints.append((id, name, x, y, categories))
  return mapPoints

def update_points(mapPoints, request, pagename=None):
  #mapPoints is a list of tuples, [( id, name, x,y, categories = list(cat_id..) )]
  # updates the map points and saves old points to old tables 
  # we are sent a list of points
  # if we don't recieve a given id for a given point for a page, we remove that point from the page
  cursor = request.cursor
  timenow = time.time()
  oldx = None
  oldy = None
  all_id_items_for_pagename = []
  given_id_items_for_pagename = []
  if pagename:
    # we get all ids for the pagename so we know which ones to delete afterward
    cursor.execute("SELECT id, x, y from mapPoints where pagename=%(page_name)s", {'page_name':pagename})
    all_id_items_result = cursor.fetchall()
    for pagename_id_item in all_id_items_result:
      all_id_items_for_pagename.append(pagename_id_item)

  for point in mapPoints:
    id = point[0]
    name = point[1]
    x = point[2]
    y = point[3]
    categories = point[4]
    if id:
      cursor.execute("SELECT created_time, created_by, created_by_ip, x, y from mapPoints where pagename=%(name)s and id=%(id)s", {'name':name, 'id':id})
      result = cursor.fetchone()
      created_time = result[0]
      created_by = result[1]
      created_by_ip = result[2]
      oldx = result[3]
      oldy = result[4]
      cursor.execute("SELECT id from mapPointCategories where pagename=%(name)s and x=%(oldx)s and y=%(oldy)s", {'name':name, 'oldx':oldx, 'oldy':oldy})
      result = cursor.fetchall()
      old_categories = []
      for cat_id in result:
        old_categories.append(cat_id[0])
      given_id_items_for_pagename.append((id, x, y))

    if id:
      cursor.execute("INSERT into oldMapPoints set pagename=%(name)s, x=%(oldx)s, y=%(oldy)s, created_time=%(created_time)s, created_by=%(created_by)s, created_by_ip=%(created_by_ip)s, deleted_time=%(time_now)s, deleted_by=%(deleted_by_id)s, deleted_by_ip=%(deleted_by_ip)s", {'name':name, 'oldx':oldx, 'oldy':oldy, 'created_time':created_time, 'created_by':created_by, 'created_by_ip':created_by_ip, 'time_now':timenow, 'deleted_by_id':request.user.id, 'deleted_by_id':request.remote_addr})
      cursor.execute("UPDATE mapPoints set pagename=%(name)s, x=%(x)s, y=%(y)s, created_time=%(time_now)s, created_by=%(created_by)s, created_by_ip=%(created_by_ip)s where pagename=%(name)s and id=%(id)s and x=%(oldx)s and y=%(oldy)s", {'name':name, 'x':x, 'y':y, 'time_now':timenow, 'created_by':request.user.id, 'created_by_ip':request.remote_addr, 'name':name, 'id:'id, 'oldx':oldx, 'oldy':oldy})
    else:
      cursor.execute("SELECT max(id) from mapPoints")
      result = cursor.fetchone()
      if result[0]:
        new_id = result[0] + 1
      else: new_id = 1
      cursor.execute("INSERT into mapPoints set pagename=%(name)s, x=%(x)s, y=%(y)s, created_time=%(time_now)s, created_by=%(created_by)s, created_by_ip=%(created_by_ip)s, id=%(new_id)s", {'name':name, 'x':x, 'y':y, 'time_now':timenow, 'created_by':request.user.id, 'created_by_ip':request.remote_addr, 'new_id':new_id})

    if id:
      for old_category in old_categories:
        cursor.execute("INSERT into oldMapPointCategories set pagename=%(name)s, x=%(x)s, y=%(y)s, deleted_time=%(time_now)s, id=%(old_category)s", {'name':name, 'x':x, 'y':y, 'time_now':timenow, 'old_category':old_category})


    for category in categories:
      cursor.execute("SELECT pagename from mapPointCategories where pagename=%(name)s and x=%(x)s and y=%(y)s and id=%(category)", {'name':name, 'x':x, 'y':y, 'category':category})
      result = cursor.fetchone()
      if result:
        cursor.execute("UPDATE mapPointCategories set pagename=%(name)s, x=%(x)s, y=%(y)s, id=%(category)s", {'name':name, 'x':x, 'y':y, 'category':category})
      else:
        cursor.execute("INSERT into mapPointCategories (pagename, x, y, id) values (%(name)s, x=%(x)s, y=%(y)s, id=%(category)s)", {'name':name, 'x':x, 'y':y, 'category':category})

  # delete the points they didn't send us for pagename
  if pagename:
    delete_id_items = []
    # this nastiness is to deal with the differences b/t unicode and noraml strings and the 'in' operation being based on id()
    for id_item in all_id_items_for_pagename:
      append_item = True
      for id_item2 in given_id_items_for_pagename:
        if str(id_item[0]) == str(id_item2[0]):
	  append_item = False
	  break
      if append_item: delete_id_items.append(id_item)

    # need to test if this delete code works.. 12-27-05 delete button in applet is broken so i can't tell for sure
    for id_item in delete_id_items:
      id = id_item[0]
      x = id_item[1]
      y = id_item[2]
      old_categories = []
      cursor.execute("SELECT id from mapPointCategories where pagename=%(pagename)s and x=%(x)s and y=%(y)s", {'pagename':pagename, 'x':x, 'y':y}))
      result = cursor.fetchall()
      for cat_id in  result:
        old_categories.append(cat_id[0])
        
      cursor.execute("INSERT into oldMapPoints set pagename=%(pagename)s, x=%(x)s, y=%(y)s, created_time=(select created_time from mapPoints where pagename=%(pagename)s and x=%(x)s and y=%(y)s), created_by=(select created_by from mapPoints where pagename=%(pagename)s and x=%(x)s and y=%(pagename)s), created_by_ip=(select created_by_ip from mapPoints where pagename=%(pagename)s and x=%(x)s and y=%(y)s), deleted_time=%(time_now)s, deleted_by=%(deleted_by)s, deleted_by_ip=%(deleted_by_ip)s", {'pagename':pagename, 'x':x, 'y':y, 'time_now':timenow, 'deleted_by':request.user.id, 'deleted_by_ip':request.remote_addr})
      cursor.execute("DELETE from mapPoints where pagename=%(pagename)s and id=%(id)s", {'pagename':pagename, 'id':id})
      for old_category in old_categories:
        cursor.execute("INSERT into oldMapPointCategories set pagename=%(pagename)s, x=%(x)s, y=%(y)s, deleted_time=%(time_now)s, id=%(old_category)s", {'pagename':pagename, 'x':x, 'y':y, 'time_now':timenow, 'old_category':old_category})
      cursor.execute("DELETE from mapPointCategories where pagename=%(pagename)s and x=%(x)s and y=%(y)s", {'pagename':pagename, 'x':x, 'y':y})
  
    # clear the memcache if they deleted all points
    if config.memcache:
      cursor.execute("SELECT count(pagename) from mapPoints where name=%(pagename)s", {'pagename': pagename})
      num_points = cursor.fetchone()
      if not num_points:
        request.mc.delete("has_map:%s" % quoteFilename(pagename))
