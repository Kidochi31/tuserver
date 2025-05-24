from socket import *
from common import endpoint, make_socket_reusable, BUFSIZE, DUMMY_ENDPOINT
from select import select
from threading import Lock, Timer
from stun import get_ip_info

class UdpSocket:
    # socket: socket - the udp socket to be used
    # local_endpoint: endpoint - the endpoint the udp socket is bound to
    # external_endpoint: endpoint | None - the endpoint the udp socket is bound to on the open internet
    # keep_alive_timer: Timer - used to ensure that the hole is kept open in the NAT
    # send_lock: Lock
    # keep_alive_targets: set[endpoint] - Udp packets will be sent to these endpoints every 10 seconds to keep udp connections alive
    # closed: bool
    def __init__(self, local_endpoint: endpoint, stun_hosts: list[endpoint]):
        self.socket = create_udp_socket(local_endpoint)
        self.local_endpoint = local_endpoint
        self.external_endpoint = get_ip_info(self.socket, stun_hosts)
        self.keep_alive_targets: set[endpoint] = set([DUMMY_ENDPOINT])
        self.keep_alive_timer = Timer(interval=10, function=self.keep_alive)
        self.keep_alive_timer.start()
        self.send_lock = Lock()
        self.closed = False
    
    def _ready_to_receive(self) -> bool:
        rlist, _, _ = select([self.socket], [], [], 0)
        return len(rlist) > 0
    
    def get_external_endpoint(self) -> endpoint | None:
        return self.external_endpoint

    def receive(self) -> list[tuple[bytes, endpoint]]:
        result = []
        while self._ready_to_receive():
            data, endpoint = self.socket.recvfrom(BUFSIZE)
            if data != b'':
                result.append((data, endpoint))
        return result
    
    def send_to(self, data: bytes, endpoint: endpoint):
        with self.send_lock:
            if self.closed:
                return
            self.socket.sendto(data, endpoint)
    
    def add_keep_alive_target(self, endpoint: endpoint):
        with self.send_lock:
            self.keep_alive_targets.add(endpoint)
        self.send_to(b'', endpoint)

    def remove_keep_alive_target(self, endpoint: endpoint):
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
    
def create_udp_socket(local_endpoint: endpoint) -> socket:
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    make_socket_reusable(udp_socket)
    udp_socket.bind(local_endpoint) # bind the socket
    return udp_socket