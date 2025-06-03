from common.protocol import encode_message, decode_message
from server.state import state
from utils.network import broadcast
from server.game import assign_roles, change_state, tally_and_eliminate

def handle_join(conn, addr, payload):
    """
    Handle a JOIN message from a client.
    Register the username for the connection and log the event.
    """
    state.set_username(conn, payload)
    print(f"[{addr}] joined as {payload}")

def handle_msg(conn, addr, payload):
    """
    Handle a MSG message from a client.
    Broadcast the message to all other clients.
    """
    sender = state.get_username(conn)
    print(f"[{sender}] {payload}")
    forward = encode_message("MSG", f"[{sender}] {payload}")
    broadcast(conn, forward)

def handle_vote(conn, addr, payload):
    """
    Handle a VOTE message from a client.
    Store the vote, broadcast it, and check if vote phase is complete.
    """
    sender = state.get_username(conn)
    print(f"[VOTE] {sender} voted for {payload}")

    state.add_vote(conn, payload)  # Store the vote
    forward = encode_message("VOTE", f"{sender} voted for {payload}")
    broadcast(conn, forward)

    # Check if all alive players have voted
    alive_voters = [c for c, p in state.players.items() if p["alive"]]
    if all(c in state.votes for c in alive_voters):
        tally_and_eliminate()

def handle_role(conn, addr, payload):
    """
    Handle a ROLE message: assign and notify the client of their role.
    """
    sender = state.get_username(conn)
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
    state.add_client(conn)
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
        state.remove_client(conn)
        print(f"[-] Disconnected {addr}")

# Added handle_start function
def handle_start(conn):
    """
    Start the game if enough players are connected.
    """
    MIN_PLAYERS = 3
    if len(state.clients) < MIN_PLAYERS:
        conn.sendall((encode_message("STATE", f"Need at least {MIN_PLAYERS} players") + "\n").encode())
        return

    assign_roles()
    change_state("night")