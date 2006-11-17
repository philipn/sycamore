# -*- coding: iso-8859-1 -*-
"""
    Sycamore - google map api address macro

    @copyright: 2006 by rottenchester <rottenchester@gmail.com>
    @license: GNU GPL, see COPYING for details.

    NB:  You must change your config.gmaps_api_key to a google maps API key otherwise this won't work.

"""

# Imports for Sycamore
import time, re
from Sycamore import config, wikiutil, wikidb, caching
from Sycamore.Page import Page

# Imports for geocode
import sys, urllib, urllib2, urlparse, gzip, xml.dom.minidom
from StringIO import StringIO

Dependencies = []

class geocode:
    '''
    geocode addresses using Google Maps API
    
    place = geocode.geocode(address)

    alt = place.altitude
    lat = place.latitude
    long = place.longitude
    
    Note that altitude is always 0 for the current (2.0) version of
    the Maps API
    '''

    # be sure the URL is set correctly for google maps

    MAP_URL = 'http://maps.google.com/maps/geo?output=xml&'

    latitude = None
    longitude = None
    altitude = None
    debug = False

    def __init__(self, request, address=None,debug=False):
        self.request  = request
        if debug == True:
            self.debug = True
        if address is not None:
            self.__getCoordinates(address)

    class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_301(self, req, fp, code, msg, headers):
            result = urllib2.HTTPRedirectHandler.http_error_301(
                self, req, fp, code, msg, headers)
            result.status = code
            return result

        def http_error_302(self, req, fp, code, msg, headers):
            result = urllib2.HTTPRedirectHandler.http_error_302(
                self, req, fp, code, msg, headers)
            result.status = code
            return result

    class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
        def http_error_default(self, req, fp, code, msg, headers):
            result = urllib2.HTTPError(
                req.get_full_url(), code, msg, headers, fp)
            result.status = code
            return result

    def __openURL(self,address):
        """URL --> string

        Open a URL and return the data as a string.  Use the smart
        handlers to deal with redirects and errors.  Accept gzip and
        handle it if we get it.

        Modified from the example in Dive Into Python
        """

        # open URL with urllib2
        address = urllib.urlencode({'q':address})
        myurl = self.MAP_URL + '&key=' + (self.request.config.gmaps_api_key or config.gmaps_api_key) + '&' + address 
        request = urllib2.Request(myurl)
        request.add_header('Accept-encoding', 'gzip')
        opener = urllib2.build_opener(self.SmartRedirectHandler(),\
                                      self.DefaultErrorHandler())
        f = opener.open(request)
        data = f.read()

        if hasattr(f, 'headers') and \
               f.headers.get('content-encoding') == 'gzip':
            # data came back gzip-compressed, decompress it
            data = gzip.GzipFile(fileobj=StringIO(data)).read()
            f.close()

        return data

    def __getCoordinates(self,address):
        """ address --> list of lat, long, altitude of the address

        At this time, altitude is always 0
        """

        # extremely rudimentary error handling

        try:
            xmlout = self.__openURL(address)
        except:
            return

        try:
            xmldoc = xml.dom.minidom.parseString(xmlout)
        except:
            return

        if self.debug: print xmlout

        # <Status><code> of 200 is good
        code = xmldoc.getElementsByTagName('code')
        if self.debug: print "Code = '%s'" % code[0].childNodes[0].data
        if code[0].childNodes[0].data != '200':
            return

        coord = xmldoc.getElementsByTagName('coordinates')
        self.longitude, self.latitude, self.altitude = \
                       coord[0].childNodes[0].data.split(',')

        if self.debug:
            print "Latitude = %s, Longitude = %s"%(self.latitude,self.longitude)
           
        return

# end geocode

class location:
    """
    location.py -- db wrapper class to read/write/create location rows
    
    place = location.location(self,macro,formatter,name,address,lat,long)

    latitude = place.latitude
    longitude = place.longitude

    uses the geocode class

    """

    def __init__(self,macro,formatter,address=None,lat=None,long=None): 

        self.macro = macro
        self.formatter = formatter
        self.name = macro.formatter.page.page_name
        self.address = address
        self.latitude = lat
        self.longitude = long

        if self.address and self.latitude is None:
            self.__geocodePlace(self.address)

    def __lookupPlace(self): 
        """
        private to lookup the name in the db
        sets address, latitude, longitude, altitude
        """

        cursor = self.macro.request.cursor
        cursor.execute('''SELECT address, x, y
                          FROM mappoints
                          WHERE pagename = %(pagename)s and address=%(address)s''',
                       {'pagename':self.name})

        row = cursor.fetchone()

        if row:
            self.address, self.latitude, self.longitude = row
        else:
            self.address = None
            self.latitude = None
            self.longitude = None

        return

    def addPlace(self):
        """
        add location name having address address if it is not
        in the database.
        """
        address = self.address
        lat = self.latitude
        long = self.longitude

        ignore = (self.formatter.isPreview() or self.formatter.name != 'text_html') or self.formatter.page.prev_date
        if ignore: return

        if lat is None:
            self.__geocodePlace(address)
        else:
            self.latitude = lat
            self.longitude = long
        if self.latitude is not None:
            self.__insertEntry(address)
            self.__clearCaches()

        self.address = address

    def __geocodePlace(self,address):

        """get the lat/log/alt of the address """

        place = geocode(self.macro.request, address)
        self.latitude = place.latitude
        self.longitude = place.longitude

    def __insertEntry(self,address):

        """ insert a location entry in the db """

        cursor = self.macro.request.cursor;
        cursor.execute('''INSERT INTO mappoints (pagename, x, y,
                          created_time, created_by, created_by_ip,
                          id, pagename_propercased,
                          address, wiki_id)
                          VALUES (%(pagename)s,%(x)s,%(y)s,
                          %(created_time)s,
                          %(created_by)s,%(created_by_ip)s,
                          %(id)s,%(pagename_propercased)s,%(address)s,
                          %(wiki_id)s)''',
                       {'pagename':self.name,
                        'wiki_id':self.macro.request.config.wiki_id,
                        'x':self.latitude,
                        'y':self.longitude,
                        'created_time':self.macro.request.save_time,
                        'created_by':self.macro.request.user.id,
                        'created_by_ip':self.macro.request.remote_addr,
                        'id':1,
                        'pagename_propercased':self.macro.formatter.page.proper_name(),
                        'address':address},True)


    def __updateEntry(self,address):

        ''' update location entry in db '''

        cursor = self.macro.request.cursor
        cursor.execute('''UPDATE mappoints
                       SET address = %(address)s,
                       x = %(x)s,
                       y = %(y)s
                       WHERE pagename=%(pagename)s and wiki_id=%(wiki_id)s''',
                       {'address':address,
                        'x':self.latitude,
                        'y':self.longitude,
                        'wiki_id':self.macro.request.config.wiki_id,
                        'pagename':self.name },True)


    def getNearby(self,max=20,distance=.2):

        ''' create a list of nearby locations, with a maximum
        number of locations = max, and a radius of distance degrees '''

        cursor = self.macro.request.cursor
        cursor.execute('''SELECT pagename_propercased, address, x, y
                        FROM mapPoints, curPages
                        WHERE abs(%(long1)s - cast(y as numeric))+
                        abs(%(lat1)s-cast(x as numeric)) < %(dist)s
                        AND pagename <> %(pagename)s
                        AND curPages.name = mapPoints.pagename
                        AND curPages.wiki_id = %(wiki_id)s
                        ORDER BY abs(%(long2)s - cast(y as numeric))+
                        abs(%(lat2)s-cast(x as numeric))
                        LIMIT %(max)s''',
                       {'long1':self.longitude,
                        'lat1':self.latitude,
                        'dist':distance,
                        'wiki_id':self.macro.request.config.wiki_id, 
                        'pagename':self.name,
                        'long2':self.longitude,
                        'lat2':self.latitude,                      
                        'max':max})

        rows = cursor.fetchall()
        if rows: 
            lis = []
            for row in rows:
                lis.append({'name':row[0],'address':row[1],'latitude':row[2],\
                            'longitude':row[3]})
            return lis
        return []

    def __clearCaches(self):
        '''
        Clears the page caches of nearby locations.  We do this so that nearby maps are updated after we've updated ourself!
        '''
        for entry in self.getNearby(max=None):
          pagename = entry['name']
          caching.CacheEntry(pagename, self.macro.request).clear()

# end location

def mapHTML(macro, place, nearby):
    html = """<script type="text/javascript">map_url=map_url+"&pname"+point_count+"=%s&addr"+point_count+"=%s&long"+point_count+"=%s&lat"+point_count+"=%s\"""" % (
        urllib.quote(Page(place.name, macro.request).proper_name()), urllib.quote(place.address), place.longitude, place.latitude)
    near_count = 0
    for loc in nearby:
        near_count += 1 
        html += """+\"&near"+(point_count+%s)+"=%s&addr"+(point_count+%s)+"=%s&long"+(point_count+%s)+"=%s&lat"+(point_count+%s)+"=%s\"""" % (
            near_count, urllib.quote(loc['name']), near_count, urllib.quote(loc['address']), near_count, urllib.quote(loc['longitude']), near_count, urllib.quote(loc['latitude']))
    html += ";point_count=point_count+%s+1;</script>" % near_count
    return html
        

def execute(macro, args, formatter):
    if not formatter: formatter = macro.formatter

    # re for old format Address("address","description")
    oldformat = re.compile(r'^\s*\"(.+)\"\s*,\s*\"(.+)\"\s*$')

    # re for new format Address("address","lat","long")
    newformat = re.compile(r'^\s*\"(.+)\"\s*,\s*\"(.+)\"\s*,\s*\"(.+)\"\s*$')

    lat = None
    long = None
    if newformat.search(args):
        (address,lat,long) = newformat.search(args).groups()
    elif oldformat.search(args):
        (address,parm1) = oldformat.search(args).groups()
    else:       
        address = args
        address = address.strip('"')

    if macro.request.config.address_locale and address.find(',') == -1:
        address = '%s, %s' % (address, macro.request.config.address_locale) # add the address locale if it's lacking

    if lat is None:
        place = location(macro,formatter,address)
    else:
        place = location(macro,formatter,address,lat,long)

    if place.latitude is None:
        return address
    else:
        out = address
        nearby = place.getNearby()
        out += mapHTML(macro,place,nearby)
        ignore = (formatter.isPreview() or formatter.name != 'text_html') or formatter.page.prev_date
        if not ignore:
            macro.request.addresses.append(place)
        return out
