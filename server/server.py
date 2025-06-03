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
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((state.HOST, state.PORT))
    server.listen()
    print(f"[SERVER] Listening on {state.HOST}:{state.PORT}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        for conn in state.clients:
            conn.close()
        server.close()

if __name__ == "__main__":
    start_server()