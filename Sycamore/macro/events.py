# -*- coding: utf-8 -*-

# Imports
import time
import re
import calendar
import string

from cStringIO import StringIO

from Sycamore import wikiutil
from Sycamore import config
from Sycamore import wikidb
from Sycamore import user

from Sycamore.Page import Page

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
    if not formatter:
        formatter=macro.formatter

    events_page = Page('Events Board', macro.request)
    if not macro.request.user.may.read(events_page):
        return ''

    htmltext = []
    do_mini = False
    if args == 'mini':
        do_mini = True
    
    are_events_today = False
    events = []

    if not do_mini:
        full_events(events, are_events_today, htmltext, macro)
    else:
        do_mini_events(events, are_events_today, htmltext, macro)

    return macro.formatter.rawHTML(''.join(htmltext))

def createTicket(tm = None):
    """
    Create a ticket using a site-specific secret (the config)
    """
    import hashlib, time, types
    ticket = tm or "%010x" % time.time()
    digest = hashlib.new('sha1')
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

def doParse(text, macro, keep_outer_paragraph=False):
    if not text.strip():
        return ''
    parsed = wikiutil.wikifyString(text, macro.request, macro.formatter.page)
    if keep_outer_paragraph:
        return parsed.strip()
    else:
        return wikiutil.stripOuterParagraph(parsed).strip()

def full_events(events, are_events_today, htmltext, macro):
    old_date = ''

    event_timezone = macro.request.config.tz

    # clear events that have passed
    yesterday_struct = time.gmtime(time.time()-60*60*24)
    yesterday = list(yesterday_struct[0:3]) + [0,0,0,0,0,0]
    yesterday = calendar.timegm(yesterday)
    macro.request.cursor.execute("""SELECT event_name, event_time
                                    FROM events
                                    WHERE event_time<%(yesterday)s and
                                          wiki_id=%(wiki_id)s""",
                                 {'yesterday':yesterday,
                                  'wiki_id':macro.request.config.wiki_id})
    macro.request.cursor.execute("""DELETE FROM events
                                    WHERE event_time<%(yesterday)s and
                                          wiki_id=%(wiki_id)s""",
                                 {'yesterday':yesterday,
                                  'wiki_id':macro.request.config.wiki_id})
    macro.request.cursor.execute(
        """SELECT uid, event_time, posted_by, text, location, event_name
           FROM events
           WHERE wiki_id=%(wiki_id)s
           ORDER BY event_time""", {'wiki_id':macro.request.config.wiki_id})
    result = macro.request.cursor.fetchone()
    while result:
        events.append(result) 
        result = macro.request.cursor.fetchone()

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

            event_time_struct = wikiutil.timeInUnixToLocal(
                                    macro.request.config.tz, event_time_unix)
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

            ptime = "%s (%s)" % (ptime, macro.request.config.tz)
                
            # This is where we want to run through the wiki processor        
            text = event[3]

            event_location = event[4]
            processed_text = doParse(text,macro,keep_outer_paragraph=True)
            processed_location = doParse(event_location,macro)
            processed_name = doParse(event_name,macro)
            month_dict = {1:'January', 2:'February', 3:'March', 4:'April',
                          5:'May', 6:'June', 7:'July', 8:'August',
                          9:'September', 10:'October', 11:'November',
                          12:'December'}
            string_month = month_dict[month]
            events_page = Page("Events Board", macro.request)
            posted_by_user = user.User(macro.request, name=posted_by)
            user_link = user.getUserLink(macro.request, posted_by_user)
            if (macro.request.user.may.admin(events_page) or
                posted_by == macro.request.user.propercased_name): 
                    if date == old_date:
                        htmltext.append(
                            '<ul>\n<h4 id="head-%s">%s</h4>\n'
                            '<a href="%s/Events_Board?action=events&uid=%s&'
                                     'del=1">[delete]</a>'
                            '&nbsp;&nbsp;<b>Time:</b> %s<br>\n'
                            '<b>Location:</b> %s<br>\n'
                            '%s(Posted by %s)\n</ul>\n' %
                            (id, processed_name, macro.request.getScriptname(),
                             id, ptime, processed_location, processed_text,
                             user_link))
                    else:
                        string_day = datetoday(int(day),int(month),int(year))
                        old_date = date
                        htmltext.append(
                            '<h2>%s, %s %s, %s</h2>\n'
                            '<ul><h4 id="head-%s">%s</h4>\n'
                            '<a href="%s/Events_Board?action=events&uid=%s&'
                                     'del=1">[delete]</a>'
                            '&nbsp;&nbsp;<b>Time:</b> '
                            '%s&nbsp;&nbsp;&nbsp;&nbsp;\n'
                            '<b>Location:</b> %s<br>\n'
                            '%s(Posted by %s)\n</ul>\n' %
                            (string_day, string_month, day, year, id,
                             processed_name,macro.request.getScriptname(), id,
                             ptime, processed_location, processed_text,
                             user_link))

            else:
                if date == old_date:
                        htmltext.append(
                            '<ul>\n<h4 id="head-%s">%s</h4>\n'
                            '<b>Time:</b> %s<br>\n'
                            '<b>Location:</b> %s<br>\n'
                            '%s(Posted by %s)\n</ul>\n' %
                            (id, processed_name, ptime, processed_location,
                             processed_text, user_link))                                   

                else:                                        
                        string_day = datetoday(int(day),int(month),int(year))                                        
                        old_date = date
                        htmltext.append(
                            '<h2>%s, %s %s</h2>\n'
                            '<ul>\n<h4 id="head-%s">%s</h4>\n'
                            '<b>Time:</b> %s&nbsp;&nbsp;&nbsp;&nbsp;\n' 
                            '<b>Location:</b> %s<br>\n'
                            '%s(Posted by %s)\n</ul>\n' %
                            (string_day, string_month, day, id, processed_name,
                             ptime, processed_location, processed_text,
                             user_link))

    title = "Post a new event:"
    htmltext.append(
        '<h3>%s</h3>\n'
        '<table border="0" cellspacing="0" cellpadding="3">\n'
        '<tr><td><form method="POST" action="%s/%s">\n'
        '<input type="hidden" name="action" value="events">\n'
        '<input type="hidden" name="ticket" value="%s">\n'
        'Event name: <input class="formfields" type="text" name="event_name"'
                           'size="30" maxlength="100">&nbsp;\n'
        'Location: <input class="formfields" type="text" '
                         'name="event_location" size="25" maxlength="100">'
        '<br><br>\n' %
        (title, macro.request.getScriptname(),
         wikiutil.quoteWikiname(macro.formatter.page.proper_name()),
         createTicket()))

    monthstring = ('<p>Date: <select name="month">\n'
                   '<option value="1">January</option>\n'
                   '<option value="2">February</option>\n'
                   '<option value="3">March</option>\n'
                   '<option value="4">April</option>\n'
                   '<option value="5">May</option>\n'
                   '<option value="6">June</option>\n'
                   '<option value="7">July</option>\n '
                   '<option value="8">August</option>\n'
                   '<option value="9">September</option>\n'
                   '<option value="10">October</option>\n'
                   '<option value="11">November</option>\n'
                   '<option value="12">December</option>\n</select>\n')
    newmonthstring = monthstring.replace(
        'value="%s"' % str(int(current_month)),
        'value="%s" selected' % str(int(current_month)))
    htmltext.append(newmonthstring)
    
    daystring = ('<select name="day">\n '
                 '<option>1</option>\n '
                 '<option>2</option>\n '
                 '<option>3</option>\n '
                 '<option>4</option>\n '
                 '<option>5</option>\n '
                 '<option>6</option>\n '
                 '<option>7</option>\n '
                 '<option>8</option>\n '
                 '<option>9</option>\n '
                 '<option>10</option>\n '
                 '<option>11</option>\n '
                 '<option>12</option>\n '
                 '<option>13</option>\n '
                 '<option>14</option>\n '
                 '<option>15</option>\n '
                 '<option>16</option>\n '
                 '<option>17</option>\n '
                 '<option>18</option>\n '
                 '<option>19</option>\n '
                 '<option>20</option>\n '
                 '<option>21</option>\n '
                 '<option>22</option>\n '
                 '<option>23</option>\n '
                 '<option>24</option>\n '
                 '<option>25</option>\n '
                 '<option>26</option>\n '
                 '<option>27</option>\n '
                 '<option>28</option>\n '
                 '<option>29</option>\n '
                 '<option>30</option>\n '
                 '<option>31</option>\n '
                 '</select>\n')
    newdaystring = daystring.replace(">"+str(int(current_day))+"<",
                                     " selected>"+str(int(current_day))+"<")
    htmltext.append(newdaystring)
    
    yearstring = '<select name="year">\n'
    for year in yearList():
        yearstring += '<option>%s</option>\n' % year
    yearstring += '</select>'
    newyearstring = yearstring.replace(">" + current_year + "<",
                                       " selected>" + current_year + "<")
    htmltext.append(newyearstring)

    hourstring = ('Time: <select name="hour">\n '
                  '<option value="0">12AM</option>\n '
                  '<option value="1">1AM</option>\n '
                  '<option value="2">2AM</option>\n '
                  '<option value="3">3AM</option>\n '
                  '<option value="4">4AM</option>\n '
                  '<option value="5">5AM</option>\n '
                  '<option value="6">6AM</option>\n '
                  '<option value="7">7AM</option>\n '
                  '<option value="8">8AM</option>\n '
                  '<option value="9">9AM</option>\n '
                  '<option value="10">10AM</option>\n '
                  '<option value="11">11AM</option>\n '
                  '<option value="12">12PM</option>\n '
                  '<option value="13">1PM</option>\n '
                  '<option value="14">2PM</option>\n '
                  '<option value="15">3PM</option>\n '
                  '<option value="16">4PM</option>\n '
                  '<option value="17">5PM</option>\n '
                  '<option value="18">6PM</option>\n '
                  '<option value="19">7PM</option>\n '
                  '<option value="20">8PM</option>\n '
                  '<option value="21">9PM</option>\n '
                  '<option value="22">10PM</option>\n '
                  '<option value="23">11PM</option>\n '
                  '</select>\n')
    newhourstring = hourstring.replace('value="%s"' % str(int(current_hour)),
                                       'value="%s" selected' %
                                           str(int(current_hour)))
    htmltext.append(newhourstring)

    if not str(int(int(current_minute)/10)) == 0:
       rounded_min = str(int(int(current_minute)/10)) + "0"
    else:
       rounded_min = "0"
    minutestring = (' : <select name="minute">\n '
                    '<option value="0">00</option>\n '
                    '<option value="10">10</option>\n '
                    '<option value="20">20</option>\n '
                    '<option value="30">30</option>\n '
                    '<option value="40">40</option>\n '
                    '<option value="50">50</option>\n '
                    '</select> (in %s)</p>\n' % event_timezone)
    newminutestring = minutestring.replace('value="%s"' % rounded_min,
                                           'value="%s" selected' % rounded_min)
    htmltext.append(newminutestring)

    htmltext.append(
                '<textarea name="event_text" rows="5" cols="67" wrapping=yes>'
                'Describe event</textarea><br>\n'
                '<input class="formbutton" type="submit" name="button" '
                       'value="Add Event">\n'
                '</form></td></tr></table>')


class TodaysEvents(object):
    def __init__(self, today, text):
        self.day = today
        self.text = text


def do_mini_events(events, are_events_today, htmltext, macro):
    todays_events = []
    cursor = macro.request.cursor
     
    timenow = time.time()
    today_struct = time.gmtime(timenow+macro.request.user.tz_offset)
    today = list(today_struct[0:3]) + [0,0,0,0,0,0]
    today = calendar.timegm(today) - macro.request.user.tz_offset
    tomorrow_struct = time.gmtime(timenow+60*60*24+macro.request.user.tz_offset)
    tomorrow = list(tomorrow_struct[0:3]) + [0,0,0,0,0,0]
    tomorrow = calendar.timegm(tomorrow) - macro.request.user.tz_offset

    if config.memcache:
        if macro.request.config.tz_offset == macro.request.user.tz_offset:
            #relative time makes 'today' different
            events = macro.request.mc.get("today_events")
        else:
            events = macro.request.mc.get("today_events:%s" % today)
        if events is not None and events.day == today:
            htmltext += events.text
            return

    cursor.execute("""SELECT event_name, uid
                      FROM events
                      WHERE event_time >= %(today)s and
                            event_time < %(tomorrow)s and
                            wiki_id=%(wiki_id)s""",
                   {'today':today, 'tomorrow':tomorrow,
                    'wiki_id':macro.request.config.wiki_id})
    events_result = cursor.fetchall()
    if not events_result:
        todays_events.append('<p><i>No events were posted for today on the <a href="%s/Events_Board">Events Board</a>.  Post one!</i></p>' % macro.request.getScriptname())
        return
    todays_events.append('<ul>')
    for event_name, uid in events_result:
        event_name = doParse(event_name, macro)
        todays_events.append('<li>%s [<a href="%s/Events_Board#head-%s">'
                             'info</a>]</li>' %
                             (event_name, macro.request.getScriptname(), uid))
    todays_events.append('</ul>')
    htmltext += todays_events

    if config.memcache:
        if macro.request.config.tz_offset == macro.request.user.tz_offset:
            event = TodaysEvents(today, todays_events)
            macro.request.mc.set("today_events", event)
        else:
            event = TodaysEvents(today, todays_events)
            # keep for 5 minutes, let it expire lazy
            macro.request.mc.add("today_events:%s" % today, event, time=60*5) 
