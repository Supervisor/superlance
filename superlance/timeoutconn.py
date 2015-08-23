from superlance.compat import httplib
import socket
import ssl


class TimeoutHTTPConnection(httplib.HTTPConnection):
    """A customised HTTPConnection allowing a per-connection
    timeout, specified at construction."""
    timeout = None

    def connect(self):
        """Override HTTPConnection.connect to connect to
        host/port specified in __init__."""

        e = "getaddrinfo returns an empty list"
        for res in socket.getaddrinfo(self.host, self.port,
                                      0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            try:
                self.sock = socket.socket(af, socktype, proto)
                if self.timeout:   # this is the new bit
                    self.sock.settimeout(self.timeout)
                self.sock.connect(sa)
            except socket.error as e:
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error(e)


class TimeoutHTTPSConnection(httplib.HTTPSConnection):
    timeout = None

    def connect(self):
        "Connect to a host on a given (SSL) port."

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.timeout:
            sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file)
