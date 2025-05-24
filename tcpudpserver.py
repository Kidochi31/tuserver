from socket import *
import traceback
from threading import Lock, Thread
from select import select
from holepuncher import HolePuncher
from listener import Listener
from connection import Connection
from collections.abc import Callable
import typing
from udpsocket import UdpSocket
from common import endpoint, make_socket_reusable, BUFSIZE
from connectioncollection import ConnectionCollection
from stun import get_ip_info

# Hole Punch Server using TCP UDP connections

class Server:
    # holepuncher: HolePuncher - the hole puncher used to create active tcp connections
    # listener: Listener - the object managing accepting new connections passively
    # udp_socket: UdpSocket - the UDP socket attached to the same port as the listener
    # external_endpoint: endpoint | None - the endpoint the listener is bound to on the open internet
    # local_endpoint: endpoint - the endpoint the listener is bound to
    # connections: ConnectionCollection - the collection of Connections
    # lock: Lock
    # closed: bool - True if the Server has closed

    # Callbacks:
    # on_connect(Server, Connection) - when the Server creates a new Connection
    # on_hole_punch_fail(Server, endpoint) - when a hole punch times out or otherwise fails
    # on_receive_reliable(Server, data, Connection) - when reliable data is received from a Connection
    # on_receive_unreliable(Server, data, Connection) - when unreliable data is received from a Connection
    # on_disconnect(Server, Connection) - when a Connection disconnects
    def __init__(self, on_connect: Callable[['Server', Connection], None],
                 on_hole_punch_fail: Callable[['Server', endpoint], None],
                 on_receive_reliable: Callable[['Server', bytes, Connection], None],
                 on_receive_unreliable: Callable[['Server', bytes, Connection], None],
                 on_disconnect: Callable[['Server', Connection], None],
                 stun_hosts: list[endpoint]):
        # create a TCP socket that will listen for incoming connections
        self.listener = Listener()
        self.local_endpoint = self.listener.get_local_endpoint()
        self.udp_socket = UdpSocket(self.local_endpoint, stun_hosts)
        self.external_endpoint = self.udp_socket.external_endpoint
        self.holepuncher = HolePuncher(self.local_endpoint)
        self.connections = ConnectionCollection()
        self.lock = Lock()
        self.closed = False

        self.on_connect = on_connect
        self.on_hole_punch_fail = on_hole_punch_fail
        self.on_receive_reliable = on_receive_reliable
        self.on_receive_unreliable = on_receive_unreliable
        self.on_disconnect = on_disconnect

    def hole_punch(self, endpoint: endpoint):
        with self.lock:
            if self.closed:
                return
            self.holepuncher.hole_punch(endpoint)

    def get_local_endpoint(self) -> endpoint:
        return self.local_endpoint

    def get_external_endpoint(self) -> endpoint | None:
        return self.external_endpoint
    
    def get_loopback_endpoint(self) -> endpoint:
        return ('127.0.0.1', self.local_endpoint[1])
    
    def get_lan_endpoints(self) -> list[endpoint]:
        infos = getaddrinfo(gethostname(), None, family=AF_INET, proto=IPPROTO_TCP, type=SOCK_STREAM)[0]
        endpoints = []
        for info in infos:
            endpoint = (str(infos[4][0]), self.local_endpoint[1])
            if endpoint not in endpoints:
                endpoints.append(endpoint)
        return endpoints

    def _manage_new_connection(self, socket: socket)-> Connection | None:
        connection = self.connections.add_connection(socket, self.udp_socket)
        if connection is None:
            return None
        self.holepuncher.remove_hole_puncher(connection.remote_endpoint)
        return connection
    
    def tick(self):
        hole_punch_fails: list['endpoint'] = []
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
            
            # managae new data
            for data, endpoint in unreliable_data:
                if endpoint not in self.connections:
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

    
    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.listener.close()
            self.holepuncher.clear()
            self.udp_socket.close()
            self.connections.disconnect_all()
