# -*- coding: iso-8859-1 -*-
import time, re
from LocalWiki import wikiutil, wikiform, config, wikidb
from LocalWiki.Page import Page
import xml.dom.minidom
from cStringIO import StringIO

def yearList():
  current_year = time.localtime(time.time())[0]  
  years_list = [str(current_year), str(current_year + 1)]
  return years_list

def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def execute(macro, args, formatter=None):
    if not formatter: formatter=macro.formatter
    htmltext = []
    do_mini = False
    if args == 'mini': do_mini = True
    
    if config.relative_dir:
        add_on = '/'
    else:
        add_on = ''

    are_events_today = False
    old_date = ''
    events = []
    db = wikidb.connect()
    cursor = db.cursor()
    cursor.execute("start transaction")
    # clear events that have passed
    cursor.execute("DELETE from events where DATE(FROM_UNIXTIME(event_time))<DATE(FROM_UNIXTIME(%s))", (time.time()))
    cursor.execute("SELECT uid, event_time, posted_by, text, location, event_name from events order by event_time")
    result = cursor.fetchone()
    while result:
      events.append(result) 
      result = cursor.fetchone()
    cursor.execute("commit")
    cursor.close()
    db.close()

    import string, re
    current_time = macro.request.user.getFormattedDateTime(time.time())
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

    for event in events:
		event_name = event[5]
	 	# we store it as a general time and we convert it to a local time..
		event_time_unix = event[1]
		event_time_struct = time.gmtime(event_time_unix)
		year = event_time_struct[0]
		month = event_time_struct[1]
		day = event_time_struct[2]
		hour = event_time_struct[3]
		minute = event_time_struct[4]
		posted_by = event[2]
                id = event[0]
		date = str(month) + " " +  str(day)

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
                
                # This is where we want to run through the wiki processor        
                text = event[3]

		event_location = event[4]
		processed_text = doParse(text,macro)
		processed_location = doParse(event_location,macro)
                processed_name = doParse(event_name,macro)
                month_dict = { 1: 'January', 2: 'Feburary', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
                string_month = month_dict[month]
                if (macro.request.user.may.admin("Events Board") or posted_by == macro.request.user.name) and not do_mini: 
                        if date == old_date:
                            htmltext.append('<ul>\n<h4 id="head-%s">%s</h4>\n'
                                  '<a href="/%s%sEvents_Board?action=events&uid=%s&del=1">[delete]</a>&nbsp;&nbsp;<b>Time:</b> %s<br>\n'
                                  '<b>Location:</b> %s<br>\n'
                                  '%s&nbsp;&nbsp;(Posted by <a href="/%s%s%s">%s</a>)\n</ul>\n' % (id, processed_name,config.relative_dir, add_on, id,ptime,processed_location,processed_text,config.relative_dir,add_on, posted_by,posted_by))
                        else:
                            string_day = datetoday(int(day),int(month),int(year))
                            old_date = date
                            htmltext.append('<h2>%s, %s %s, %s</h2>\n'
                                    '<ul><h4 id="head-%s">%s</h4>\n'
                                    '<a href="/%s%sEvents_Board?action=events&uid=%s&del=1">[delete]</a>&nbsp;&nbsp;<b>Time:</b> %s&nbsp;&nbsp;&nbsp;&nbsp;\n'
                                    '<b>Location:</b> %s<br>\n'
                                    '%s&nbsp;&nbsp;(Posted by <a href="/%s%s%s">%s</a>)\n</ul>\n' % (string_day,string_month,day,year,id, processed_name,config.relative_dir,add_on, id,ptime,processed_location,processed_text,config.relative_dir,add_on,posted_by,posted_by))
                elif do_mini:
                    event_unix_time = time.mktime((int(year), int(month), int(day), 0, 0, 0, 0, 0, 0))
                    unix_day = time.mktime((0, 0, 1, 0, 0, 0, 0, 0, 0)) - time.mktime((0,0,0,0,0,0,0,0,0))
                    unix_hour = time.mktime((0, 0, 0, 1, 0, 0, 0, 0, 0)) - time.mktime((0,0,0,0,0,0,0,0,0))
                    unix_now = time.time() + (config.tz_offset * unix_hour)
                    if event_unix_time <= unix_now + unix_day and time.gmtime(unix_now)[2] == int(day):
                    # same day, let's print it!
                        are_events_today = True
                        htmltext.append('\n<p>%s [<a href="/%s%sEvents_Board#head-%s">info</a>]</p>\n'
                                            % (processed_name, config.relative_dir, add_on, id))


                else:
                    if date == old_date:
                            htmltext.append('<ul>\n<h4 id="head-%s">%s</h4>\n'
                                    '<b>Time:</b> %s<br>\n'
                                    '<b>Location:</b> %s<br>\n'
                                    '%s&nbsp;&nbsp;(Posted by <a href="/%s%s%s">%s</a>)\n</ul>\n' % (id,processed_name,ptime,processed_location,processed_text,config.relative_dir,add_on, posted_by,posted_by))                                   

                    else:                                        
                            string_day = datetoday(int(day),int(month),int(year))                                        
                            old_date = date
                            htmltext.append('<h2>%s, %s %s</h2>\n'
                                    '<ul>\n<h4 id="head-%s">%s</h4>\n'                                        
                                    '<b>Time:</b> %s&nbsp;&nbsp;&nbsp;&nbsp;\n' 
                                    '<b>Location:</b> %s<br>\n'                                        
                                    '%s&nbsp;&nbsp;(Posted by <a href="/%s%s%s">%s</a>)\n</ul>\n' % (string_day,string_month,day,id,processed_name,ptime,processed_location,processed_text,config.relative_dir,add_on, posted_by,posted_by))

     
    if do_mini and not are_events_today:
        htmltext.append('<i>No events were posted for today on the <a href="/%s%sEvents_Board">Events Board</a>.  Post one!</i>' % (config.relative_dir, add_on))
    if not do_mini:
       title = "Post a new event:"
       htmltext.append('<h3>%s</h3>\n'
                   '<table border="0" cellspacing="0" cellpadding="3">\n'
                   '<tr><td><form method="POST" action="/%s%s%s">\n'
                   '<input type="hidden" name="action" value="events">\n'
                   '<input type="hidden" name="ticket" value="%s">\n'
                   'Event name: <input class="formfields" type="text" name="event_name" size="30">&nbsp;\n'
                   'Location: <input class="formfields" type="text" name="event_location" size="25"><br><br>\n'
   		% (title, config.relative_dir, add_on, macro.formatter.page.page_name, createTicket()))
   
       monthstring ='<p>Date: <select name="month">\n<option value="1">January</option>\n<option value="2">February</option>\n<option value="3">March</option>\n<option value="4">April</option>\n<option value="5">May</option>\n<option value="6">June</option>\n<option value="7">July</option>\n <option value="8">August</option>\n<option value="9">September</option>\n<option value="10">October</option>\n<option value="11">November</option>\n<option value="12">December</option>\n</select>\n'
       newmonthstring = monthstring.replace('value="%s"' % str(int(current_month)), 'value="%s" selected' % str(int(current_month)))
       htmltext.append(newmonthstring)
       
       daystring = '<select name="day">\n <option>1</option>\n <option>2</option>\n <option>3</option>\n <option>4</option>\n <option>5</option>\n <option>6</option>\n <option>7</option>\n <option>8</option>\n <option>9</option>\n <option>10</option>\n <option>11</option>\n <option>12</option>\n <option>13</option>\n <option>14</option>\n <option>15</option>\n <option>16</option>\n <option>17</option>\n <option>18</option>\n <option>19</option>\n <option>20</option>\n <option>21</option>\n <option>22</option>\n <option>23</option>\n <option>24</option>\n <option>25</option>\n <option>26</option>\n <option>27</option>\n <option>28</option>\n <option>29</option>\n <option>30</option>\n <option>31</option>\n </select>\n'
       newdaystring = daystring.replace(">" + str(int(current_day)) + "<", " selected>" + str(int(current_day)) + "<")
       htmltext.append(newdaystring)
       
       yearstring = '<select name="year">\n'
       for year in yearList():
          yearstring += '<option>%s</option>\n' % year
       yearstring += '</select>'
       newyearstring = yearstring.replace(">" + current_year + "<", " selected>" + current_year + "<")
       htmltext.append(newyearstring)
   
       hourstring = 'Time: <select name="hour">\n <option value="0">12AM</option>\n <option value="1">1AM</option>\n <option value="2">2AM</option>\n <option value="3">3AM</option>\n <option value="4">4AM</option>\n <option value="5">5AM</option>\n <option value="6">6AM</option>\n <option value="7">7AM</option>\n <option value="8">8AM</option>\n <option value="9">9AM</option>\n <option value="10">10AM</option>\n <option value="11">11AM</option>\n <option value="12">12PM</option>\n <option value="13">1PM</option>\n <option value="14">2PM</option>\n <option value="15">3PM</option>\n <option value="16">4PM</option>\n <option value="17">5PM</option>\n <option value="18">6PM</option>\n <option value="19">7PM</option>\n <option value="20">8PM</option>\n <option value="21">9PM</option>\n <option value="22">10PM</option>\n <option value="23">11PM</option>\n </select>\n'
       newhourstring = hourstring.replace('value="%s"' % str(int(current_hour)), 'value="%s" selected' % str(int(current_hour)))
       htmltext.append(newhourstring)
   
       if not str(int(int(current_minute)/10)) == 0:
          rounded_min = str(int(int(current_minute)/10)) + "0"
       else:
          rounded_min = "0"
       minutestring = ' : <select name="minute">\n <option value="0">00</option>\n <option value="10">10</option>\n <option value="20">20</option>\n <option value="30">30</option>\n <option value="40">40</option>\n <option value="50">50</option>\n </select></p>\n'
       newminutestring = minutestring.replace('value="%s"' % rounded_min, 'value="%s" selected' % rounded_min)
       htmltext.append(newminutestring)
   
   
       htmltext.append(
                   #'<input class="formfields" type="text" name="event_text" size="100"></td><td valign="top">\n'
                   '<textarea name="event_text" rows="5" cols="67" wrapping=yes>Describe event</textarea><br>\n'
                   '<input class="formbutton" type="submit" name="button" value="Add Event">\n'
                   '</form></td></tr></table>')


    return macro.formatter.rawHTML(''.join(htmltext))

def createTicket(tm = None):
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


def doParse(text, macro):
   if not text: return ''
   text = re.sub('[\n]', ' [[BR]]', text)
   Parser = wikiutil.importPlugin("parser", "wiki", "Parser")
   buffer = StringIO()
   macro.request.redirect(buffer)
   parser = Parser(text,macro.request)
   parser.format(macro.formatter)
   macro.request.redirect()
   formatted_text = buffer.getvalue()
   return formatted_text
