import sys
import os

__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..'))])

from Sycamore import __init__
from Sycamore import request

req = request.RequestDummy()
cursor = req.cursor

def update_pages(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE allPages
        SET name=%(fixed_name)s,
            propercased_name=%(fixed_propercased_name)s
        WHERE name=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })
    cursor.execute("""
        UPDATE curPages 
        SET name=%(fixed_name)s,
            propercased_name=%(fixed_propercased_name)s
        WHERE name=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_files(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE files 
        SET attached_to_pagename=%(fixed_name)s,
            attached_to_pagename_propercased=%(fixed_propercased_name)s
        WHERE attached_to_pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_imagecaptions(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE imageCaptions 
        SET attached_to_pagename=%(fixed_name)s
        WHERE attached_to_pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_imageinfo(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE imageInfo
        SET attached_to_pagename=%(fixed_name)s
        WHERE attached_to_pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_mappointcategories(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE mapPointCategories 
        SET pagename=%(fixed_name)s
        WHERE pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_mappoints(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE mapPoints 
        SET pagename=%(fixed_name)s
        WHERE pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_oldfiles(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE oldFiles
        SET attached_to_pagename=%(fixed_name)s,
            attached_to_pagename_propercased=%(fixed_propercased_name)s,
        WHERE attached_to_pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_oldimageinfo(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE oldImageInfo
        SET attached_to_pagename=%(fixed_name)s
        WHERE attached_to_pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_oldmappointcategories(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE oldMapPointCategories
        SET pagename=%(fixed_name)s
        WHERE pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_oldmappoints(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE oldMapPoints
        SET pagename=%(fixed_name)s
        WHERE pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_pageacls(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE pageAcls 
        SET pagename=%(fixed_name)s
        WHERE pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_pagedependencies(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE pageDependencies 
        SET page_that_depends=%(fixed_name)s
        WHERE page_that_depends=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })
    cursor.execute("""
        UPDATE pageDependencies 
        SET source_page=%(fixed_name)s
        WHERE source_page=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_thumbnails(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE thumbnails 
        SET attached_to_pagename=%(fixed_name)s
        WHERE attached_to_pagename=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

def update_userfavorites(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor):
    cursor.execute("""
        UPDATE userFavorites 
        SET page=%(fixed_name)s
        WHERE page=%(old_name)s AND wiki_id=%(wiki_id)s
    """, {'fixed_name': fixed_name,
          'fixed_propercased_name': fixed_propercased_name,
          'old_name': pagename,
          'wiki_id': wiki_id
    })

# Get all pages with bad chars in them
bad_names = []
cursor.execute("SELECT name, propercased_name, wiki_id FROM allPages")
for pagename, propercased_name, wiki_id in cursor.fetchall():
    if pagename.find('_') != -1:
        bad_names.append((pagename, propercased_name, wiki_id))

# Replace the character in allPages, curPages
for pagename, propercased_name, wiki_id in bad_names:
    print pagename, wiki_id
    fixed_name = pagename.replace('_', ' ')
    fixed_propercased_name = propercased_name.replace('_', ' ')
    update_pages(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)

# Update all relevant related tables
for pagename, propercased_name, wiki_id in bad_names:
    print pagename, wiki_id
    fixed_name = pagename.replace('_', ' ')
    fixed_propercased_name = propercased_name.replace('_', ' ')
    update_files(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_imagecaptions(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_imageinfo(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_mappointcategories(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_mappoints(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_oldfiles(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_oldimageinfo(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_oldmappointcategories(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_oldmappoints(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_pageacls(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_pagedependencies(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_thumbnails(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)
    update_userfavorites(fixed_name, fixed_propercased_name, pagename, wiki_id, cursor)

req.db.commit()
req.db_disconnect()
print 'done'
