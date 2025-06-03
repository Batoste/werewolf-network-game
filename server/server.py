# Standard library imports
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Standard library imports
import socket
import threading
# Third-party or local imports
from common.protocol import decode_message, encode_message
# Global configuration and state
HOST = '127.0.0.1'
PORT = 3001

clients = []  # List of connected client sockets
usernames = {}  # Maps client sockets to usernames

def handle_join(conn, addr, payload):
    """
    Handle a JOIN message from a client.
    Register the username for the connection and log the event.
    """
    usernames[conn] = payload
    print(f"[{addr}] joined as {payload}")

def handle_msg(conn, addr, payload):
    """
    Handle a MSG message from a client.
    Broadcast the message to all other clients.
    """
    sender = usernames.get(conn, str(addr))
    print(f"[{sender}] {payload}")
    forward = encode_message("MSG", f"[{sender}] {payload}")
    broadcast(conn, forward)

def handle_vote(conn, addr, payload):
    """
    Handle a VOTE message from a client.
    Broadcast the vote to all other clients.
    """
    sender = usernames.get(conn, str(addr))
    print(f"[VOTE] {sender} voted for {payload}")
    forward = encode_message("VOTE", f"{sender} voted for {payload}")
    broadcast(conn, forward)

def handle_role(conn, addr, payload):
    """
    Handle a ROLE message: assign and notify the client of their role.
    """
    sender = usernames.get(conn, str(addr))
    print(f"[ROLE] Assigned role {payload} to {sender}")
    forward = encode_message("ROLE", f"{sender} is a {payload}")
    # Send the role assignment only to the requesting client
    conn.sendall(forward.encode())

def handle_state(conn, addr, payload):
    """
    Handle a STATE message: broadcast new game state to all clients.
    """
    print(f"[STATE] New game state: {payload}")
    forward = encode_message("STATE", payload)
    broadcast(conn, forward)

def broadcast(sender_conn, message):
    """
    Send a message to all clients except the sender.
    """
    for client in clients:
        if client != sender_conn:
            try:
                client.sendall(message.encode())
            except Exception:
                # Ignore errors sending to disconnected clients
                pass

def handle_client(conn, addr):
    """
    Handle communication with a single client.
    Receives messages, decodes them, and dispatches to appropriate handlers.
    """
    print(f"[+] New connection from {addr}")
    clients.append(conn)
    try:
        while True:
            # Continuously receive messages from the client
            data = conn.recv(1024)
            if not data:
                # Client disconnected gracefully
                break
            message = data.decode().strip()
            print(f"[{addr}] {message}")
            msg_type, payload = decode_message(message)
            
            # Dispatch based on message type
            if msg_type == "JOIN":
                handle_join(conn, addr, payload)
            elif msg_type == "MSG":
                handle_msg(conn, addr, payload)
            elif msg_type == "VOTE":
                handle_vote(conn, addr, payload)
            elif msg_type == "ROLE":
                handle_role(conn, addr, payload)
            elif msg_type == "STATE":
                handle_state(conn, addr, payload)

    except ConnectionResetError:
        # Handle abrupt client disconnects
        print(f"[!] Connection lost with {addr}")
    finally:
        # Clean up: remove client from lists and close connection
        conn.close()
        if conn in clients:
            clients.remove(conn)
        print(f"[-] Disconnected {addr}")

def start_server():
    """
    Start the TCP server and accept multiple client connections.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER] Listening on {HOST}:{PORT}")

    try:
        while True:
            # Accept new client connections and start handler threads
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        # Gracefully handle server shutdown
        print("\n[SERVER] Shutting down...")
    finally:
        # Close all client connections and server socket
        for conn in clients:
            conn.close()
        server.close()

if __name__ == "__main__":
    # Entry point: start the server
    start_server()