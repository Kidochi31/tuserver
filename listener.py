from socket import socket
from threading import Lock
import traceback
from common import make_socket_reusable, debug_print
from select import select
from iptools import *

class Listener:
    # listen: bool - whether the listener should actively listen (or merely keep the socket open)
    # listener_socket: socket - the socket used to listent to incoming tcp connections
    # local_endpoint: IP_endpoint - the endpoint the listener is bound to
    # lock: Lock
    def __init__(self, family: AddressFamily, listen: bool, port: int):
        self.listen = listen
        self.listener_socket = create_listener_socket(family, self.listen, port)
        self.local_endpoint = get_canonical_local_endpoint(self.listener_socket)
        self.lock = Lock()
    
    def get_local_endpoint(self) -> IP_endpoint:
        return self.local_endpoint

    def _ready_to_accept(self) -> bool:
        try:
            rlist, _, _ = select([self.listener_socket], [], [], 0)
            return len(rlist) > 0
        except:
            return False
    
    def take_new_connections(self) -> list[socket]:
        with self.lock:
            new_connections : list[socket] = []
            while self._ready_to_accept():
                print("accept")
                try:
                    sock, _ = self.listener_socket.accept()
                    new_connections.append(sock)
                except:
                    break
            return new_connections
    
    def close(self):
        with self.lock:
            try:
                self.listener_socket.close()
            except Exception:
                debug_print(f"Listener Close Exception: {traceback.format_exc()}")

def create_listener_socket(family: AddressFamily, listen: bool, port: int) -> socket:
    listener = socket(family, SOCK_STREAM)
    if family == AF_INET6:
        listener.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
    make_socket_reusable(listener)
    listener.bind(('', port)) # bind the socket
    if listen:
        print("listening")
        listener.listen(10)
    print(listener)
    return listener
