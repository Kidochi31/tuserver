import socket
import threading
import select
from stun import get_ip_info
import traceback
import time

accepted_socket = None
should_quit = None
DEBUG = False

def main():
    global accepted_socket
    global should_quit
    # STUN setup
    stun_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    stun_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        stun_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass
    stun_socket.bind(('', 0))

    ip_result = get_ip_info(stun_socket, [("stun.ekiga.net", 3478)])
    if ip_result is None:
        print("STUN failed")
        exit()
    external_ip, external_port = ip_result
    print(f"ExternalAddress: {external_ip}:{external_port}")
    print(f"LocalAddress: {stun_socket.getsockname()}")

    # TCP listener socket
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass
    listen_socket.settimeout(0.5)
    listen_socket.bind(stun_socket.getsockname())
    listen_socket.listen(1)

    # TCP connect socket
    connect_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        connect_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass
    connect_socket.bind(listen_socket.getsockname())

    address = input("Enter in the address: ")
    port = int(input("Enter in the port: "))

    stop_threads = threading.Event()
    accepted_socket = None
    wait_for_socket = threading.Event()

    input("Press any key to connect and accept...")

    # Connect thread
    def connect_func():
        endpoint = (address, port)
        while not stop_threads.is_set():
            try:
                connect_socket.connect(endpoint)
                print("Connect successful")
                wait_for_socket.set()
                return
            except Exception as e:
                if DEBUG:
                    print(f"Connect Exception: {traceback.format_exc()}")

    # Accept thread
    def accept_func():
        global accepted_socket
        while not stop_threads.is_set():
            try:
                conn, _ = listen_socket.accept()
                print("Accept successful")
                accepted_socket = conn
                wait_for_socket.set()
                return
            except Exception as e:
                if DEBUG:
                    print(f"Accept Exception: {traceback.format_exc()}")

    connect_thread = threading.Thread(target=connect_func)
    accept_thread = threading.Thread(target=accept_func)
    connect_thread.start()
    accept_thread.start()

    wait_for_socket.wait()
    stop_threads.set()

    connection :socket.socket | None = None

    if accepted_socket is None:
        print("Connected with connect_socket")
        connection = connect_socket
        
        try:
            listen_socket.close()
        except Exception as e:
            if DEBUG:
                print(f"Close Listen Exception: {traceback.format_exc()}")
    else:
        print("Connected with accepted_socket")
        connection = accepted_socket
        try:
            connect_socket.close()
        except Exception as e:
            if DEBUG:
                print(f"Close Connect Exception: {traceback.format_exc()}")
    
    print(f"Other endpoint: {connection.getpeername()}")

    print("Write text to chat. Enter \"quit\" to quit.")
    def read_func():
        global should_quit
        while (data := connection.recv(1000)) and not should_quit:
            print(data.decode())
        print("other side disconnected")
        should_quit = True
            
    
    def write_func():
        global should_quit
        try:
            while not should_quit:
                text = input("")
                if(text == "quit"):
                    print("quitting...")
                    should_quit = True
                    print("removing write thread...")
                    quit()
                connection.send(text.encode())
        except:
            print("other side disconnected")
            should_quit = True
    
    read_thread = threading.Thread(target=read_func, daemon=True)
    write_thread = threading.Thread(target=write_func, daemon=True)
    read_thread.start()
    write_thread.start()

    while True:
        if should_quit:
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            quit()
        time.sleep(0.1)

if __name__ == "__main__":
    main()