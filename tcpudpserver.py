from socket import socket
from threading import Lock
from holepuncher import HolePuncher
from listener import Listener
from connection import Connection
from collections.abc import Callable
from udpsocket import UdpSocket
from common import CONNECT_DESTINATION, IPV6_LOOPBACK, IPV4_LOOPBACK, make_socket_reusable
from connectioncollection import ConnectionCollection
from iptools import *

# Hole Punch Server using TCP UDP connections
IPV4 = AF_INET
IPV6 = AF_INET6

class Server:
    # family: AddressFamily - whether the server uses IPv6 or IPv4
    # holepuncher: HolePuncher - the hole puncher used to create active tcp connections
    # listener: Listener - the object managing accepting new connections passively
    # udp_socket: UdpSocket - the UDP socket attached to the same port as the listener
    # local_endpoint: IP_endpoint - the endpoint the listener is bound to
    # connections: ConnectionCollection - the collection of Connections
    # lock: Lock
    # closed: bool - True if the Server has closed

    # Callbacks:
    # on_connect(Server, Connection) - when the Server creates a new Connection
    # on_hole_punch_fail(Server, IP_endpoint) - when a hole punch times out or otherwise fails
    # on_receive_reliable(Server, data, Connection) - when reliable data is received from a Connection
    # on_receive_unreliable(Server, data, Connection) - when unreliable data is received from a Connection
    # on_disconnect(Server, Connection) - when a Connection disconnects
    def __init__(self, on_connect: Callable[['Server', Connection], None],
                 on_hole_punch_fail: Callable[['Server', IP_endpoint], None],
                 on_receive_reliable: Callable[['Server', bytes, Connection], None],
                 on_receive_unreliable: Callable[['Server', bytes, Connection], None],
                 on_disconnect: Callable[['Server', Connection], None],
                 stun_hosts: list[unresolved_endpoint],
                 family: AddressFamily,
                 listen: bool = True,
                 port: int = 0):
        # create a TCP socket that will listen for incoming connections
        self.family = family
        self.listener = Listener(family, listen, port)
        self.local_endpoint = self.listener.get_local_endpoint()
        self.udp_socket = UdpSocket(self.local_endpoint, stun_hosts, family)
        self.holepuncher = HolePuncher(self.local_endpoint, family)
        self.connections = ConnectionCollection()
        self.lock = Lock()
        self.closed = False

        self.on_connect = on_connect
        self.on_hole_punch_fail = on_hole_punch_fail
        self.on_receive_reliable = on_receive_reliable
        self.on_receive_unreliable = on_receive_unreliable
        self.on_disconnect = on_disconnect

    def hole_punch(self, endpoint: unresolved_endpoint, timeout: float | None) -> bool:
        with self.lock:
            if self.closed:
                return False
            ip_endpoint = resolve_to_canonical_endpoint(endpoint, self.family)
            if ip_endpoint is None:
                return False
            self.holepuncher.hole_punch(ip_endpoint, timeout)
            return True

    def stop_hole_punch(self, endpoint: unresolved_endpoint):
        with self.lock:
            ip_endpoint = resolve_to_canonical_endpoint(endpoint, self.family)
            if ip_endpoint is None:
                return
            self.holepuncher.remove_hole_puncher(ip_endpoint)

    def get_local_endpoint(self) -> IP_endpoint:
        return self.local_endpoint

    def get_external_endpoint(self) -> IP_endpoint | None:
        return self.udp_socket.external_endpoint
    
    def get_loopback_endpoint(self) -> IP_endpoint | None:
        try:
            s = socket(self.family, SOCK_DGRAM)
            if self.family == AF_INET6:
                s.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
            make_socket_reusable(s)
            s.bind(self.get_local_endpoint())
            endpoint = resolve_to_canonical_endpoint(IPV4_LOOPBACK if self.family == AF_INET else IPV6_LOOPBACK, self.family)
            if endpoint is None:
                return None
            s.connect(endpoint) # type: ignore
            return get_canonical_local_endpoint(s)
        except Exception:
            return None
    
    def get_lan_endpoint(self) -> IP_endpoint | None:
        try:
            s = socket(self.family, SOCK_DGRAM)
            if self.family == AF_INET6:
                s.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
            s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            make_socket_reusable(s)
            s.bind(self.get_local_endpoint())
            endpoint = resolve_to_canonical_endpoint(CONNECT_DESTINATION, self.family)
            if endpoint is None:
                return None
            s.connect(endpoint) # type: ignore
            return get_canonical_local_endpoint(s)
        except Exception:
            return None

    def _manage_new_connection(self, socket: socket)-> Connection | None:
        connection = self.connections.add_connection(socket, self.udp_socket)
        if connection is None:
            return None
        self.holepuncher.remove_hole_puncher(connection.remote_endpoint)
        return connection
    
    def tick(self):
        try:
            hole_punch_fails: list[IP_endpoint] = []
            new_connections: list[Connection] = []
            disconnects: list[Connection] = []
            receive_unreliable: list[tuple[bytes, Connection]] = []
            receive_reliable: list[tuple[bytes, Connection]] = []
            with self.lock:
                if self.closed:
                    return
                # first manage all hole punch failures
                for endpoint in self.holepuncher.take_fails():
                    hole_punch_fails.append(endpoint)
                
                # next manage all successful connections
                for socket in self.holepuncher.take_successes():
                    connection = self._manage_new_connection(socket)
                    if connection is not None:
                        new_connections.append(connection)
                for socket in self.listener.take_new_connections():
                    connection = self._manage_new_connection(socket)
                    if connection is not None:
                        new_connections.append(connection)
                
                # next read new data (but don't manage yet)
                unreliable_data = self.udp_socket.receive()
                reliable_data = self.connections.receive()

                # manage all disconnections
                for connection in self.connections.take_disconnections():
                    disconnects.append(connection)
                
                # manage new data
                for data, endpoint in unreliable_data:
                    if endpoint is None or endpoint not in self.connections:
                        continue
                    connection = self.connections[endpoint]
                    receive_unreliable.append((data, connection))
                for data, endpoint in reliable_data:
                    connection = self.connections[endpoint]
                    receive_reliable.append((data, connection))
            # end of lock
            for endpoint in hole_punch_fails:
                self.on_hole_punch_fail(self, endpoint)
            for connection in new_connections:
                self.on_connect(self, connection)
            for connection in disconnects:
                self.on_disconnect(self, connection)
            for data, connection in receive_unreliable:
                self.on_receive_unreliable(self, data, connection)
            for data, connection in receive_reliable:
                self.on_receive_reliable(self, data, connection)
        except:
            self.close()
            raise

    
    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.listener.close()
            self.holepuncher.clear()
            self.udp_socket.close()
            self.connections.disconnect_all()
