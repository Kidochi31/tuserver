from sys import argv
from socket import *
from stun import get_ip_info

STUN_SERVERS = [('stun.ekiga.net', 3478), ('stun.ideasip.com', 3478), ('stun.voiparound.com', 3478),
                ('stun.voipbuster.com', 3478), ('stun.voipstunt.com', 3478), ('stun.voxgratia.org', 3478)]

def main():
    if len(argv) < 2 or len(argv) > 3:
        print("Usage: python runstun.py port [server:port]")
        exit()
    
    port = int(argv[1])
    server = []
    if len(argv) >= 3:
        host_name, host_port = argv[2].split(":")
        host_port = int(host_port)
        server = [(host_name, host_port)]
    
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(("", port))

    external_address, external_port = get_ip_info(sock, server + STUN_SERVERS)
    print(external_address)
    print(external_port)

if __name__ == "__main__":
    main()