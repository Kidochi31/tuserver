from socket import socket, AddressFamily
from common import make_socket_reusable, BUFSIZE, DUMMY_ENDPOINT
from select import select
from threading import Lock, Timer
from stun import get_ip_info
from iptools import *

class UdpSocket:
    # socket: socket - the udp socket to be used
    # local_endpoint: IP_endpoint - the endpoint the udp socket is bound to
    # external_endpoint: IP_endpoint | None - the endpoint the udp socket is bound to on the open internet
    # keep_alive_timer: Timer - used to ensure that the hole is kept open in the NAT
    # send_lock: Lock
    # keep_alive_targets: set[endpoint] - Udp packets will be sent to these endpoints every 10 seconds to keep udp connections alive
    # closed: bool
    def __init__(self, local_endpoint: IP_endpoint, stun_hosts: list[unresolved_endpoint], family: AddressFamily):
        self.socket = create_udp_socket(local_endpoint, family)
        self.local_endpoint = local_endpoint
        self.external_endpoint = get_ip_info(self.socket, stun_hosts)
        
        self.keep_alive_targets: set[IP_endpoint] = set()
        dummy_endpoint = resolve_to_canonical_endpoint(DUMMY_ENDPOINT, self.socket.family)
        if dummy_endpoint is not None:
            self.keep_alive_targets.add(dummy_endpoint)
        
        self.keep_alive_timer = Timer(interval=10, function=self.keep_alive)
        self.keep_alive_timer.start()
        self.send_lock = Lock()
        self.closed = False
    
    def _ready_to_receive(self) -> bool:
        try:
            rlist, _, _ = select([self.socket], [], [], 0)
            return len(rlist) > 0
        except:
            return False
    
    def get_external_endpoint(self) -> IP_endpoint | None:
        return self.external_endpoint

    def receive(self) -> list[tuple[bytes, IP_endpoint | None]]:
        result: list[tuple[bytes, IP_endpoint | None]] = []
        while self._ready_to_receive():
            try:
                data, endpoint = self.socket.recvfrom(BUFSIZE)
                if data != b'':
                    result.append((data, get_canonical_endpoint(endpoint, self.socket.family)))
            except:
                break
        return result
    
    def send_to(self, data: bytes, endpoint: IP_endpoint):
        with self.send_lock:
            if self.closed:
                return
            try:
                self.socket.sendto(data, endpoint)
            except:
                return
    
    def add_keep_alive_target(self, endpoint: IP_endpoint):
        with self.send_lock:
            self.keep_alive_targets.add(endpoint)
        self.send_to(b'', endpoint)

    def remove_keep_alive_target(self, endpoint: IP_endpoint):
        with self.send_lock:
            self.keep_alive_targets.remove(endpoint)

    def keep_alive(self):
        if self.closed:
            return
        endpoints = None
        with self.send_lock:
            endpoints = list(self.keep_alive_targets)
        for endpoint in endpoints:
            self.send_to(b'', endpoint)
        with self.send_lock:
            if self.closed:
                return
            self.keep_alive_timer.cancel()
            self.keep_alive_timer = Timer(interval=10, function=self.keep_alive)
            self.keep_alive_timer.start()
    
    def close(self):
        with self.send_lock:
            self.closed = True
            self.keep_alive_timer.cancel()
            self.socket.close()
    
def create_udp_socket(local_endpoint: IP_endpoint, family: AddressFamily) -> socket:
    udp_socket = socket(family, SOCK_DGRAM)
    make_socket_reusable(udp_socket)
    udp_socket.bind(local_endpoint) # bind the socket
    return udp_socket