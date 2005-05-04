# Imports
import time,string
import os
import xml.dom.minidom
from LocalWiki import config, user, util, wikiutil
from LocalWiki.PageEditor import PageEditor

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
        if request.form.get('del')[0] == "1" and request.user.may.admin("Events Board"):
            uid = int(request.form.get('uid')[0])
            dom = xml.dom.minidom.parse(config.app_dir + "/events.xml")
            events = dom.getElementsByTagName("event")
            root = dom.documentElement
            for e in events:
                if int(e.getAttribute("uid")) == uid:
		    name = e.getAttribute("name")
		    root.removeChild(e)
                    the_xml = dom.toxml()
                    xmlfile = open(config.app_dir + "/events.xml", "w")
                    xmlfile.write(the_xml)
                    xmlfile.close()
                    dom.toxml()
		    msg = 'Event "%s" <b>deleted</b>!' % name
        elif request.form.get('del')[0] == "1":
            uid = request.form.get('uid')[0]
            dom = xml.dom.minidom.parse(config.app_dir + "/events.xml")
            events = dom.getElementsByTagName("event")
            root = dom.documentElement
            for e in events:
                if e.getAttribute("uid") == uid and e.getAttribute("posted_by") == request.user.name:
                    name = e.getAttribute("name")
                    root.removeChild(e)
                    the_xml = dom.topretyxml()
                    xmlfile = open(config.app_dir + "/events.xml","w")
                    xmlfile.write(the_xml)
                    xmlfile.close()
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
           month = request.form.get('month')[0]
           day = request.form.get('day')[0]
           hour = request.form.get('hour')[0]
           minute = request.form.get('minute')[0]
           year = request.form.get('year')[0]
           posted_by = request.user.name
           now = request.user.getFormattedDateTime(time.time())
           #formatted_event_text = event_text + " - " + request.user.name
           #newtext = oldtext + "------" + "\n" + "''" + ''.join(now) + "'' " + formatted_event_text + "------" + "\n" + ''.join(month) + "/" + ''.join(day) + " at " + ''.join(hour) + ":" + ''.join(minute)
           #PageEditor._write_file(page,newtext)
    
           # NOTE!!!!!! WE NEED TO VALIDATE THE TEXT AND THE OTHER FIELDS
           if isValid(event_text,event_name,event_location,month,day,hour,minute,year) and not hasPassed(month,day,hour,minute,year,request):
              writeEvent(request,event_text,event_name,event_location,month,day,hour,minute,year,posted_by)
              msg = _('Your event has been added!')
           elif hasPassed(month,day,hour,minute,year,request):
              msg = _('Event time is in the past!  Please choose a time in the future.')
           else:
              msg = _('Event <b>NOT</b> posted. You entered some invalid text into the form.  No HTML is allowed')
   
    else:
        msg = _('Please fill out all fields of the form.')
        
    return page.send_page(request, msg)

def doRSS(request, add_on):
    dom = xml.dom.minidom.parse(config.app_dir + "/events.xml")
    events = dom.getElementsByTagName("event") 
    root = dom.documentElement

    #set up the RSS file
    rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>%s Events Board</title><link>http://%s%s%s/Events_Board</link><description>Events occuring soon, taken from the %s Events Board.</description><language>en-us</language>
</channel>
</rss>""" % (config.sitename, config.domain, add_on, config.relative_dir, config.sitename)

    rss_dom = xml.dom.minidom.parseString(rss_init_text)
    channel = rss_dom.getElementsByTagName("channel")[0]
    #items = channel.getElementsByTagName("item")
    #rss_root = rss_dom.createElement("rss")
    #rss_dom.appendChild(root)
    #rss_root.setAttribute("version","2.0")
    #rss_root.setAttribute("xmlns:dc","http://purl.org/dc/elements/1.1/")
    #channel = rss_dom.createElement("channel")
    #title = rss_dom.createElement("title")
    #title.appendChild(rss_dom.createTextNode("DavisWiki EventsBoard"))
    #channel.appendChild(title)
    #link = rss_dom.createElement("link")
    #link.appendChild(rss_dom.createTextNode("http://daviswiki.org"))
    #channel.appendChild(link)
    #description = rss_dom.createElement("description")
    #description.appendChild(rss_dom.createTextNode("Events occuring soon, taken from the Davis Wiki Events Board."))
    #channel.appendChild(description)
    #language = rss_dom.createElement("language")
    #language.appendChild(rss_dom.createTextNode("en-us"))
    #channel.appendChild(language)

    # Check to see if the event has already passed
    # The user has hard-coded time! This is ESSENTIAL for security.
    import string, re
    current_time = request.user.getFormattedDateTime(time.time())
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
    
        
        for event in events:
            event_name = event.getAttribute("name")
            month = event.getAttribute("month")
            day = event.getAttribute("day")
            hour = event.getAttribute("hour")
            minute = event.getAttribute("minute")
            year = event.getAttribute("year")
            posted_by = event.getAttribute("posted_by")
            event_location = getText(event.getElementsByTagName("location")[0].childNodes)
            id = event.getAttribute("uid")
            text = getText(event.getElementsByTagName("text")[0].childNodes)
            processed_name = wikiutil.simpleStrip(request,event_name)
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
        
            deleted = 0
            if int(year) < int(current_year) :
                root.removeChild(event)
                the_xml = dom.toprettxml()
                xmlfile = open(config.app_dir + "/events.xml","w")
                xmlfile.write(the_xml)
                xmlfile.close()
                deleted = 1
            elif int(year) == int(current_year):
                if int(month) < int(current_month):
                    root.removeChild(event)
                    the_xml = dom.toxml()
                    xmlfile = open(config.app_dir + "/events.xml","w")
                    xmlfile.write(the_xml)
                    xmlfile.close()
                    deleted = 1
                elif int(month) == int(current_month):
                    if int(day) < int(current_day):
                        root.removeChild(event)
                        the_xml = dom.toxml()
                        xmlfile = open(config.app_dir + "/events.xml","w")
                        xmlfile.write(the_xml)
                        xmlfile.close()
                        deleted = 1
            if (not deleted) and (int(year) == int(current_year)) and (int(month) == int(current_month)) and (int(day) == int(current_day)):
		total_date = "%s, %s %s" % (datetoday(int(day),int(month),int(year)),findMonth(month),day)
                item = rss_dom.createElement("item")
                rss_text = []
                
                rss_text.append('<b>Date:</b> %s<br>\n'
                            '<b>Time:</b> %s<br>\n'
                            '<b>Location:</b> %s<br><br>\n'
                            '%s&nbsp;&nbsp;(Posted by <a href="http://%s/%s%s%s">%s</a>)\n' % (total_date,ptime,processed_location,processed_text,config.domain,config.relative_dir,add_on, posted_by,posted_by))        
		item_guid = rss_dom.createElement("guid")
		item_guid.setAttribute("isPermaLink","false")
		item_guid.appendChild(rss_dom.createTextNode(''.join(id)))
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
        # do we need this?
        #(dom_rss.documentElement).appendChild(channel)
    the_xml = rss_dom.toxml()

    return the_xml


def isValid(event_text,event_name,event_location,month,day,hour,minute,year):
    bool = 1
    if not int(month) < 13:
        bool = bool - 1 
    if not int(day) < 32:
        bool = bool - 1
    if not int(hour) < 24:
        bool = bool - 1
    if not int(minute) < 51:
        bool = bool - 1
    if not (int(year) > 2003 and int(year) < 2006):
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
    months = [ 'January', 'Februrary', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December' ]   
    return months[int(month)-1]

def writeEvent(request, event_text, event_name, event_location, month, day, hour, minute,year,posted_by):
    from LocalWiki.logfile import editlog, eventlog
    event_text = unicode(event_text, "ascii", "replace")
    event_name = unicode(event_name, "ascii", "replace")
    event_location = unicode(event_location, "ascii", "replace")
    event_text = event_text.encode("ascii", "replace")
    event_location = event_location.encode("ascii", "replace")
    event_name = event_name.encode("ascii", "replace")

    dom = xml.dom.minidom.parse(config.app_dir + "/events.xml")
    root = dom.documentElement
    id = int(root.getAttribute("total")) + 1
    root.setAttribute("total", str(id))
    event = dom.createElement("event")
    event.setAttribute("month",month)
    event.setAttribute("day",day)
    event.setAttribute("hour",hour)
    event.setAttribute("minute",minute)
    event.setAttribute("year",year)
    event.setAttribute("name",event_name)
    event.setAttribute("posted_by",posted_by)
    event.setAttribute("uid",str(id))
    t = dom.createElement("text")
    t.appendChild(dom.createTextNode(event_text))
    event.appendChild(t)
    l = dom.createElement("location")
    l.appendChild(dom.createTextNode(event_location))
    event.appendChild(l)

    index = 0

    events = dom.getElementsByTagName("event")
    for e in events:  
      yr = int(e.getAttribute("year"))
      mo = int(e.getAttribute("month"))
      dy = int(e.getAttribute("day"))
      hr = int(e.getAttribute("hour"))
      mn = int(e.getAttribute("minute"))
      if yr > int(year):
         break
      if yr < int(year):
         index += 1
      else:
         if mo > int(month):
            break
         if mo < int(month):
            index += 1
         else:
            if dy > int(day):
               break
	    if dy < int(day):
               index += 1
            else:
               if hr > int(hour):
                  break
	       if hr < int(hour):
                  index += 1
               else:
	          if mn < int(minute):
         	     index += 1
                  else:
                     break

    if len(events) == index:
       root.appendChild(event)
    else:
       root.insertBefore(event,events[index]) 

    the_xml = dom.toxml()
    xmlfile = open(config.app_dir + "/events.xml", "w")
    xmlfile.write(the_xml)
    xmlfile.close()
    dom.toxml()
    # Record the changes in the editlog
    log = editlog.EditLog()
    log.add(request, "Events Board", None, os.path.getmtime(config.app_dir + "/events.xml"),
    ('Event "%s" added' % event_name), 'NEWEVENT')

     
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
    current_time = request.user.getFormattedDateTime(time.time())
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
