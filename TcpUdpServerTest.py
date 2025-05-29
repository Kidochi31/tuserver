from tcpudpserver import *
from threading import Thread
import traceback
from iptools import IP_endpoint

should_quit = None

def main():
    connections: list[Connection] = []

    def on_disconnect(server: Server, connection: Connection):
        print(f"client at {connection.remote_endpoint} disconnected.")
        connections.remove(connection)
    
    def on_connect(server: Server, connection: Connection):
        print(f"client at {connection.remote_endpoint} connected.")
        connections.append(connection)

    stun_hosts = [("stun.ekiga.net", 3478)]
    
    server = Server(on_connect, on_hole_punch_fail, on_receive_reliable, on_receive_unreliable, on_disconnect, stun_hosts, IPV4)
    
    print(f"ExternalAddress: {server.get_external_endpoint()}")
    print(f"LANAddress: {server.get_lan_endpoint()}")
    print(f"LoopbackAddress: {server.get_loopback_endpoint()}")

    def tick_func():
        while not server.closed:
            server.tick()

    tick_thread = Thread(target=tick_func)
    tick_thread.start()
    
    try:
        while True:
            if server.closed:
                break
            text = input("")
            if text == "quit":
                server.close()
            elif text.startswith("holepunch "):
                text = text.removeprefix("holepunch ")
                address, port = text.split(":", maxsplit=1)
                port = int(port)
                endpoint = (address, port)
                server.hole_punch(endpoint, None)
            elif text.startswith("udp "):
                text = text.removeprefix("udp ")
                for connection in connections:
                    connection.send_unreliable(text.encode())
            else:
                for connection in connections:
                    connection.send_reliable(text.encode())
    except BaseException as e:
        print(f"\nException in main loop: {traceback.format_exc()}")
        server.close()
    
    print("Main Thread Ended")

def on_receive_reliable(server: Server, data: bytes, connection: Connection):
    print(f"from {connection.remote_endpoint}: {data.decode()}")

def on_receive_unreliable(server: Server, data: bytes, connection: Connection):
    print(f"from {connection.remote_endpoint} via udp: {data.decode()}")

def on_hole_punch_fail(server: Server, endpoint: IP_endpoint):
    print(f"failed to hole punch: {endpoint}")

if __name__ == "__main__":
    main()