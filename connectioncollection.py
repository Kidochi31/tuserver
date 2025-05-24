from socket import *
from connection import Connection
from common import BUFSIZE, endpoint, debug_print
from threading import Lock
from udpsocket import UdpSocket
from select import select

class ConnectionCollection:
    # connections: Dictionary[endpoint, Connection] - the dictionary of Connections from the remote endpoint
    # sockets: set[socket] - a list of sockets to poll for reading
    # disconnections: list[Connection] - a list of connections that have recently disconnected but not been handled
    # lock: Lock - the lock for this connection collection
    def __init__(self):
        self.connections :dict[endpoint, Connection] = {}
        self.sockets :list[socket] = []
        self.disconnections :set[Connection] = set()
        self.lock = Lock()

    def __contains__(self, endpoint: endpoint) -> bool:
        return endpoint in self.connections.keys()
    
    def __getitem__(self, endpoint: endpoint) -> Connection:
        return self.connections[endpoint]
    
    def add_connection(self, socket: socket, udp_socket: UdpSocket) -> Connection | None:
        with self.lock:
            endpoint = socket.getpeername()
            if endpoint in self:
                debug_print(f"connection already made!")
                return None
            connection = Connection(socket, udp_socket)
            self.connections[endpoint] = connection
            self.sockets.append(socket)
            udp_socket.add_keep_alive_target(endpoint)
            return connection
    
    def _disconnect_socket(self, socket: socket):
        endpoint = socket.getpeername()
        if endpoint in self:
            connection = self.connections.pop(endpoint)
            connection._disconnect()
            self.sockets.remove(socket)
            connection.udp_socket.remove_keep_alive_target(endpoint)
            self.disconnections.add(connection)

    def receive(self) -> list[tuple[bytes, endpoint]]:
        with self.lock:
            for connection in list(self.connections.values()):
                if connection.closed:
                    self._disconnect_socket(connection.tcp_socket)
            if len(self.sockets) == 0:
                return []
            result = []
            rlist, _, xlist = select(self.sockets, [], self.sockets, 0)
            for socket in xlist:
                self._disconnect_socket(socket)
            for socket in rlist:
                if socket in xlist:
                    continue
                data = socket.recv(BUFSIZE)
                if data:
                    endpoint = socket.getpeername()
                    result.append((data, endpoint))
                else:
                    self._disconnect_socket(socket)
            return result

    def take_disconnections(self) -> list[Connection]:
        with self.lock:
            disconnections = list(self.disconnections)
            self.disconnections.clear()
            return disconnections
        
    def disconnect_all(self):
        with self.lock:
            for endpoint in self.connections.keys():
                connection = self.connections[endpoint]
                connection._disconnect()
            
            self.connections.clear()
            self.disconnections.clear()
            self.sockets.clear()

