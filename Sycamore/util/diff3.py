# -*- coding: utf-8 -*-
"""
    Sycamore - diff3 algorithm
    
    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2002 by Florian Festi
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os
import tempfile
import random

from Sycamore import config

diff3_marker_mine = '<<<<<<<'
diff3_marker_old = '|||||||'
diff3_marker_divider = '======='
diff3_marker_yours = '>>>>>>>'

def escape_text(text):
   """
   Replace occurances of diff marker symbols with escaped versions.
   """
   text_lines = []
   for line in text.split('\n'):
        line = line.replace(diff3_marker_mine, "x%s" % diff3_marker_mine)
        line = line.replace(diff3_marker_old, "x%s" % diff3_marker_old)
        line = line.replace(diff3_marker_divider, "x%s" % diff3_marker_divider)
        line = line.replace(diff3_marker_yours, "x%s" % diff3_marker_yours)
        text_lines.append(line)
   return '\n'.join(text_lines)

def unescape_text(text):
   """
   Un-does escape_text().
   """
   text_lines = []
   for line in text.split('\n'):
        line = line.replace("x%s" % diff3_marker_mine, diff3_marker_mine)
        line = line.replace("x%s" % diff3_marker_old, diff3_marker_old)
        line = line.replace("x%s" % diff3_marker_divider, diff3_marker_divider)
        line = line.replace("x%s" % diff3_marker_yours, diff3_marker_yours)
        text_lines.append(line)
   return '\n'.join(text_lines)

def set_my_markers(diff3_result, my_marker, old_marker1, old_marker2,
                   your_marker, divider_marker, marker1, marker2, marker3):
    final_output = []
    ignore = False
    self_merge = False
    had_conflict = False
    for line in diff3_result:
        line = line.decode('utf-8')
        if line == my_marker:
            had_conflict = True
            final_output.append(marker1)
        elif line.endswith(old_marker1):
            # ignore this part for brevity
            ignore = True
            on_this_line = line[:line.find(old_marker1)]
            if on_this_line:
                final_output.append("%s\n" % on_this_line)
        elif line == old_marker2:
            # skip old, use yours
            ignore = True
            self_merge = True
        elif line == divider_marker: 
            ignore = False
            if not self_merge:
                final_output.append(marker2)
        elif line == your_marker:
            if not self_merge:
                had_conflict = True
                final_output.append(marker3)
            else:
                self_merge = False
        elif not ignore:
            final_output.append(line)

    return final_output, had_conflict

def text_merge(old, other, new,
               marker1=diff3_marker_mine,
               marker2=diff3_marker_divider,
               marker3=diff3_marker_yours):

    old = escape_text(old)
    other = escape_text(other)
    new = escape_text(new)

    had_conflict = False
    oldfile = tempfile.NamedTemporaryFile()
    oldfile.write(old.encode('utf-8'))
    oldfile.flush()
    otherfile = tempfile.NamedTemporaryFile()
    otherfile.write(other.encode('utf-8'))
    otherfile.flush()
    myfile = tempfile.NamedTemporaryFile()
    myfile.write(new.encode('utf-8'))
    myfile.flush()
    random_num = random.random()
    diff3_result = os.popen(
        "%s %s -L mine%s %s -L old%s %s -L yours%s --merge" %
            (config.diff3_location, myfile.name, random_num, oldfile.name,
             random_num, otherfile.name, random_num),
        'r')
    my_marker = "%s mine%s\n" % (diff3_marker_mine, random_num)
    old_marker1 = "%s old%s\n" % (diff3_marker_old, random_num)
    old_marker2 = "%s old%s\n" % (diff3_marker_mine, random_num)
    your_marker = "%s yours%s\n" % (diff3_marker_yours, random_num)
    divider_marker = "=======\n"

    final_output, had_conflict = set_my_markers(
        diff3_result, my_marker, old_marker1, old_marker2, your_marker,
        divider_marker, marker1, marker2, marker3)
    return (unescape_text(''.join(final_output)), had_conflict)

if __name__ == '__main__':
  old = """He and ["Judy Corbett"] are responsible for ["Village Homes"]. Michael and Judy separated, and Michael currently resides in downtown Davis. Michael is the principal designer of the ["Covell Village"] project. He is one of the authors of the ["Ahwahnee Principles"].

Michael Corbett served on the ["City Council"] from 6/20/1986 to 6/20/1990.  Served as Mayor from 1988 to 1989. He was responsible for expanding central park for the future expansion of the Farmers Market. He never swayed on his commitment to maintaing the integrity of Davis' downtown keeping the theatres from going to a freeway location. He voted to get the city to build the theater in the core of downtown on city property. One of the many choices he made as Mayor to keep the "Village" concept strong. He also had the drainage ponds in North and west Davis converted to wildlife habitat.

----
''As mayor, Mike voted to pave over Central Park and put up a three story parking infrastructure.  Fortunately he was outvoted so that we can today enjoy ["Davis Farmer's Market"].'' --["AaAa"]
  ''2005-11-09 12:08:04'' [[nbsp]] Mike Corbett voted against the commercial plans for what is now Central Park.  He was on the losing end of a 3-2 vote. The citizens then put Measure S on the ballot to overturn the Council's action.   --["SharlaDaly"]
  - I know this is feeding a troll, but this sets up a good punchline. A three story parking structure would certainly be taking the term "Central Park" literally. - ["RobRoy"]

''You should get your facts straight -- Judy is Mike's ex-wife. Call the City for verification on Mike's voting record as Mayor.'' --["AaAa"]
  The burden of proof lies on you, because you're the one who made the claim.
   ''You'd probably want to contact the City Clerk, Bette Racki:
     *Phone: (530) 757-5648
     *Fax: (530) 758-0204
     *E-Mail: [[MailTo(bracki AT ci DOT davis DOT ca DOT us)]]
   ''

''I notice his city council years overlap his mayor years, is this correct? Is there an external link for this info? Is his (etc.) voting records online?'' ''RE: Parking structure. Without knowing context and facts many items can sound outrageous. Take the recent Nile Virus issue, will future Davisites read that "The city council voted to spray a fine mist of poison over the entire residential population"? Probably.''

It's been a long time since I was in Davis, but both Mike and I were very involved in Measure S in 1986(?).  That was a citizen's referendum to reverse a city council decision to sell the Arden-Mayfair site between 3rd and 4th streets for commercial development (to a company called Terranomics).  Anyway, that site is now home to the piece of Central Park that is home to the Farmer's Market.  BTW, the Mayor was selected from the Council, so the terms overlap.


You can read about Measure S at: http://www.city.davis.ca.us/pb/cultural/30years/chapt06.cfm - ["JohnOliver"]

[[Comments]]

''2007-06-25 16:26:57'' [[nbsp]] Micheal Corbett was the sole designer and developer of the world famous "Village Homes" in Davis, CA. Based on his lifelong interest in architecture and the environment, he developed one of the first solar and environmental communities in the world. He won acclaim not only from our President at the time Jimmy Carter, but from many other world leaders. Many concepts from his first book "A Better Place to Live" were used as he forged ahead to build a community many at the time thought was a little off-beat! He also designed the most recent environmental development, "Covell Village" which was voted down by the citizens of Davis. As Davis claims to be so concerned about growth, and environmental issues they were put to the test when this development failed. Mace Ranch and Wildhorse Davis' first production sprawl developments must have caught on. Having one of the most acclaimed developments in the world was more than the citizens could handle. --["Users/Louis"]

""" 
  other = """Michael Corbett served on the ["City Council"] from 6/20/1986 to 6/20/1990.  Served as Mayor from 1988 to 1989. He was responsible for expanding central park for the future expansion of the Farmers Market. He never swayed on his commitment to maintaing the integrity of Davis' downtown keeping the theatres from going to a freeway location. He voted to get the city to build the theater in the core of downtown on city property. One of the many choices he made as Mayor to keep the "Village" concept strong. He also had the drainage ponds in North and west Davis converted to wildlife habitat.




''I notice his city council years overlap his mayor years, is this correct? Is there an external link for this info? Is his (etc.) voting records online?'' ''RE: Parking structure. Without knowing context and facts many items can sound outrageous. Take the recent Nile Virus issue, will future Davisites read that "The city council voted to spray a fine mist of poison over the entire residential population"? Probably.''

It's been a long time since I was in Davis, but both Mike and I were very involved in Measure S in 1986(?).  That was a citizen's referendum to reverse a city council decision to sell the Arden-Mayfair site between 3rd and 4th streets for commercial development (to a company called Terranomics).  Anyway, that site is now home to the piece of Central Park that is home to the Farmer's Market.  BTW, the Mayor was selected from the Council, so the terms overlap.


You can read about Measure S at: http://www.city.davis.ca.us/pb/cultural/30years/chapt06.cfm - ["JohnOliver"]

[[Comments]]

''2007-06-25 16:26:57'' [[nbsp]] Micheal Corbett was the sole designer and developer of the world famous "Village Homes" in Davis, CA. Based on his lifelong interest in architecture and the environment, he developed one of the first solar and environmental communities in the world. He won acclaim not only from our President at the time Jimmy Carter, but from many other world leaders. Many concepts from his first book "A Better Place to Live" were used as he forged ahead to build a community many at the time thought was a little off-beat! He also designed the most recent environmental development, "Covell Village" which was voted down by the citizens of Davis. As Davis claims to be so concerned about growth, and environmental issues they were put to the test when this development failed. Mace Ranch and Wildhorse Davis' first production sprawl developments must have caught on. Having one of the most acclaimed developments in the world was more than the citizens could handle. --["Users/Louis"]

"""
  new = """Michael Corbett served on the ["City Council"] from 6/20/1986 to 6/20/1990.  Served as Mayor from 1988 to 1989.  He and ["Judy Corbett"] are responsible for ["Village Homes"]. Michael and Judy separated, and Michael currently resides in downtown Davis. Michael is the principal designer of the ["Covell Village"] project. He is one of the authors of the ["Ahwahnee Principles"].  He was responsible for expanding central park for the future expansion of the Farmers Market. He never swayed on his commitment to maintaining the integrity of Davis' downtown keeping the theatres from going to a freeway location. He voted to get the city to build the theater in the core of downtown on city property. One of the many choices he made as Mayor to keep the "Village" concept strong. He also had the drainage ponds in North and west Davis converted to wildlife habitat.

----
''As mayor, Mike voted to pave over Central Park and put up a three story parking infrastructure.  Fortunately he was outvoted so that we can today enjoy ["Davis Farmer's Market"].'' --["AaAa"]
  ''2005-11-09 12:08:04'' [[nbsp]] Mike Corbett voted against the commercial plans for what is now Central Park.  He was on the losing end of a 3-2 vote. The citizens then put Measure S on the ballot to overturn the Council's action.   --["SharlaDaly"]
  - I know this is feeding a troll, but this sets up a good punchline. A three story parking structure would certainly be taking the term "Central Park" literally. - ["RobRoy"]

''You should get your facts straight -- Judy is Mike's ex-wife. Call the City for verification on Mike's voting record as Mayor.'' --["AaAa"]
  The burden of proof lies on you, because you're the one who made the claim.
   ''You'd probably want to contact the City Clerk, Bette Racki:
     *Phone: (530) 757-5648
     *Fax: (530) 758-0204
     *E-Mail: [[MailTo(bracki AT ci DOT davis DOT ca DOT us)]]
   ''

''I notice his city council years overlap his mayor years, is this correct? Is there an external link for this info? Is his (etc.) voting records online?'' ''RE: Parking structure. Without knowing context and facts many items can sound outrageous. Take the recent Nile Virus issue, will future Davisites read that "The city council voted to spray a fine mist of poison over the entire residential population"? Probably.''

It's been a long time since I was in Davis, but both Mike and I were very involved in Measure S in 1986(?).  That was a citizen's referendum to reverse a city council decision to sell the Arden-Mayfair site between 3rd and 4th streets for commercial development (to a company called Terranomics).  Anyway, that site is now home to the piece of Central Park that is home to the Farmer's Market.  BTW, the Mayor was selected from the Council, so the terms overlap.


You can read about Measure S at: http://www.city.davis.ca.us/pb/cultural/30years/chapt06.cfm - ["JohnOliver"]

[[Comments]]

''2007-06-25 16:26:57'' [[nbsp]] Micheal Corbett was the sole designer and developer of the world famous "Village Homes" in Davis, CA. Based on his lifelong interest in architecture and the environment, he developed one of the first solar and environmental communities in the world. He won acclaim not only from our President at the time Jimmy Carter, but from many other world leaders. Many concepts from his first book "A Better Place to Live" were used as he forged ahead to build a community many at the time thought was a little off-beat! He also designed the most recent environmental development, "Covell Village" which was voted down by the citizens of Davis. As Davis claims to be so concerned about growth, and environmental issues they were put to the test when this development failed. Mace Ranch and Wildhorse Davis' first production sprawl developments must have caught on. Having one of the most acclaimed developments in the world was more than the citizens could handle. --["Users/Louis"]

"""
  marker1='----- /!\ Edit conflict! Your version: -----\n'
  marker2='----- /!\ Edit conflict! Other version: -----\n'
  marker3='----- /!\ End of edit conflict -----\n'
  print text_merge(old, other, new, marker1, marker2, marker3)[0]
