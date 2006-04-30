from Sycamore import config, wikidb
import xml.dom.minidom

def pointsToXML(cursor):
    xml_init_text = '<?xml version="1.0" ?><data></data>'
    points_dom = xml.dom.minidom.parseString(xml_init_text)
    data = points_dom.getElementsByTagName("data")[0]

    cursor.execute("SELECT id, img, name from mapCategoryDefinitions;")
    cat_definitions = cursor.fetchall()
    masterCat = points_dom.createElement("category")
    masterCat.setAttribute("id", "0")
    masterCat.setAttribute("name", "Categories")
    for id, img, name in cat_definitions:
      cat = points_dom.createElement("category")
      cat.setAttribute("id", str(id))
      cat.setAttribute("img", str(img))
      cat.setAttribute("name", name)
      masterCat.appendChild(cat)
    data.appendChild(masterCat)
  
    point_id = 1 # we give ID to the applet but we don't need it.  not sure why the applet does..
    pages = points_dom.createElement("pages")
    cursor.execute("SELECT curPages.propercased_name, m.x, m.y, c.id from mapPoints as m, mapPointCategories as c, curPages where curPages.name=c.pagename and m.x=c.x and m.y=c.y order by curPages.propercased_name;")
    pages_points = cursor.fetchall()
    points_cat_dict = {}
    for pagename, x, y, cat_id in pages_points:
      if not points_cat_dict.has_key((pagename, x, y)):
        points_cat_dict[(pagename, x, y)] = [cat_id]
      else: 
        points_cat_dict[(pagename, x, y)].append(cat_id)

    for point_info, cat_list in points_cat_dict.iteritems():
      point = points_dom.createElement("page")
      point.setAttribute("id", str(point_id))
      point_id += 1
      point.setAttribute("name", point_info[0])
      location = points_dom.createElement("location")
      location.setAttribute("x", str(point_info[1]))
      location.setAttribute("y", str(point_info[2]))
      point.appendChild(location)
      for category_id in cat_list:
        cat = points_dom.createElement("cat")
	cat.setAttribute("id", str(category_id))
	point.appendChild(cat)
      pages.appendChild(point)
        
    if pages_points: data.appendChild(pages)

    return points_dom.toprettyxml()

def execute(pagename, request):
  request.http_headers([("Content-Type", "application/xml")])
  request.write(pointsToXML(request.cursor))
