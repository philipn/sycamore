# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Create a LocalWiki wiki

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""
# $Id: moin_create.py,v 1.6 2004/01/30 21:29:57 thomaswaldmann Exp $
__version__ = "$Revision: 1.6 $"[11:-2]


#############################################################################
### Helpers
#############################################################################


def check_apache():
    import _winreg
    apache_base = r'SOFTWARE\Apache Group\Apache'
    apache = None
    versions = []

    try:
        try:
            apache = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, apache_base)
        except EnvironmentError:
            _util.log('There seems to be no Apache installed on your machine.')

        if apache:
            for idx in range(100): # defense against endless loop
                try:
                    versions.append(_winreg.EnumKey(apache, idx))
                except EnvironmentError:
                    break
                    
            if versions:
                _util.log('Found Apache versions:')
                for version in versions:
                    try:
                        vkey = _winreg.OpenKey(apache, version)
                        path, type = _winreg.QueryValueEx(vkey, 'ServerRoot')
                        _util.log("    %s in '%s'" % (version, path))
                    finally:
                        _winreg.CloseKey(vkey)
            else:
                _util.log('Found Apache, but no versions.')
    finally:
        if apache: _winreg.CloseKey(apache)

    return versions


def do_check():
    import sys
    
    if sys.platform == 'win32':
        _util.log("Checking registry...")
        check_apache()
    else:
        # Posix
        pass


#############################################################################
### Main program
#############################################################################

def usage():
    """ Print usage information.
    """
    import os, sys
    sys.stderr.write("""
%(cmd)s v%(version)s, Copyright (c) 2001 by Jürgen Hermann <jh@web.de>

Usage: %(cmd)s [options] [files...]

Options:
    -q, --quiet             Be quiet (no informational messages)
    --help                  This help text
    --version               Version information
    --check                 Try to find installed webservers and their config

""" % {'cmd': __name__.split('.')[-1].replace('_', '-'), 'version': __version__})
    sys.exit(1)


def version():
    """ Print version information.
    """
    import sys
    from LocalWiki import version
    sys.stderr.write("%s (%s %s [%s])\n" %
        (__version__, version.project, version.release, version.revision))
    sys.exit(1)


def main():
    """ moin-create's main code.
    """
    import getopt, sys

    #
    # Check parameters
    #
    try:
        optlist, args = getopt.getopt(sys.argv[1:],
            'q',
            ['help', 'quiet', 'version', 'check'])
    except getopt.GetoptError, e:
        _util.fatal("Invalid parameters: %s" % str(e), usage=1)

    #print optlist, args

    if _util.haveOptions(optlist, ["--version"]): version()
    if not (optlist or args) or _util.haveOptions(optlist, ["--help"]): usage()

    _util.flag_quiet = _util.haveOptions(optlist, ["-q", "--quiet"])

    #
    # Test stuff
    #
    if _util.haveOptions(optlist, ["--check"]): do_check()


def run():
    global _util
    from LocalWiki.scripts import _util
    _util.runMain(__name__, main)


if __name__ == "__main__": run()

