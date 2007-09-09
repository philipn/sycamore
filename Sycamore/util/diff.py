# -*- coding: utf-8 -*-
"""
    Sycamore - Side by side diffs

    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @copyright: 2002 by Scott Moonen <smoonen@andstuff.org>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import difflib

from Sycamore.wikiutil import escape

def indent(line):
    eol = []
    while line and line[0] == '\n':
        eol.append('\n')
        line = line[1:]
    stripped = line.lstrip()
    if len(line) - len(stripped):
        line = "&nbsp;" * (len(line) - len(stripped)) + stripped
    return ''.join(eol) + line

# This code originally by Scott Moonen, used with permission.
def diff(request, old, new, text_mode=False):
    """
    Find changes between old and new and return
    HTML markup visualising them.
    """
    _ = request.getText
    t_line = _("Line") + " "

    seq1 = old.splitlines()
    seq2 = new.splitlines()
    
    seqobj = difflib.SequenceMatcher(None, seq1, seq2)
    linematch = seqobj.get_matching_blocks()

    if len(seq1) == len(seq2) and linematch[0] == (0, 0, len(seq1)):
        # No differences.
        return _("No differences found!")

    lastmatch = (0, 0)

    if not text_mode:
        result = [
            '<table class="diff">\n'
            '<tr>\n'
            '<td class="diff-removed">\n'
            '<span>\n'
            '%s\n'
            '</span>\n'
            '</td>\n'
            '<td class="diff-added">\n'
            '<span>\n'
            '%s\n'
            '</span>\n'
            '</td>\n'
            '</tr>\n'
            % (_('Deletions are marked like this.'),
               _('Additions are marked like this.'))]
    else:
        result = [
            '<table>\n'
            '<tr>\n'
            '<td>\n'
            '<span>\n'
            '%s\n'
            '</span>\n'
            '</td>\n'
            '<td>\n'
            '<span>\n'
            '%s\n'
            '</span>\n'
            '</td>\n'
            '</tr>\n'
            % (_('Deletions are marked with - .'),
               _('Additions are marked with +.'))]


    # Print all differences
    for match in linematch:
        # Starts of pages identical?
        if lastmatch == match[0:2]:
            lastmatch = (match[0] + match[2], match[1] + match[2])
            continue

        if not text_mode:
            result.append('<tr class="diff-title">\n'
                          '<td>\n'
                          '%s %s:\n'
                          '</td>\n'
                          '<td>\n'
                          '%s %s:\n'
                          '</td>\n'
                          '</tr>\n'
                          % (t_line, str(lastmatch[0] + 1), t_line,
                             str(lastmatch[1] + 1)))
        else:   
          result.append('<tr>\n'
                        '<td>\n'
                        '%s %s:\n'
                        '</td>\n'
                        '<td>\n'
                        '%s %s:\n'
                        '</td>\n'
                        '</tr>\n'
                        % (t_line, str(lastmatch[0] + 1),
                           t_line, str(lastmatch[1] + 1)))
        
        leftpane  = [] 
        rightpane = [] 
        linecount = max(match[0] - lastmatch[0], match[1] - lastmatch[1])
        for line in range(linecount):
            if line < match[0] - lastmatch[0]:
                if line > 0:
                    leftpane.append('\n')
                if not text_mode:
                    leftpane.append(seq1[lastmatch[0] + line])
                else:
                    leftpane.append("- %s" % seq1[lastmatch[0] + line])
            if line < match[1] - lastmatch[1]:
                if line > 0:
                    rightpane.append('\n')
                if not text_mode:
                    rightpane.append(seq2[lastmatch[1] + line])
                else:
                    rightpane.append("+ %s" % seq2[lastmatch[1] + line])

        charobj = difflib.SequenceMatcher(None, ''.join(leftpane),
                                          ''.join(rightpane))
        charmatch = charobj.get_matching_blocks()
        
        if charobj.ratio() < 0.5:
            # Insufficient similarity.
            if leftpane:
                leftresult = '<span>%s</span>' % indent(escape(
                    ''.join(leftpane)))
            else:
                leftresult = ''

            if rightpane:
                rightresult = '<span>%s</span>' % indent(escape(
                    ''.join(rightpane)))
            else:
                rightresult = ''
        else:
            # Some similarities; markup changes.
            charlast = (0, 0)

            leftresult  = ''
            rightresult = ''
            for thismatch in charmatch:
                if thismatch[0] - charlast[0] != 0:
                    leftresult += """<span>%s</span>""" % indent(
                        escape(''.join(leftpane)[charlast[0]:thismatch[0]]))
                if thismatch[1] - charlast[1] != 0:
                    rightresult += """<span>%s</span>""" % indent(
                        escape(''.join(rightpane)[charlast[1]:thismatch[1]]))
                leftresult += escape(''.join(
                    leftpane)[thismatch[0]:thismatch[0] + thismatch[2]])
                rightresult += escape(''.join(
                    rightpane)[thismatch[1]:thismatch[1] + thismatch[2]])
                charlast = (thismatch[0] + thismatch[2],
                            thismatch[1] + thismatch[2])

        leftpane  = '<br>\n'.join(map(indent, leftresult.splitlines()))
        rightpane = '<br>\n'.join(map(indent, rightresult.splitlines()))

        if not text_mode:
          result.append('<tr>\n'
                        '<td class="diff-removed">\n'
                        '%s\n'
                        '</td>\n'
                        '<td class="diff-added">\n'
                        '%s\n'
                        '</td>\n'
                        '</tr>\n'
                        % (leftpane, rightpane))
        else:
          result.append('<tr>\n'
                        '<td>\n'
                        '%s\n'
                        '</td>\n'
                        '<td>\n'
                        '%s\n'
                        '</td>\n'
                        '</tr>\n'
                        % (leftpane, rightpane))


        lastmatch = (match[0] + match[2], match[1] + match[2])

    result.append('</table>\n')
    return ''.join(result)
