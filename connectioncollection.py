from socket import socket
from connection import Connection
from common import BUFSIZE, debug_print
from threading import Lock
from udpsocket import UdpSocket
from select import select
from iptools import *

class ConnectionCollection:
    # connections: Dictionary[endpoint, Connection] - the dictionary of Connections from the remote endpoint
    # sockets: set[socket] - a list of sockets to poll for reading
    # disconnections: list[Connection] - a list of connections that have recently disconnected but not been handled
    # lock: Lock - the lock for this connection collection
    def __init__(self):
        self.connections :dict[IP_endpoint, Connection] = {}
        self.sockets :list[socket] = []
        self.disconnections :set[Connection] = set()
        self.lock = Lock()

    def __contains__(self, endpoint: IP_endpoint) -> bool:
        return endpoint in self.connections.keys()
    
    def __getitem__(self, endpoint: IP_endpoint) -> Connection:
        return self.connections[endpoint]
    
    def add_connection(self, socket: socket, udp_socket: UdpSocket) -> Connection | None:
        with self.lock:
            endpoint = get_canonical_remote_endpoint(socket)
            if endpoint in self:
                debug_print(f"connection already made!")
                return None
            connection = Connection(socket, udp_socket)
            self.connections[endpoint] = connection
            self.sockets.append(socket)
            udp_socket.add_keep_alive_target(endpoint)
            return connection
    
    def _disconnect_socket(self, socket: socket):
        endpoint = get_canonical_remote_endpoint(socket)
        if endpoint in self:
            connection = self.connections.pop(endpoint)
            disconnect(connection)
            self.sockets.remove(socket)
            connection.udp_socket.remove_keep_alive_target(endpoint)
            self.disconnections.add(connection)

    def _get_receive_exception_sockets(self) -> tuple[list[socket], list[socket]]:
        try:
            rlist, _, xlist = select(self.sockets, [], self.sockets, 0)
            return (rlist, xlist)
        except:
            return ([], [])

    def receive(self) -> list[tuple[bytes, IP_endpoint]]:
        with self.lock:
            for connection in list(self.connections.values()):
                if connection.closed:
                    self._disconnect_socket(connection.tcp_socket)
            if len(self.sockets) == 0:
                return []
            result : list[tuple[bytes, IP_endpoint]] = []
            rlist, xlist = self._get_receive_exception_sockets()
            for socket in xlist:
                self._disconnect_socket(socket)
            for socket in rlist:
                if socket in xlist:
                    continue
                try:
                    data = socket.recv(BUFSIZE)
                except:
                    data : bytes = b''
                if data:
                    endpoint = get_canonical_remote_endpoint(socket)
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
                disconnect(connection)
            
            self.connections.clear()
            self.disconnections.clear()
            self.sockets.clear()

def disconnect(connection: Connection):
    connection.closed = True
    try:
        connection.tcp_socket.shutdown(SHUT_RDWR)
    except Exception:
        pass
    try:
        connection.tcp_socket.close()
    except Exception:
        pass