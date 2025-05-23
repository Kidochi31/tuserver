from socket import *
import traceback


# Hole Punch Server using TCP UDP connections

# Uses 1 thread per hole puncher to create connection
# (i.e. only thread-heavy during hole punching)
# Uses 1 thread for all connection accepting
# Uses 1 thread for all sending/receiving
# (i.e. uses only 2 threads during normal operation)

class Server:
    # listener: socket - the socket used to listent to incoming tcp connections
    # local_endpoint: endpoint - the endpoint the listener is bound to
    # connections: list[(socket, socket, endpoint)] - the list of connected sockets (tcp, udp, remote endpoint)
    def __init__(self):
        # create a TCP socket that will listen for incoming connections
        self.listener = create_listener_socket()
        self.local_endpoint = self.listener.getsockname()




def create_listener_socket():
    listener = socket(AF_INET, SOCK_STREAM)
    listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    try:
        listener.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1) # unix version
    except AttributeError:
        pass
    listener.settimeout(0.5)
    listener.bind(('', 0)) # bind the socket
    listener.listen(10)
    return listener

def listen_thread(listener: socket):
    while True:
        try:
            socket, address = listener.accept()
        except Exception as e:
            print(f"Listen Exception: {traceback.format_exc()}")
    