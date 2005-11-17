# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Processor for CSV data

    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

Dependencies = []

def process(request, formatter, lines):
    # parse bangpath for arguments
    exclude = []
    for arg in lines[0].split()[1:]:
        if arg[0] == '-':
            try:
                idx = int(arg[1:])
            except ValueError:
                pass
            else:
                exclude.append(idx-1)

    # remove bang path, create output list
    del lines[0]
    output = []

    if lines[0]:
        # expect column headers in first line
        first = 1
    else:
        # empty first line, no bold headers
        first = 0
        del lines[0]

    output.append(formatter.table(1))
    for line in lines:
        output.append(formatter.table_row(1))
        cells = line.split(';')
        for idx in range(len(cells)):
            if idx in exclude: continue
            output.append(formatter.table_cell(1))
            if first: output.append(formatter.strong(1))
            output.append(formatter.text(cells[idx]))
            if first: output.append(formatter.strong(0))
            output.append(formatter.table_cell(0))
        output.append(formatter.table_row(0))
        first = 0
    output.append(formatter.table(0))

    request.write(''.join(output))

