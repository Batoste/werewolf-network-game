import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.protocol import encode_message, MessageType
import socket
import threading

HOST = '127.0.0.1'
PORT = 3001

def receive_messages(sock):
    """
    Listen for incoming messages from the server
    """
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            print(f"[SERVER] {data.decode().strip()}")
        except:
            break

def main():
    """
    Connect to the server and send messages from user input
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"[CLIENT] Connected to {HOST}:{PORT}")

        # Start a thread to listen for messages from server
        thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
        thread.start()

        try:
            while True:
                msg = input()
                if msg.lower() in ('exit', 'quit'):
                    break
                # Send user input as a MSG type message
                formatted_msg = encode_message(MessageType.MSG.value, msg)
                sock.sendall(formatted_msg.encode())
        except KeyboardInterrupt:
            print("\n[CLIENT] Exiting...")
        finally:
            sock.close()

if __name__ == "__main__":
    main()