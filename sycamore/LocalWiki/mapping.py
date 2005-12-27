# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Wiki mapping support functions

    @copyright: 2005 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""
# Imports
import xml.dom.minidom, time

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
    cursor.execute("SELECT id, x, y from mapPoints where pagename=%s", (pagename))
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
      cursor.execute("SELECT created_time, created_by, created_by_ip, x, y from mapPoints where pagename=%s and id=%s", (name, id))
      result = cursor.fetchone()
      created_time = result[0]
      created_by = result[1]
      created_by_ip = result[2]
      oldx = result[3]
      oldy = result[4]
      cursor.execute("SELECT id from mapPointCategories where pagename=%s and x=%s and y=%s", (name, oldx, oldy))
      result = cursor.fetchall()
      old_categories = []
      for cat_id in result:
        old_categories.append(cat_id[0])
      given_id_items_for_pagename.append((id, x, y))

    if id:
      cursor.execute("INSERT into oldMapPoints set pagename=%s, x=%s, y=%s, created_time=%s, created_by=%s, created_by_ip=%s, deleted_time=%s, deleted_by=%s, deleted_by_ip=%s", (name, oldx, oldy, created_time, created_by, created_by_ip, timenow, request.user.id, request.remote_addr))
      cursor.execute("UPDATE mapPoints set pagename=%s, x=%s, y=%s, created_time=%s, created_by=%s, created_by_ip=%s where pagename=%s and id=%s and x=%s and y=%s", (name, x, y, timenow, request.user.id, request.remote_addr, name, id, oldx, oldy))
    else:
      cursor.execute("SELECT max(id) from mapPoints")
      result = cursor.fetchone()
      if result[0]:
        new_id = result[0] + 1
      else: new_id = 1
      cursor.execute("INSERT into mapPoints set pagename=%s, x=%s, y=%s, created_time=%s, created_by=%s, created_by_ip=%s, id=%s", (name, x, y, timenow, request.user.id, request.remote_addr, new_id))

    if id:
      for old_category in old_categories:
        cursor.execute("INSERT into oldMapPointCategories set pagename=%s, x=%s, y=%s, deleted_time=%s, id=%s", (name, x, y, timenow, old_category))


    for category in categories:
      cursor.execute("REPLACE into mapPointCategories set pagename=%s, x=%s, y=%s, id=%s", (name, x, y, category))

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
      cursor.execute("SELECT id from mapPointCategories where pagename=%s and x=%s and y=%s", (pagename, x, y))
      result = cursor.fetchall()
      for cat_id in  result:
        old_categories.append(cat_id[0])
        
      cursor.execute("INSERT into oldMapPoints set pagename=%s, x=%s, y=%s, created_time=(select created_time from mapPoints where pagename=%s and x=%s and y=%s), created_by=(select created_by from mapPoints where pagename=%s and x=%s and y=%s), created_by_ip=(select created_by_ip from mapPoints where pagename=%s and x=%s and y=%s), deleted_time=%s, deleted_by=%s, deleted_by_ip=%s", (pagename, x, y, pagename, x, y, pagename, x, y, pagename, x, y, timenow, request.user.id, request.remote_addr))
      cursor.execute("DELETE from mapPoints where pagename=%s and id=%s", (pagename, id))
      for old_category in old_categories:
        cursor.execute("INSERT into oldMapPointCategories set pagename=%s, x=%s, y=%s, deleted_time=%s, id=%s", (pagename, x, y, timenow, old_category))
      cursor.execute("DELETE from mapPointCategories where pagename=%s and x=%s and y=%s", (pagename, x, y))
