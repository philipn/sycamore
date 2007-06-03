'''tzinfo timezone information for America/Coral_Harbour.'''
from pytz.tzinfo import DstTzInfo
from pytz.tzinfo import memorized_datetime as d
from pytz.tzinfo import memorized_ttinfo as i

class Coral_Harbour(DstTzInfo):
    '''America/Coral_Harbour timezone definition. See datetime.tzinfo for details'''

    zone = 'America/Coral_Harbour'

    _utc_transition_times = [
d(1,1,1,0,0,0),
d(1918,4,14,7,0,0),
d(1918,10,27,6,0,0),
d(1919,5,25,7,0,0),
d(1919,11,1,4,0,0),
d(1942,2,9,7,0,0),
d(1945,8,14,23,0,0),
d(1945,9,30,6,0,0),
        ]

    _transition_info = [
i(-18000,0,'EST'),
i(-14400,3600,'EDT'),
i(-18000,0,'EST'),
i(-14400,3600,'EDT'),
i(-18000,0,'EST'),
i(-14400,3600,'EWT'),
i(-14400,3600,'EPT'),
i(-18000,0,'EST'),
        ]

Coral_Harbour = Coral_Harbour()

