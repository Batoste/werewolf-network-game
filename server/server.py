"""Server module to start the server, accept incoming client connections, and handle them concurrently."""

import os
import sys
import socket
import threading

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from server.state import state
from server.handler import handle_client


def start_server():
    """
    Start the server and listen for incoming connections.
    Accepts connections and spawns a new thread for each client.
    """
    # Create a TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow address reuse to avoid "address already in use" errors
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Bind the socket to the host and port specified in state
    server.bind((state.HOST, state.PORT))
    # Start listening for incoming connections
    server.listen()
    print(f"[SERVER] Listening on {state.HOST}:{state.PORT}")

    try:
        while True:
            # Accept a new client connection
            conn, addr = server.accept()
            # Spawn a new thread to handle the client
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        # Handle graceful shutdown on keyboard interrupt
        print("\n[SERVER] Shutting down...")
    finally:
        # Close all client connections
        for conn in state.clients:
            conn.close()
        # Close the server socket
        server.close()


if __name__ == "__main__":
    start_server()