/* simpleindex.cc: Index each paragraph in a textfile as a document.
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

// Put a limit on the size of terms to help prevent the index being bloated
// by useless junk terms
static const unsigned int MAX_PROB_TERM_LENGTH = 64;

inline static bool
p_alnum(unsigned int c)
{
    return isalnum(c);
}

inline static bool
p_notalnum(unsigned int c)
{
    return !isalnum(c);
}

inline static bool
p_notplusminus(unsigned int c)
{
    return c != '+' && c != '-';
}

static void
lowercase_term(string &term)
{
    string::iterator i = term.begin();
    while (i != term.end()) {
	*i = tolower(*i);
	i++;
    }
}

int main(int argc, char **argv)
{
    if (argc != 4) {
	cout << "usage: " << argv[0] << " <db location> <page id> <pagename>" << endl;
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

    //ifstream batch_file(argv[2],ios::in);
    //string filename;
    string pagename(argv[3]);
    unsigned int passed_id = atoi(argv[2]);
    unsigned int id = 0;
    while (!cin.eof())
    {
    //getline(batch_file, filename);
    //cout << filename << endl;
    //ifstream file(filename.c_str(),ios::in);
    
    Stem stemmer("english");
    string para;
    while (true){
	string line;
	if (cin.eof()) {
	   if (para.empty()) break;
	} 
	else {
	    getline(cin, line); 
	    //cout << "line: " << line << endl;
	    //cout << "file.eof():" << file.eof() << endl;
	    //cout << "batch_file.eof():" << batch_file.eof() << endl;
	    //cout << "para.empty():" << para.empty() << endl;
	}
	if (cin.eof()) {
	    if (!para.empty()) {
		try {
		    Document doc;
		    doc.set_data(pagename + "\n" + para);

		    termcount pos = 0;
		    string::iterator i, j = para.begin(), k;
		    while ((i = find_if(j, para.end(), p_alnum)) != para.end())
		    {
			j = find_if(i, para.end(), p_notalnum);
			k = find_if(j, para.end(), p_notplusminus);
			if (k == para.end() || !isalnum(*k)) j = k;
			string::size_type len = j - i;
			if (len <= MAX_PROB_TERM_LENGTH) {
			    string term = para.substr(i - para.begin(), len);
			    lowercase_term(term);
			    term = stemmer.stem_word(term);
			    doc.add_posting(term, pos++);
			}
		    }

		    // Add the document to the database
		    id = passed_id;
		    if (passed_id)
		    {
		    	database.replace_document(id,doc);
		    }
		    else
		    {
			id = database.add_document(doc);
		    }
		} catch (const Error &error) {
		    cerr << "Exception: "  << error.get_msg() << endl;
		    exit(1);
		}

		para = "";
	    }
	}
	if (!para.empty()) para += ' ';
	para += line;
    }
    }
    if (!passed_id)
    {
    cout << id;
    }
}
