from socket import *
from iptools import *

BUFSIZE = 2000
DUMMY_ENDPOINT : unresolved_endpoint  = ("192.0.2.1", 2000)
CONNECT_DESTINATION : unresolved_endpoint = ("255.255.255.255", 2000)
IPV6_LOOPBACK : unresolved_endpoint = ("::1", 2000)
IPV4_LOOPBACK : unresolved_endpoint = ("127.0.0.1", 2000)
DEBUG = False

def make_socket_reusable(socket: socket):
    socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    try:
        socket.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1) # unix version
    except (AttributeError, NameError):
        pass

def debug_print(str: str):
    if DEBUG:
        print(str)