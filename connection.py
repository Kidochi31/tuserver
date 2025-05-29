from socket import socket
from udpsocket import UdpSocket
from iptools import *

class Connection:
    # tcp_socket: socket - the socket of the tcp connection
    # udp_socket: UdpSocket - the socket of the udp connection
    # local_endpoint: IP_endpoint - the local endpoint of the sockets
    # remote_endpoint: IP_endpoint - the destination of the sockets
    # closed: bool - whether the connection has been closed

    def __init__(self, tcp_socket: socket, udp_socket: UdpSocket):
        self.tcp_socket = tcp_socket
        self.udp_socket = udp_socket
        self.local_endpoint = get_canonical_local_endpoint(tcp_socket)
        self.remote_endpoint = get_canonical_remote_endpoint(tcp_socket)
        self.closed = False
    
    def close(self):
        self.closed = True
    
    
    
    def send_unreliable(self, data: bytes):
        if self.closed:
            return
        try:
            self.udp_socket.send_to(data, self.remote_endpoint)
        except Exception:
            self.close()
    
    def send_reliable(self, data:bytes):
        if self.closed:
            return
        try:
            self.tcp_socket.sendall(data)
        except Exception:
            self.close()