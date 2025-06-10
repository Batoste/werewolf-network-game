"""Entry point of the Werewolf server."""

import socket
import threading

from config import HOST, PORT
from .handler import handle_client
from .state import state


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
    server.bind((HOST, PORT))
    # Start listening for incoming connections
    server.listen()
    print(f"[SERVER] Listening on {HOST}:{PORT}")

    try:
        while True:
            # Accept a new client connection
            conn, addr = server.accept()
            # Spawn a new thread to handle the client
            thread = threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            )
            thread.start()
    except KeyboardInterrupt:
        # Handle graceful shutdown on keyboard interrupt
        print("\n[SERVER] Shutting down...")
    finally:
        # Close all client connections
        with state.lock:
            for conn in state.clients:
                conn.close()
        # Close the server socket
        server.close()


if __name__ == "__main__":
    start_server()
