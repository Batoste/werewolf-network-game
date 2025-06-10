from PyQt5.QtCore import QObject, pyqtSignal
import socket
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.protocol import encode_message, decode_message, MessageType


class NetworkWorker(QObject):
    message_received = pyqtSignal(str, str)
    connection_lost = pyqtSignal()
    connected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.sock = None
        self.running = False
        self.buffer = ""

    # Server configuration
    SERVER_PORT = 3001
    
    def connect_to_server(self, username):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(("localhost", self.SERVER_PORT))
            join_msg = encode_message(MessageType.JOIN.value, username)
            self.sock.sendall(join_msg.encode())
            self.running = True
            self.connected.emit()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def listen_for_messages(self):
        while self.running and self.sock:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                self.buffer += data.decode()
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line.strip():
                        msg_type, payload = decode_message(line.strip())
                        self.message_received.emit(msg_type, payload)
            except Exception as e:
                print(f"Receive error: {e}")
                break
        self.connection_lost.emit()

    def send_message(self, msg_type, payload):
        if self.sock and self.running:
            try:
                formatted_msg = encode_message(msg_type, payload)
                self.sock.sendall(formatted_msg.encode())
                
                # Record certain commands in the history
                if msg_type in [MessageType.VOTE.value, MessageType.NIGHT_VOTE.value, MessageType.START.value, MessageType.RESTART.value]:
                    cmd = f"/{msg_type.lower()}"
                    if payload:
                        cmd += f" {payload}"
                    self.message_received.emit("COMMANDE", f"Commande send: {cmd}")
            except Exception as e:
                print(f"Send error: {e}")

    def disconnect(self):
        self.running = False
        if self.sock:
            self.sock.close()