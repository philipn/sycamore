/* remove.cc: Remove the specified document from the database
 *
 * ----START-LICENCE----
 * Copyright 1999,2000,2001 BrightStation PLC
 * Copyright 2002 Ananova Ltd
 * Copyright 2002,2003,2004 Olly Betts
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
 * USA
 * -----END-LICENCE-----
 */

#include <xapian.h>

#include <algorithm>
#include <iostream.h>
#include <fstream.h>
#include <string>
#include <unistd.h>

using namespace Xapian;
using namespace std;

#include <ctype.h>


int main(int argc, char **argv)
{
    if (argc != 3) {
	cout << "usage: " << argv[0] << " <db location> <page id>" << endl;
	exit(1);
    }

    WritableDatabase database;
    try {
	// Open the database
	database = Auto::open(argv[1], DB_CREATE_OR_OPEN);
    } catch (const Error &error) {
	cerr << "Exception: "  << error.get_msg() << endl;
	exit(1);
    }

    unsigned int passed_id = atoi(argv[2]);
    database.delete_document(passed_id);
}
