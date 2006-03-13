"""
Wiki page Meta Data

- David A. Reid
"""

from Sycamore import wikidb

def addKey(page, type, key, value):
    if not key:
        key, value = value, ''

    cursor = wikidb.connect().cursor()

    exists = cursor.execute(
        ("SELECT value from metadata WHERE "
         "pagename=%(page)s and type=%(type)s and name=%(name)s;"),
        {'page': page, 'type': type.lower(), 'name': key.lower()})

    if exists and exists[0] != value:
        query = ("UPDATE metadata SET value=%(value)s WHERE "
                 "pagename=%(page)s, type=%(type)s, name=%(name)s;"),
    elif not exists:
        query = ("INSERT INTO metadata SET "
                 "pagename=%(page)s, type=%(type)s, "
                 "name=%(name)s, value=%(value)s")
    else: 
        return
    
    return cursor.execute(query,
                              {'value': value, 'page': page, 
                               'type': type.lower(), 
                               'name': key.lower()}, isWrite=True)

