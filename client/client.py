# Standard library imports
import os

# Third-party imports
from colorama import Fore, Style, init
from common.protocol import encode_message, decode_message, MessageType
from config import HOST, PORT
import socket
import threading

init(autoreset=True)

# Client configuration and allowed values


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
                    "KILL": Fore.RED,
                    "NIGHT_MSG": Fore.LIGHTMAGENTA_EX,
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

        except Exception:
            break


def main():
    """
    Establish connection to the server, handle user input commands, validate inputs, and send encoded messages accordingly.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        pseudo = input("Enter your username: ")
        os.system("cls" if os.name == "nt" else "clear")
        print(
            Fore.LIGHTGREEN_EX + "🎮 Welcome to the Werewolf Game!\n" + Style.RESET_ALL
        )
        join_msg = encode_message(MessageType.JOIN.value, pseudo)
        sock.sendall(join_msg.encode())

        # Define valid roles and states for input validation
        VALID_ROLES = {"villager", "werewolf", "seer", "witch", "hunter"}
        VALID_STATES = {"day", "night"}

        # Start a thread to listen for messages from server asynchronously
        thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
        thread.start()

        try:
            while True:
                msg = input(f"{Fore.BLUE}> {Style.RESET_ALL}")
                if msg.lower() in ("exit", "quit"):
                    break

                # Handle vote command: extract target and send a VOTE message
                elif msg.startswith("/vote "):
                    target = msg.split(" ", 1)[1]
                    formatted_msg = encode_message(MessageType.VOTE.value, target)

                # Handle role command: validate role and send ROLE message if valid
                elif msg.startswith("/role "):
                    role = msg.split(" ", 1)[1].lower()
                    if role not in VALID_ROLES:
                        print(
                            f"{Fore.RED}[ERROR]{Style.RESET_ALL} Invalid role: '{role}'"
                        )
                        continue
                    formatted_msg = encode_message(MessageType.ROLE.value, role)

                # Handle state command: validate state and send STATE message if valid
                elif msg.startswith("/state "):
                    new_state = msg.split(" ", 1)[1].lower()
                    if new_state not in VALID_STATES:
                        print(
                            f"{Fore.RED}[ERROR]{Style.RESET_ALL} Invalid state: '{new_state}'"
                        )
                        continue
                    formatted_msg = encode_message(MessageType.STATE.value, new_state)

                # Handle start command: send START message
                elif msg.strip() == "/start":
                    formatted_msg = encode_message(MessageType.START.value, "")

                # Display help message
                elif msg.strip() == "/help":
                    print(
                        f"{Fore.YELLOW}Available commands:\n"
                        f"/vote <target> - Vote for a player\n"
                        f"/role <role> - Set your role (villager, werewolf, etc.)\n"
                        f"/state <state> - Change game state (day, night)\n"
                        f"/start - Start the game\n"
                        f"/help - Show this help message\n"
                        f"/exit or /quit - Exit the game{Style.RESET_ALL}"
                    )
                    continue

                # Handle restart command: send RESTART message
                elif msg.strip() == "/restart":
                    formatted_msg = encode_message(MessageType.RESTART.value, "")

                # Handle night message command: send NIGHT_MSG message
                elif msg.startswith("/nmsg "):
                    formatted_msg = encode_message(
                        MessageType.NIGHT_MSG.value, msg.split(" ", 1)[1]
                    )

                # Handle night vote command: send NIGHT_VOTE message
                elif msg.startswith("/nvote "):
                    formatted_msg = encode_message(
                        MessageType.NIGHT_VOTE.value, msg.split(" ", 1)[1]
                    )

                # Default case: treat input as a normal chat message and send MSG message
                else:
                    formatted_msg = encode_message(MessageType.MSG.value, msg)
                sock.sendall(formatted_msg.encode())
        except KeyboardInterrupt:
            print("\n[CLIENT] Exiting...")
        finally:
            sock.close()


if __name__ == "__main__":
    main()
