# Imports
import time,string
import os
from LocalWiki import config, user, util, wikiutil, wikidb
from LocalWiki.PageEditor import PageEditor
from LocalWiki.Page import Page
import xml.dom.minidom

creator_text = 'The %s Robot' % config.sitename

def clean(text):
	text=text.replace('\x85','&#8230;') # elipsis
	text=text.replace('\x91','&#8216;') # opening single quote
	text=text.replace('\x92','&#8217;') # closing single quote
	text=text.replace('\x93','&#8220;') # opening double quote
	text=text.replace('\x94','&#8221;') # closing double quote
	text=text.replace('\x96','&#8211;') # en-dash
	text=text.replace('\x97','&#8212;') # em-dash
	return text


def execute(pagename, request):
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = PageEditor(pagename, request)
    msg = ''
    oldtext = page.get_raw_body()
    if not config.relative_dir:
            add_on = ''
    else:
            add_on = '/'


    # Do we want an RSS feed?
    if request.form.has_key('rss'):
      if request.form.get("rss")[0] == "1":
        request.http_headers()
        request.write(doRSS(request,add_on))
	raise util.LocalWikiNoFooter
        return

    # be extra paranoid
    elif actname in config.excluded_actions or \
	not request.user.valid:
        #not request.user.may.edit(pagename):
            msg = _('You are not allowed to edit this page. (You need an account in most cases)')
    # check to make sure the events macro is in the page
    elif string.find(oldtext,"[[Events]]") == -1:
       msg = _('Not allowed to add an event')

    # check whether page exists at all
    elif not page.exists():
        msg = _('This page does not exist.')

    # check whether the user filled out the form
    elif request.form.has_key('uid') and request.form.has_key('del'):
        if request.form.get('del')[0] == "1" and request.user.may.admin(Page("Events Board", request)):
	    # let's try and delete the event!
	    uid = request.form.get('uid')[0]
	    request.cursor.execute("SELECT event_name from events where uid=%(uid)s", {'uid':uid})
	    name = request.cursor.fetchone()[0]
	    request.cursor.execute("DELETE from events where uid=%(uid)s", {'uid':uid})
            msg = 'Event "%s" <b>deleted</b>!' % name

        elif request.form.get('del')[0] == "1":
            uid = request.form.get('uid')[0]
	    request.cursor.execute("SELECT event_name from events where uid=%(uid)s", {'uid':uid})
	    name = request.cursor.fetchone()[0]
	    request.cursor.execute("DELETE from events where uid=%(uid)s and posted_by=%(username)s", {'uid':uid, 'username':request.user.name})
            msg = 'Event "%s" <b>deleted</b>!' % name



    elif request.form.has_key('button') and \
        request.form.has_key('event_text') and request.form.has_key('event_name') and request.form.has_key('event_location') and request.form.has_key('month') and request.form.has_key('day') and request.form.has_key('hour') and request.form.has_key('minute') and request.form.has_key('ticket'):
        # check whether this is a valid renaming request (make outside
        # attacks harder by requiring two full HTTP transactions)
        if not _checkTicket(request.form['ticket'][0]):
           msg = _('Please use the web interface to change the page!')
        else:
           event_text = clean(request.form.get('event_text')[0])
           event_name = clean(request.form.get('event_name')[0])
           event_location = clean(request.form.get('event_location')[0])
           month = int(request.form.get('month')[0])
           day = int(request.form.get('day')[0])
           hour = int(request.form.get('hour')[0])
           minute = int(request.form.get('minute')[0])
           year = int(request.form.get('year')[0])
           posted_by = request.user.name
           now = request.user.getFormattedDateTime(time.time(), global_time=True)
           #formatted_event_text = event_text + " - " + request.user.name
           #newtext = oldtext + "------" + "\n" + "''" + ''.join(now) + "'' " + formatted_event_text + "------" + "\n" + ''.join(month) + "/" + ''.join(day) + " at " + ''.join(hour) + ":" + ''.join(minute)
           #PageEditor._write_file(page,newtext)
    
           # WE NEED TO VALIDATE THE TEXT AND THE OTHER FIELDS
           if isValid(event_text,event_name,event_location,month,day,hour,minute,year) and not hasPassed(month,day,hour,minute,year,request):
              event_time_unix = time.mktime((year, month, day, hour, minute, 0, 0, 0, -1))
              writeEvent(request,event_text,event_name,event_location,event_time_unix,posted_by)
              msg = _('Your event has been added!')
           elif hasPassed(month,day,hour,minute,year,request):
              msg = _('Event time is in the past!  Please choose a time in the future.')
           else:
              msg = _('Event <b>NOT</b> posted. You entered some invalid text into the form.  No HTML is allowed')
   
    else:
        msg = _('Please fill out all fields of the form.')
        
    return page.send_page(request, msg)

def doRSS(request, add_on):
    #set up the RSS file
    rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>%s Events Board</title><link>http://%s%s%s/Events_Board</link><description>Events occuring soon, taken from the %s Events Board.</description><language>en-us</language>
</channel>
</rss>""" % (config.sitename, config.domain, add_on, config.relative_dir, config.sitename)

    rss_dom = xml.dom.minidom.parseString(rss_init_text)
    channel = rss_dom.getElementsByTagName("channel")[0]

    # Check to see if the event has already passed
    import string, re
    current_time = request.user.getFormattedDateTime(time.time(), global_time=True)
    year_cut = string.split(current_time," ")[0]
    current_year = string.split(year_cut, "-")[0]
    month_cut = string.split(current_time," ")[0]
    current_month = string.split(month_cut,"-")[1]
    day_cut = string.split(current_time," ")[0]
    current_day = string.split(day_cut,"-")[2]
    hour_cut = string.split(current_time," ")[1]
    current_hour = string.split(hour_cut,":")[0]
    string_month = findMonth(current_month)
     
#Check to see if the rss has already been generated for the current day
    #generated = 0
    #for item in items:
    #    if getText(item.getElementsByTagName("dc:date")[0].childNodes) == current_year + "-" + current_month + "-" + current_day:
    #        generated = 1
    generated = 0
    if not generated:        
        rss_text = []
	events = []
	print time.time()
	request.cursor.execute("SELECT uid, event_time, posted_by, text, location, event_name from events where DATE(FROM_UNIXTIME(event_time))=DATE(FROM_UNIXTIME(%(timenow)s))", {'timenow':time.time()})
	result = request.cursor.fetchone()
	while result:
	  events.append(result)
	  result = request.cursor.fetchone()
    
        for event in events:
	    event_time_unix = event[1]

	    # stupid date stuff
	    time_struct = time.gmtime(event_time_unix)
	    year = time_struct[0]
	    month = time_struct[1]
	    day = time_struct[2]
	    hour = time_struct[3]
	    minute = time_struct[4]

            posted_by = event[2]
            event_location = event[4]
	    event_name = event[5]

            id = event[0]
            text = event[3]
            if event_name: processed_name = wikiutil.simpleStrip(request,event_name)
	    else: processed_name = ''
            processed_text = doParse(text,request)
            processed_location = doParse(event_location,request)
            if int(hour) > 12 :
                read_hour = int(hour) - 12
                if not int(minute) == 0:
                    ptime = str(read_hour) + ":" + str(minute) + " PM"
                else:
                    ptime = str(read_hour) + ":00" + " PM"
            elif int(hour) == 0: 
                if not int(minute) == 0:
                    ptime = "12:" + str(minute) + " AM"
                else:
                    ptime = "12:00 AM"
	    elif int(hour) == 12:
 		if not int(minute) == 0:
 		    ptime = "12:" + str(minute) + " PM"
		else:
		    ptime = "12:00 PM"
            else:
                if not int(minute) == 0:
                    ptime = str(hour) + ":" + str(minute) + " AM"
                else:
                    ptime = str(hour) + ":00 AM"
        
	    total_date = "%s, %s %s" % (datetoday(int(day),int(month),int(year)),findMonth(month),day)
            item = rss_dom.createElement("item")
            rss_text = []

            rss_text.append('<b>Date:</b> %s<br>\n'
                        '<b>Time:</b> %s<br>\n'
                        '<b>Location:</b> %s<br><br>\n'
                        '%s&nbsp;&nbsp;(Posted by <a href="http://%s/%s%s%s">%s</a>)\n' % (total_date,ptime,processed_location,processed_text,config.domain,config.relative_dir,add_on, posted_by,posted_by))        
	    item_guid = rss_dom.createElement("guid")
	    item_guid.setAttribute("isPermaLink","false")
	    item_guid.appendChild(rss_dom.createTextNode(''.join(str(id))))
	    item.appendChild(item_guid)
            item_description = rss_dom.createElement("description")
            item_description.appendChild(rss_dom.createTextNode(''.join(rss_text)))
            item_title = rss_dom.createElement("title")
            item_title.appendChild(rss_dom.createTextNode(processed_name))
            item.appendChild(item_title)
            item_link = rss_dom.createElement("link")
            item_link.appendChild(rss_dom.createTextNode("http://%s/%s%sEvents_Board" % (config.domain, config.relative_dir, add_on)))
            item.appendChild(item_link)
            item_date = rss_dom.createElement("dc:date")
            item_date.appendChild(rss_dom.createTextNode("%s-%s-%s" % (current_year,current_month,current_day)))
            item.appendChild(item_date)
            creator = rss_dom.createElement("dc:creator")
            creator.appendChild(rss_dom.createTextNode(creator_text))
            item.appendChild(creator)
            item.appendChild(item_description)
            channel.appendChild(item)

    the_xml = rss_dom.toxml()

    return the_xml


def isValid(event_text,event_name,event_location,month,day,hour,minute,year):
    current_year = time.localtime(time.time())[0]
    bool = 1
    if not int(month) < 13:
        bool = bool - 1 
    if not int(day) < 32:
        bool = bool - 1
    if not int(hour) < 24:
        bool = bool - 1
    if not int(minute) < 51:
        bool = bool - 1
    if not (int(year) >= current_year and int(year) <= current_year + 1):
        bool = bool -1
    if string.find(event_text,"<") >= 0 or string.find(event_name,"<") >= 0:
        bool = bool - 1
    return bool 

def _createTicket(tm = None):
    """Create a ticket using a site-specific secret (the config)"""
    import sha, time, types
    ticket = tm or "%010x" % time.time()
    digest = sha.new()
    digest.update(ticket)

    cfgvars = vars(config)
    for var in cfgvars.values():
        if type(var) is types.StringType:
            digest.update(repr(var))

    return "%s.%s" % (ticket, digest.hexdigest())


def _checkTicket(ticket):
    """Check validity of a previously created ticket"""
    timestamp = ticket.split('.')[0]
    ourticket = _createTicket(timestamp)
    return ticket == ourticket

def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc
    
def datetoday(day, month, year):
   d = day
   m = month
   y = year
   if m < 3:
       z = y-1
   else:
       z = y
   dayofweek = ( 23*m//9 + d + 4 + y + z//4 - z//100 + z//400 )
   if m >= 3:
       dayofweek -= 2
   dayofweek = dayofweek%7
   days =[ 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
    'Sunday' ]
   return days[dayofweek-1]
   
def findMonth(month):
    months = [ 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December' ]   
    return months[int(month)-1]

def writeEvent(request, event_text, event_name, event_location, event_time_unix, posted_by):
    event_text = unicode(event_text, "ascii", "replace")
    event_name = unicode(event_name, "ascii", "replace")
    event_location = unicode(event_location, "ascii", "replace")
    event_text = event_text.encode("ascii", "replace")
    event_location = event_location.encode("ascii", "replace")
    event_name = event_name.encode("ascii", "replace")
    request.cursor.execute("SELECT max(uid) from events")
    max_id = 0
    result = request.cursor.fetchone()
    if result:
     if result[0]: max_id = result[0]
    id = max_id + 1
    posted_time = time.time()
    request.cursor.execute("INSERT into events (uid, event_time, posted_by, text, location, event_name, posted_time, posted_by_ip) values (%(id)s, %(event_time_unix)s, %(posted_by)s, %(event_text)s, %(event_location)s, %(event_name)s, %(posted_time)s, %(userip)s)", {'id':id, 'event_time_unix':event_time_unix, 'posted_by':posted_by, 'event_text':event_text, 'event_location':event_location, 'event_name':event_name, 'posted_time':posted_time, 'userip':request.remote_addr})

     
def doParse(text, request):
   #from LocalWiki.formatter.text_html import Formatter
   #from LocalWiki import formatter
   import re
   #from cStringIO import StringIO
   text = re.sub('[\n]', '<br>', text)
   formatted_text = wikiutil.simpleParse(request,text)
   #Parser = wikiutil.importPlugin("parser", "wiki", "Parser")
   #buffer = StringIO()
   #request.redirect(buffer)
   #parser = Parser(text,request)
   #formatter.page = PageEditor("EventsBoard", request)
   #parser.format(Formatter(request))
   #request.redirect()
   #formatted_text = buffer.getvalue()
   return formatted_text


def hasPassed(month,day,hour,minute,year,request):
    import string, re
    current_time = request.user.getFormattedDateTime(time.time(), global_time=True)
    year_cut = string.split(current_time," ")[0]
    current_year = string.split(year_cut, "-")[0]
    month_cut = string.split(current_time," ")[0]
    current_month = string.split(month_cut,"-")[1]
    day_cut = string.split(current_time," ")[0]
    current_day = string.split(day_cut,"-")[2]
    hour_cut = string.split(current_time," ")[1]
    current_hour = string.split(hour_cut,":")[0]
    minute_cut = string.split(current_time," ")[1]
    current_minute = string.split(minute_cut,":")[1]
    bool = 0
    
    if int(year) < int(current_year):
      bool = 0
    elif int(year) == int(current_year):
      if int(month) < int(current_month):
        bool = 1
      elif int(month) == int(current_month):
        if int(day) < int(current_day):
          bool = 1
        elif int(day) == int(current_day):
          if int(hour) < int(current_hour):
 	    bool = 1
    else:
       bool = 0
       
    return bool
