from sys import argv
from socket import *
from stun import get_ip_info
from ipaddress import ip_address
from iptools import get_canonical_endpoint, resolve_to_canonical_endpoint

STUN_SERVERS = [('stun.ekiga.net', 3478), ('stun.ideasip.com', 3478), ('stun.voiparound.com', 3478),
                ('stun.voipbuster.com', 3478), ('stun.voipstunt.com', 3478), ('stun.voxgratia.org', 3478)]

def main():
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: python runstun.py port [server:port]")
        exit()

    print("get host name")
    print(resolve_to_canonical_endpoint((gethostname(), 0), AF_INET6))
    print(resolve_to_canonical_endpoint(("fe80::671f:a4bf:ffbf:40d3%11", 1000), AF_INET6))
    print(resolve_to_canonical_endpoint(("8.8.8.8", 0), AF_INET6))
    print("hole punch")
    port = int(argv[1])
    server = []
    if len(argv) >= 3:
        host_name, host_port = argv[2].split(":")
        host_port = int(host_port)
        server = [(host_name, host_port)]
    
    sock = socket(AF_INET6, SOCK_DGRAM)
    sock.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 0)
    sock.bind(("", port))

    external_address, external_port = get_ip_info(sock, server + STUN_SERVERS)
    print(external_address)
    print(external_port)

if __name__ == "__main__":
    main()