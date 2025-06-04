"""Handles incoming client messages and game state transitions for the Werewolf game server."""

from common.protocol import encode_message, decode_message
from server.state import state
from utils.network import broadcast
from server.game import assign_roles, change_state, tally_and_eliminate


def handle_msg(conn, addr, payload):
    """
    Handle a MSG message from a client.
    Broadcast the message to all other clients.
    """
    if state.game_state != "waiting" and not state.players.get(conn, {}).get("alive", True):
        conn.sendall((encode_message("STATE", "You are dead and cannot talk.") + "\n").encode())
        return

    sender = state.get_username(conn)
    role = state.players.get(conn, {}).get("role")

    if state.game_state == "night" and role != "werewolf":
        conn.sendall((encode_message("STATE", "You can't talk at night") + "\n").encode())
        return

    print(f"[{sender}] {payload}")
    forward = encode_message("MSG", f"[{sender}] {payload}")
    broadcast(conn, forward)


def handle_vote(conn, addr, payload):
    """
    Handle a VOTE message from a client.
    Store the vote, broadcast it, and check if vote phase is complete.
    """
    sender = state.get_username(conn)
    role = state.players.get(conn, {}).get("role")

    # Prevent dead players from voting
    if not state.players.get(conn, {}).get("alive", True):
        conn.sendall((encode_message("STATE", "You are dead and cannot vote.") + "\n").encode())
        return

    if state.game_state == "night":
        role = state.players.get(conn, {}).get("role")
        if role != "werewolf":
            conn.sendall((encode_message("STATE", "Only werewolves can vote at night") + "\n").encode())
            return

    target_conn = state.get_conn_by_username(payload)
    if not target_conn:
        conn.sendall((encode_message("STATE", f"Player {payload} does not exist.") + "\n").encode())
        return
    if not state.players.get(target_conn, {}).get("alive", False):
        conn.sendall((encode_message("STATE", f"{payload} is dead. Choose a living player.") + "\n").encode())
        return

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
                # Handle new client joining with username validation
                if not handle_join(conn, addr, payload):
                    return  # abort if join fails
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
            elif msg_type == "RESTART":
                # Handle game restart logic
                print(f"[RESTART] Game restarted by {state.get_username(conn)}")
                state.clear_votes()
                change_state("waiting")
            elif msg_type == "NIGHT_MSG":
                sender = state.get_username(conn)
                print(f"[NIGHT_MSG] {sender}: {payload}")
                forward = encode_message("NIGHT_MSG", f"{sender} {payload}")
                from server.game import broadcast_werewolves
                broadcast_werewolves(conn, forward)
            elif msg_type == "NIGHT_VOTE":
                handle_night_vote(conn, payload)

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
    # Minimum number of players required to start the game
    MIN_PLAYERS = 3

    if state.game_state != "waiting":
        conn.sendall((encode_message("STATE", "Game already started") + "\n").encode())
        return
    elif len(state.clients) < MIN_PLAYERS:
        conn.sendall((encode_message("STATE", f"Need at least {MIN_PLAYERS} players") + "\n").encode())
        return

    assign_roles()
    change_state("night")


def handle_night_msg(conn, payload):
    """
    Relay NIGHT_MSG only to alive werewolves.
    """
    if state.game_state != "waiting" and not state.players.get(conn, {}).get("alive", True):
        conn.sendall((encode_message("STATE", "You are dead and cannot talk.") + "\n").encode())
        return

    sender = state.get_username(conn)
    if not (state.players[conn]["alive"] and state.players[conn]["role"] == "werewolf"):
        return
    forward = encode_message("NIGHT_MSG", f"[{sender}] {payload}")
    for c, p in state.players.items():
        if p["alive"] and p["role"] == "werewolf":
            c.sendall((forward + "\n").encode())


def handle_night_vote(conn, payload):
    """
    Handle NIGHT_VOTE from werewolves and eliminate target when all have voted.
    """
    target_conn = state.get_conn_by_username(payload)
    if not target_conn:
        conn.sendall((encode_message("STATE", f"Player {payload} does not exist.") + "\n").encode())
        return
    if not state.players.get(target_conn, {}).get("alive", False):
        conn.sendall((encode_message("STATE", f"{payload} is dead. Choose a living player.") + "\n").encode())
        return

    if not (state.players[conn]["alive"] and state.players[conn]["role"] == "werewolf"):
        return

    # Prevent self-voting
    if payload == state.get_username(conn):
        conn.sendall((encode_message("STATE", "You cannot vote for yourself.") + "\n").encode())
        return

    state.add_vote(conn, payload)

    # If all alive werewolves have voted, tally votes and eliminate target
    werewolves = [c for c, p in state.players.items() if p["alive"] and p["role"] == "werewolf"]
    if all(w in state.votes for w in werewolves):
        from server.game import tally_and_eliminate
        tally_and_eliminate()


def handle_restart():
    """
    Reset the game state but keep clients connected.
    """
    print("[SERVER] Restarting game state...")
    state.players.clear()
    state.votes.clear()
    state.game_state = "waiting"
    broadcast(None, encode_message("STATE", "Game has been restarted") + "\n")


def handle_join(conn, addr, payload):
    """
    Loop until the client provides a valid and unique username.
    """
    while True:
        if state.username_exists(payload):
            conn.sendall((encode_message("STATE", "This username is already taken. Enter a new one:") + "\n").encode())
            try:
                data = conn.recv(1024)
                if not data:
                    return False
                msg_type, payload = decode_message(data.decode().strip())
                if msg_type != "JOIN":
                    continue
            except:
                return False
        else:
            state.set_username(conn, payload)
            print(f"[{addr}] joined as {payload}")
            return True