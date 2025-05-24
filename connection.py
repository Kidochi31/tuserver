from socket import *
from common import BUFSIZE, endpoint
from udpsocket import UdpSocket

from collections.abc import Callable

class Connection:
    # tcp_socket: socket - the socket of the tcp connection
    # udp_socket: UdpSocket - the socket of the udp connection
    # local_endpoint: endpoint - the local endpoint of the sockets
    # remote_endpoint: endpoint - the destination of the sockets
    # closed: bool - whether the connection has been closed

    def __init__(self, tcp_socket: socket, udp_socket: UdpSocket):
        self.tcp_socket = tcp_socket
        self.udp_socket = udp_socket
        self.local_endpoint = tcp_socket.getsockname()
        self.remote_endpoint = tcp_socket.getpeername()
        self.closed = False
    
    def close(self):
        self.closed = True
    
    def _disconnect(self):
        self.closed = True
        try:
            self.tcp_socket.shutdown(SHUT_RDWR)
        except Exception:
            pass
        try:
            self.tcp_socket.close()
        except Exception:
            pass
    
    def send_unreliable(self, data: bytes):
        if self.closed:
            return
        self.udp_socket.send_to(data, self.remote_endpoint)
    
    def send_reliable(self, data:bytes):
        if self.closed:
            return
        try:
            self.tcp_socket.sendall(data)
        except Exception:
            self.close()