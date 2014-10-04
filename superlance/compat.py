try:
    import http.client as httplib
except ImportError:
    import httplib

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    from sys import maxsize as maxint
except ImportError:
    from sys import maxint

try:
    import urllib.parse as urlparse
    import urllib.parse as urllib
except ImportError:
    import urlparse
    import urllib

try:
    import xmlrpc.client as xmlrpclib
except ImportError:
    import xmlrpclib
