# Standard and third-party imports
from colorama import Fore, Style, init
init(autoreset=True)

# Standard library imports
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.protocol import encode_message, decode_message, MessageType
import socket
import threading

# Client configuration and allowed values
HOST = '127.0.0.1'
PORT = 3001

def receive_messages(sock):
    """
    Continuously listen for incoming messages from the server and display them with appropriate color coding.
    """
    buffer = ""

    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            buffer += data.decode()
            
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                msg_type, payload = decode_message(line.strip())
                
                color_map = {
                    "MSG": Fore.CYAN,
                    "VOTE": Fore.YELLOW,
                    "ROLE": Fore.MAGENTA,
                    "STATE": Fore.GREEN,
                    "JOIN": Fore.BLUE,
                    "START": Fore.LIGHTGREEN_EX,
                    "KILL": Fore.RED
                }
                color = color_map.get(msg_type, Fore.WHITE)
                
                if msg_type == "ROLE":
                    print(f"\n{color}You are a {payload}!{Style.RESET_ALL}")
                elif msg_type == "STATE":
                    if payload == "villagers_win":
                        print(f"\n{Fore.GREEN}🎉 Villagers win!{Style.RESET_ALL}")
                    elif payload == "werewolves_win":
                        print(f"\n{Fore.RED}🐺 Werewolves win!{Style.RESET_ALL}")
                    elif payload == "day":
                        print(f"\n{color}☀️ Day has begun!{Style.RESET_ALL}")
                    elif payload == "night":
                        print(f"\n{color}🌙 Night has fallen...{Style.RESET_ALL}")
                    else:
                        print(f"\n{color}[STATE]{Style.RESET_ALL} {payload}")
                else:
                    print(f"\n{color}[{msg_type}]{Style.RESET_ALL} {payload}")
                    
                print(f"{Fore.BLUE}> {Style.RESET_ALL}", end="")
                
        except:
            break

def main():
    """
    Establish connection to the server, handle user input commands, validate inputs, and send encoded messages accordingly.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        pseudo = input("Enter your username: ")
        os.system('cls' if os.name == 'nt' else 'clear')
        print(Fore.LIGHTGREEN_EX + "🎮 Welcome to the Werewolf Game!\n" + Style.RESET_ALL)
        join_msg = encode_message(MessageType.JOIN.value, pseudo)
        sock.sendall(join_msg.encode())

        VALID_ROLES = {"villager", "werewolf", "seer", "witch", "hunter"}
        VALID_STATES = {"day", "night"}

        # Start a thread to listen for messages from server asynchronously
        thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
        thread.start()

        try:
            while True:
                msg = input(f"{Fore.BLUE}> {Style.RESET_ALL}")
                if msg.lower() in ('exit', 'quit'):
                    break
                elif msg.startswith("/vote "):
                    # Handle vote command: extract target and send a VOTE message
                    target = msg.split(" ", 1)[1]
                    formatted_msg = encode_message(MessageType.VOTE.value, target)
                elif msg.startswith("/role "):
                    # Handle role command: validate role and send ROLE message if valid
                    role = msg.split(" ", 1)[1].lower()
                    if role not in VALID_ROLES:
                        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Invalid role: '{role}'")
                        continue
                    formatted_msg = encode_message(MessageType.ROLE.value, role)
                elif msg.startswith("/state "):
                    # Handle state command: validate state and send STATE message if valid
                    state = msg.split(" ", 1)[1].lower()
                    if state not in VALID_STATES:
                        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Invalid state: '{state}'")
                        continue
                    formatted_msg = encode_message(MessageType.STATE.value, state)
                elif msg.strip() == "/start":
					# Handle start command: send START message
                     formatted_msg = encode_message(MessageType.START.value, "")
                else:
                    # Default case: treat input as a normal chat message and send MSG message
                    formatted_msg = encode_message(MessageType.MSG.value, msg)
                sock.sendall(formatted_msg.encode())
        except KeyboardInterrupt:
            print("\n[CLIENT] Exiting...")
        finally:
            sock.close()

if __name__ == "__main__":
    main()
    