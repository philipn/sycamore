# -*- coding: utf-8 -*-

# Imports
import urllib

from Sycamore import config
from Sycamore import user
from Sycamore import wikiutil
from Sycamore import request

from Sycamore.Page import Page
from Sycamore.macro import address

def execute(pagename, request):
    page = Page(pagename, request)
    gmaps_api_key = request.config.gmaps_api_key or config.gmaps_api_key
    script_loc = (
        '<script src="http://maps.google.com/maps?file=api&v=2&key=%s" '
                'type="text/javascript"></script>' % gmaps_api_key)
    script_loc += ('<script src="%s/wiki/gmap.js" type="text/javascript">'
                   '</script>' % config.web_dir)
    wiki_name, page_locs, nearby_locs = get_map_info(request)
    map_html= mapJS(wiki_name, page_locs, nearby_locs, request)
    html = ('<html><head>%s</head>'
            '<body onLoad="loadMap();" style="padding:0;margin:0;">'
            '<div id="map" style="width: 450px; height: 300px; margin:0; '
                                 'padding:0; border:none;">'
            '</div>%s</body></html>' % (script_loc, map_html))
    request.http_headers()
    request.write(html)


class mapItem(object):
    def __init__(self, pagename, address, latitude, longitude):
        self.pagename = pagename
        self.address = address
        self.latitude = latitude
        self.longitude = longitude

def get_map_info(request):
    """
    Grabs the point and page information from the request form.
    """ 
    page_locs = [] 
    nearby_locs = []
    for key in request.form:
        item = request.form[key][0]
        if key.startswith('pname'):
            id = int(key[len('pname'):])
            locs = page_locs
        elif key.startswith('near'):
            id = int(key[len('near'):])
            locs = nearby_locs
        else:
            continue
        pagename = urllib.unquote(item)
        address = wikiutil.escape(urllib.unquote(
            request.form['addr%s' % id][0]))
        latitude = float(request.form['lat%s' % id][0])
        longitude = float(request.form['long%s' % id][0])
        locs.append(mapItem(pagename, address, latitude, longitude))

    wiki_name = request.form['wiki'][0]
    return (wiki_name, page_locs, nearby_locs)

def mapJS(wiki_name, page_locs, nearby_locs, request):
    """
    Create a string containing javascript for google map
    page = the page object
    place = place object of center of map
    nearby = dictionary of nearby places
    """
    # pick center point as the first point if there's more than one point
    # associated with the page
    center = page_locs[0]

    pagename = center.pagename
    page = Page(pagename, request, wiki_name=wiki_name)
    out = """
<script type="text/javascript">
//<![CDATA[
function doLoad() {
var map = new GMap2(document.getElementById("map"));
map.addControl(new GSmallMapControl());
map.addControl(new GMapTypeControl()); 
map.setCenter(new GLatLng(%s,%s),16);
        """ % (center.latitude, center.longitude)
        
    nearbys_processed = {}
    i = 0 # for 'a' 'b' labels on markers
    if nearby_locs:
        for x in nearby_locs:
            nearby_page = Page(x.pagename, request, wiki_name=wiki_name)
            if (x.pagename, x.latitude, x.longitude) in nearbys_processed:
                # only plot a given nearby point once 
                # (it is sometimes easier to just have repeated nearbys
                # in the query, hence we filter them out here)
                continue
            namestr = ("""'<b><a href="%s" target=_parent>%s</a></b>"""
                       """<br>%s'""" %
                       (nearby_page.url(relative=False),
                        x.pagename.replace("'","\\"+"'"), x.address.replace("'","\\"+"'")))
            out += """
            var point = new GLatLng(%s,%s);
            map.addOverlay(createMarker(point,%s, %s));
            """ % (x.latitude, x.longitude, i, namestr)
            # add it as plotted
            nearbys_processed[(x.pagename, x.latitude, x.longitude)] = None
            i += 1

    for x in page_locs:
        namestr = ("""'<b><a href="%s" target=_parent>%s</a></b>"""
                   """<br>%s'""" %
                   (page.url(relative=False), x.pagename.replace("'","\\"+"'"),
                    x.address.replace("'","\\"+"'")))
        out += ("var p_point = new GLatLng(%s,%s);\n"
                "var myArrow = createArrow(p_point,%s);\n"
                "map.addOverlay(myArrow);\n"
                "GEvent.trigger(myArrow,'click');" %
                (x.latitude, x.longitude, namestr))
           
    out += """
            loaded = true;
       }
       //]]>
       </script>"""
    return out
