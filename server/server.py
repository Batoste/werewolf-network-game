import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import socket
import threading
from common.protocol import decode_message

HOST = '127.0.0.1'
PORT = 3001

clients = []

def broadcast(sender_conn, message):
    """
    Send message to all clients except the sender
    """
    for client in clients:
        if client != sender_conn:
            try:
                client.sendall(message.encode())
            except:
                pass

def handle_client(conn, addr):
    """
    Handle communication with a single client
    """
    print(f"[+] New connection from {addr}")
    clients.append(conn)
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = data.decode().strip()
            print(f"[{addr}] {message}")

            msg_type, payload = decode_message(message)
            if msg_type == "MSG":
                broadcast(conn, message)
    except ConnectionResetError:
        print(f"[!] Connection lost with {addr}")
    finally:
        conn.close()
        if conn in clients:
            clients.remove(conn)
        print(f"[-] Disconnected {addr}")

def start_server():
    """
    Start TCP server and accept multiple client connections
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER] Listening on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        for conn in clients:
            conn.close()
        server.close()

if __name__ == "__main__":
    start_server()