"""
    This is just a sample for a xmlrpc plugin
"""

def execute(xmlrpcobj, *args):
    return xmlrpcobj._outstr("Hello World!")

