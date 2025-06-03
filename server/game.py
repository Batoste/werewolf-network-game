import random
import time
from common.protocol import encode_message
from server.state import state
from utils.network import broadcast

def assign_roles():
    """
    Assign roles to players in the game.
    Randomly assign one werewolf and the rest villagers.
    """
    roles = ["werewolf"] + ["villager"] * (len(state.clients) - 1)
    random.shuffle(roles)
    for conn, role in zip(state.clients, roles):
        state.players[conn] = {
            "name": state.usernames[conn],
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
    state.game_state = new_state
    state.votes.clear()
    broadcast(None, encode_message("STATE", new_state))
    
def tally_and_eliminate():
    """
    Tally votes and eliminate the player with the most votes.
    If there's a tie, the first player in the list is eliminated.
    """
    from collections import Counter
    voted_names = list(state.votes.values())
    target, _ = Counter(voted_names).most_common(1)[0]
    for conn, info in state.players.items():
        if info["name"] == target:
            state.players[conn]["alive"] = False
            broadcast(None, encode_message("KILL", target) + "\n")
            break
    check_end_game()
    change_state("night" if state.game_state == "day" else "day")
    
def check_end_game():
    """
    Check if the game has ended based on the current state of state.players.
    If all werewolves are dead, villagers win; if werewolves outnumber villagers, they win.
    """
    werewolves = [p for p in state.players.values() if p["role"] == "werewolf" and p["alive"]]
    villagers = [p for p in state.players.values() if p["role"] != "werewolf" and p["alive"]]
    if not werewolves:
        broadcast(None, encode_message("STATE", "villagers_win") + "\n")
    elif len(werewolves) >= len(villagers):
        broadcast(None, encode_message("STATE", "werewolves_win") + "\n")