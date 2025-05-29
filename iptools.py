from socket import *
from ipaddress import ip_address
from typing import Union


IPv4_endpoint = tuple[str, int]
IPv6_endpoint = tuple[str, int, int, int]

ADDRESS = 0
PORT = 1
FLOWINFO = 2
SCOPEID = 3

IP_endpoint = Union[IPv4_endpoint,IPv6_endpoint]
unresolved_endpoint = tuple[str, int]


def get_endpoint_family(endpoint: IP_endpoint) -> AddressFamily:
    if len(endpoint) == 2:
        return AF_INET
    if len(endpoint) == 4:
        return AF_INET6
    return AF_INET6

def ipv4_to_canonical_ipv6(endpoint: IPv4_endpoint) -> IPv6_endpoint:
    addr_str = "::ffff:"+endpoint[ADDRESS]
    ip = ip_address(addr_str)
    return (ip.compressed, endpoint[PORT], 0, 0)

def ipv6_to_ipv4(endpoint: IPv6_endpoint) -> IPv4_endpoint | None:
    ip = ip_address(endpoint[ADDRESS]).ipv4_mapped
    if ip is None:
        return None
    return (ip.compressed, endpoint[PORT])

def ipv6_to_canonical_ipv6(endpoint: IPv6_endpoint) -> IPv6_endpoint:
    ip = ip_address(endpoint[ADDRESS])
    return (ip.compressed, endpoint[PORT], endpoint[FLOWINFO], endpoint[SCOPEID])

def get_canonical_ipv6(endpoint: IP_endpoint) -> IPv6_endpoint:
    family = get_endpoint_family(endpoint)
    if family == AF_INET: # ipv4
        return ipv4_to_canonical_ipv6(endpoint)
    else: # ipv6
        return ipv6_to_canonical_ipv6(endpoint)

def get_ipv4(endpoint: IP_endpoint) -> IPv4_endpoint | None:
    family = get_endpoint_family(endpoint)
    if family == AF_INET: # ipv4
        return endpoint
    else: # ipv4
        return ipv6_to_ipv4(endpoint)
    
def get_canonical_endpoint(endpoint: IP_endpoint, family: AddressFamily) -> IP_endpoint | None:
    if family == AF_INET: # ipv4
        return get_ipv4(endpoint)
    else: # ipv6
        return get_canonical_ipv6(endpoint)

def resolve_to_canonical_ipv6(endpoint: unresolved_endpoint) -> IPv6_endpoint | None:
    try:
        address_ipv6:IPv6_endpoint = getaddrinfo(endpoint[ADDRESS], endpoint[PORT], family=AF_INET6)[0][-1]
        return ipv6_to_canonical_ipv6(address_ipv6)
    except Exception:
        pass
    try:
        address_ipv4:IPv4_endpoint = getaddrinfo(endpoint[ADDRESS], endpoint[PORT], family=AF_INET)[0][-1]
        return ipv4_to_canonical_ipv6(address_ipv4)
    except Exception:
        pass
    return None

def resolve_to_ipv4(endpoint: unresolved_endpoint) -> IPv4_endpoint | None:
    try:
        address_ipv4:IPv4_endpoint = getaddrinfo(endpoint[ADDRESS], endpoint[PORT], family=AF_INET)[0][-1]
        return address_ipv4
    except Exception:
        pass
    return None

def resolve_to_canonical_endpoint(endpoint: unresolved_endpoint, family: AddressFamily) -> IP_endpoint | None:
    if family == AF_INET: # ipv4
        return resolve_to_ipv4(endpoint)
    else: # ipv6
        return resolve_to_canonical_ipv6(endpoint)

def get_canonical_local_endpoint(socket: socket) -> IP_endpoint:
    return get_canonical_endpoint(socket.getsockname(), socket.family)

def get_canonical_remote_endpoint(socket: socket) -> IP_endpoint:
    return get_canonical_endpoint(socket.getpeername(), socket.family)

def get_canonical_endpoint_with_port(endpoint: IP_endpoint, port: int, family: AddressFamily) -> IP_endpoint | None:
    if len(endpoint) == 2:
        endpoint = (endpoint[0], port)
    else:
        endpoint = (endpoint[0], port, endpoint[2], endpoint[3])
    return get_canonical_endpoint(endpoint, family)