from socket import *
import traceback
from threading import Thread, Lock
from common import endpoint, make_socket_reusable, debug_print

HOLEPUNCH_TIMEOUT = 10

class HolePuncher:
    # local_endpoint: endpoint - the endpoint the listener is bound to
    # lock: Lock
    # hole_punchers: Dictionary[endpoint, socket] - the dictionary of connecting TCP sockets and associated thread to the remote endpoint
    # hole_punch_fails: list[endpoint] - a list of remote endpoints that could not be connected to (and have yet to be managed)
    # hole_punch_successes: list[socket] - a list of sockets that have succeeded in connecting (and have yet to be managed)
    
    def __init__(self, local_endpoint: endpoint):
        self.local_endpoint = local_endpoint
        self.lock = Lock()
        self.hole_punchers:dict[endpoint, socket] = {} 
        self.fails:set[endpoint] = set()
        self.successes:set[socket] = set()

    def _on_success(self, endpoint: endpoint):
        with self.lock:
            if endpoint in self.hole_punchers.keys():
                socket = self.hole_punchers.pop(endpoint)
                self.successes.add(socket)
    
    def _on_fail(self, endpoint: endpoint):
        with self.lock:
            if endpoint in self.hole_punchers.keys():
                hp_socket = self.hole_punchers.pop(endpoint)
                try_close(hp_socket, "Closing Hole Puncher Exception")
                self.fails.add(endpoint)
    
    def remove_hole_puncher(self, endpoint: endpoint):
        with self.lock:
            if endpoint in self.hole_punchers.keys():
                hp_socket = self.hole_punchers.pop(endpoint)
                try_close(hp_socket, "Closing Hole Puncher Exception")
            if endpoint in self.fails:
                self.fails.remove(endpoint)

    def hole_punch(self, endpoint: endpoint):
        with self.lock:
            if endpoint in self.hole_punchers:
                debug_print(f"already hole puncher!")
                return
            if endpoint in self.fails:
                self.fails.remove(endpoint)
            
            hp_socket = create_hole_puncher_socket(self.local_endpoint)
            self.hole_punchers[endpoint] = hp_socket
            hp_thread = Thread(target=hole_punch_thread, args=(hp_socket, endpoint, self, HOLEPUNCH_TIMEOUT))
            hp_thread.start()
    
    def take_successes(self) -> list[socket]:
        with self.lock:
            successes = list(self.successes)
            self.successes.clear()
            return successes
        
    def take_fails(self) -> list[endpoint]:
        with self.lock:
            fails = list(self.fails)
            self.fails.clear()
            return fails
        
    def clear(self):
        with self.lock:
            for endpoint in list(self.hole_punchers.keys()):
                hp_socket = self.hole_punchers.pop(endpoint)
                try_close(hp_socket, "Closing Hole Puncher Exception")
            for socket in self.successes:
                try_close(socket, "Closing Hole Puncher Exception", shutdown=True)
            self.hole_punchers.clear()
            self.successes.clear()
            self.fails.clear()

def try_close(socket: socket, exception_log_name: str, shutdown:bool=False):
        if shutdown:
            try:
                socket.shutdown(SHUT_RDWR)
            except Exception:
                debug_print(f"At shutdown {exception_log_name}: {traceback.format_exc()}")
        try:
            socket.close()
        except Exception:
            debug_print(f"At close {exception_log_name}: {traceback.format_exc()}")

def create_hole_puncher_socket(local_endpoint: endpoint) -> socket:
    hp_socket = socket(AF_INET, SOCK_STREAM)
    make_socket_reusable(hp_socket)
    hp_socket.bind(local_endpoint) # bind the socket
    return hp_socket

def hole_punch_thread(hp_socket: socket, endpoint: endpoint, hole_puncher: HolePuncher, timeout: float):
    try:
        hp_socket.settimeout(timeout)
        hp_socket.connect(endpoint)
        hp_socket.settimeout(None)
        hole_puncher._on_success(endpoint)
    except Exception as e:
        debug_print(f"Connect Exception: {traceback.format_exc()}")
        hole_puncher._on_fail(endpoint)
    debug_print("stopping hole punch thread")