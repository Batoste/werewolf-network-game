# Standard library imports
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Standard library imports
import socket
import threading
import random
import time
# Third-party or local imports
from common.protocol import decode_message, encode_message
# Global configuration and state
HOST = '127.0.0.1'
PORT = 3001

clients = []  # List of connected client sockets
usernames = {}  # Maps client sockets to usernames

game_state = "waiting"  # "day", "night", "end"
players = {}  # conn -> {"name": "Noe", "role": "villager", "alive": True}
votes = {}  # conn -> voted_name

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
    Store the vote, broadcast it, and check if vote phase is complete.
    """
    sender = usernames.get(conn, str(addr))
    print(f"[VOTE] {sender} voted for {payload}")

    votes[conn] = payload  # Store the vote
    forward = encode_message("VOTE", f"{sender} voted for {payload}")
    broadcast(conn, forward)

    # Check if all alive players have voted
    alive_voters = [c for c, p in players.items() if p["alive"]]
    if all(c in votes for c in alive_voters):
        tally_and_eliminate()

def handle_role(conn, addr, payload):
    """
    Handle a ROLE message: assign and notify the client of their role.
    """
    sender = usernames.get(conn, str(addr))
    print(f"[ROLE] Assigned role {payload} to {sender}")
    forward = encode_message("ROLE", f"{sender} is a {payload}") + "\n"
    # Send the role assignment only to the requesting client
    conn.sendall(forward.encode())

def handle_state(conn, addr, payload):
    """
    Handle a STATE message: broadcast new game state to all clients.
    """
    print(f"[STATE] New game state: {payload}")
    forward = encode_message("STATE", payload) + "\n"
    broadcast(None, forward)

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
            elif msg_type == "START":
                handle_start(conn)

    except ConnectionResetError:
        # Handle abrupt client disconnects
        print(f"[!] Connection lost with {addr}")
    finally:
        # Clean up: remove client from lists and close connection
        conn.close()
        if conn in clients:
            clients.remove(conn)
        print(f"[-] Disconnected {addr}")

# Added handle_start function
def handle_start(conn):
    """
    Start the game if enough players are connected.
    """
    MIN_PLAYERS = 3
    if len(clients) < MIN_PLAYERS:
        conn.sendall((encode_message("STATE", f"Need at least {MIN_PLAYERS} players") + "\n").encode())
        return

    assign_roles()
    change_state("night")

def broadcast(sender_conn, message):
    """
    Send a message to all clients except the sender.
    """
    for client in clients: # Iterate over all connected clients
        if client != sender_conn: # Don't send to the sender
            try:
                client.sendall((message if message.endswith("\n") else message + "\n").encode())
            except:
                # Ignore errors sending to disconnected clients
                pass
            
def assign_roles():
    """
    Assign roles to players in the game.
    Randomly assign one werewolf and the rest villagers.
    """
    roles = ["werewolf"] + ["villager"] * (len(clients) - 1)
    random.shuffle(roles)
    for conn, role in zip(clients, roles):
        players[conn] = {
            "name": usernames[conn],
            "role": role,
            "alive": True
        }
        msg = encode_message("ROLE", role) + "\n"
        conn.sendall(msg.encode())
        time.sleep(0.1)  # Small delay to avoid overwhelming clients
        
def change_state(new_state):
    """
    Change the game state and notify all clients.
    Resets votes and broadcasts the new state.
    """
    global game_state, votes
    game_state = new_state
    votes = {}
    broadcast(None, encode_message("STATE", new_state))
    
def tally_and_eliminate():
    """
    Tally votes and eliminate the player with the most votes.
    If there's a tie, the first player in the list is eliminated.
    """
    from collections import Counter
    voted_names = list(votes.values())
    target, _ = Counter(voted_names).most_common(1)[0]
    for conn, info in players.items():
        if info["name"] == target:
            players[conn]["alive"] = False
            broadcast(None, encode_message("KILL", target) + "\n")
            break
    check_end_game()
    change_state("night" if game_state == "day" else "day")
    
def check_end_game():
    """
    Check if the game has ended based on the current state of players.
    If all werewolves are dead, villagers win; if werewolves outnumber villagers, they win.
    """
    werewolves = [p for p in players.values() if p["role"] == "werewolf" and p["alive"]]
    villagers = [p for p in players.values() if p["role"] != "werewolf" and p["alive"]]
    if not werewolves:
        broadcast(None, encode_message("STATE", "villagers_win") + "\n")
    elif len(werewolves) >= len(villagers):
        broadcast(None, encode_message("STATE", "werewolves_win") + "\n")

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