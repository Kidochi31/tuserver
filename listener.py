from socket import *
from threading import Lock, Thread
import traceback
from collections.abc import Callable
from common import endpoint, make_socket_reusable, debug_print
from select import select

class Listener:
    # listener_socket: socket - the socket used to listent to incoming tcp connections
    # local_endpoint: endpoint - the endpoint the listener is bound to
    # lock: Lock
    def __init__(self):
        self.listener_socket = create_listener_socket()
        self.local_endpoint = self.listener_socket.getsockname()
        self.lock = Lock()
    
    def get_local_endpoint(self) -> endpoint:
        return self.local_endpoint

    def _ready_to_accept(self) -> bool:
        rlist, _, _ = select([self.listener_socket], [], [], 0)
        return len(rlist) > 0
    
    def take_new_connections(self) -> list[socket]:
        with self.lock:
            new_connections = []
            while self._ready_to_accept():
                socket, _ = self.listener_socket.accept()
                new_connections.append(socket)
            return new_connections
    
    def close(self):
        with self.lock:
            try:
                self.listener_socket.close()
            except Exception:
                debug_print(f"Listener Close Exception: {traceback.format_exc()}")

def create_listener_socket() -> socket:
    listener = socket(AF_INET, SOCK_STREAM)
    make_socket_reusable(listener)
    listener.bind(('', 0)) # bind the socket
    listener.listen(10)
    return listener
