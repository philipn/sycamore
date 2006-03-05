# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Installation tests

    Note that this module tests a wiki instance for errors, and
    does not unit-test the code or something.

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

def runTest(request):
    """ This is used by moin.cgi to test the configuration, after LocalWiki
        is successfully imported. It should request.write(a plain text diagnosis
        to stdout.
    """
    # Note that importing here makes a difference, namely the request
    # object is already created
    import os, sys, xml
    from LocalWiki import config, version

    request.write('Release %s\n' % version.release)
    request.write('Revision %s\n' % version.revision)
    request.write('Python version %s\n' % sys.version)
    request.write('Python installed to %s\n' % sys.exec_prefix)
    request.write('PyXML is %sinstalled\n' % (xml.__file__.find('_xmlplus') == -1 and 'NOT ' or ''))

    request.write('Python Path:\n')
    for dir in sys.path:
        request.write('   %s\n' % dir)

    # check if the request is a local one
    import socket
    local_request = (socket.getfqdn(request.server_name) == socket.getfqdn(request.remote_addr))

    # check directories
    request.write("Checking directories...\n")
    dirs = [('data', config.data_dir),
            ('text', config.text_dir),
            ('user', config.user_dir),
            ('backup', config.backup_dir)]
    for name, path in dirs:
        if not os.path.isdir(path):
            request.write("*** %s directory NOT FOUND (set to '%s')\n" % (name, path))
        elif not os.access(path, os.R_OK | os.W_OK | os.X_OK):
            request.write("*** %s directory NOT ACCESSIBLE (set to '%s')\n" % (name, path))
        else:
            path = os.path.abspath(path)
            request.write("    %s directory tests OK (set to '%s')\n" % (name, path))

    # keep some values to ourselves
    request.write("\nServer Environment:\n")
    if local_request:
        # print the environment, in case people use exotic servers with broken
        # CGI APIs (say, M$ IIS), to help debugging those
        keys = os.environ.keys()
        keys.sort()
        for key in keys:
            request.write("    %s = %s" % (key, repr(os.environ[key])))
    else:
        request.write("    ONLY AVAILABLE FOR LOCAL REQUESTS ON THIS HOST!")

    # run unit tests
    request.write("\nUnit Tests:\n")
    try:    
        from LocalWiki import _tests
    except ImportError:
        request.write("    *** NOT AVAILABLE ***")
    else:
        _tests.run(request)

