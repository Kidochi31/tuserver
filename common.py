from socket import *

endpoint = tuple[str, int]

BUFSIZE = 2000
DUMMY_ENDPOINT = ("192.0.2.1", 2000)
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