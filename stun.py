from socket import *
from random import randbytes
from ipaddress import IPv4Address, IPv6Address

# Send a STUN message to a server, with optional extra data
def send_stun_request(sock: socket, addr: tuple[str, int]) -> bytes:
    trans_id = randbytes(16)
    message_start = b'\x00\x01\x00\x00' # x0001 is bind msg rqst; 0000 is message length
    sock.sendto(message_start + trans_id, addr)
    return trans_id

def get_int(bytes: bytes) -> int:
    return int.from_bytes(bytes, byteorder="big")

def stun_response_valid(bytes: bytes, transaction_id: bytes) -> bool:
    # Too short, not a valid message
    if len(bytes) < 20:
        return False
    received_transaction_id = bytes[4:20]
    return received_transaction_id == transaction_id

# returns the external ip address and port number of the socket
def get_stun_response(sock: socket, addr: tuple[str, int], max_timeouts: int) -> tuple[IPv4Address | IPv6Address, int]:
    timeouts = 0
    while True:
        try:
            transaction_id = send_stun_request(sock, addr)
            data = sock.recv(2048)
            if not stun_response_valid(data, transaction_id):
                raise timeout # timeout if invalid response
            
        except timeout:
            timeouts += 1
            if timeouts >= max_timeouts:
                raise timeout
            continue

        attributes = data[20:]
        while len(attributes) > 0:
            type, length = attributes[0:2], get_int(attributes[2:4])
            value = attributes[4:4+length]

            attributes = attributes[4+length:]
            
            if type == b'\x00\x01': # MAPPED-ADDRESS
                family = value[1]
                extPort = get_int(value[2:4])
                extAddress = IPv4Address(value[4:8]) if family == 0x01 else IPv6Address(value[4:20]) #0x02
                return (extAddress, extPort)
        raise gaierror # could not find the address
    

# Get the network topology, external IP, and external port
def get_ip_info(sock: socket, stun_hosts: list[(str, int)], max_timeouts: int =5) -> tuple[IPv4Address | IPv6Address | None, int | None]:
    old_timeout = sock.gettimeout()
    sock.settimeout(0.5)
    response = (None, None)

    for stun_addr in stun_hosts:
        try:
            response = get_stun_response(sock, stun_addr, max_timeouts)
            break
        except Exception:  # host not found, or timeout
            continue
    
    sock.settimeout(old_timeout)
    return response

