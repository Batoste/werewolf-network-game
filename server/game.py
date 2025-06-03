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
    
    if new_state == "night":
        time.sleep(1)
        werewolf_night_phase()
    
def tally_and_eliminate():
    """
    Tally votes and eliminate the player with the most votes.
    If there's a tie, the first player in the list is eliminated.
    """
    from collections import Counter
    voted_names = list(state.votes.values())
    target, _ = Counter(voted_names).most_common(1)[0]
    
    # Find and eliminate the target
    for conn, info in state.players.items():
        if info["name"] == target:
            state.players[conn]["alive"] = False
            # Send death message to everyone
            broadcast(None, encode_message("KILL", target) + "\n")
            # Send special message to the victim
            if state.game_state == "night":
                death_msg = encode_message("STATE", "You have been killed by wolves during the night") + "\n"
            else:
                death_msg = encode_message("STATE", "You have been eliminated by the village") + "\n"
            conn.sendall(death_msg.encode())
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
        state.set_game_state("end")
        broadcast(None, encode_message("STATE", "villagers_win") + "\n")
    elif len(werewolves) >= len(villagers):
        state.set_game_state("end")
        broadcast(None, encode_message("STATE", "werewolves_win") + "\n")

def werewolf_night_phase():
    """
    Let werewolves communicate and vote during the night phase.
    """
    werewolves = [conn for conn, p in state.players.items() if p["role"] == "werewolf" and p["alive"]]
    
    if len(werewolves) == 1:
        conn = werewolves[0]
        msg = encode_message("STATE", "Vous êtes le seul loup-garou. Choisissez une victime avec /nvote <nom>") + "\n"
        conn.sendall(msg.encode())
    elif len(werewolves) > 1:
        msg = encode_message("STATE", "Loups-garous, débattez avec /nmsg et votez avec /nvote <nom>") + "\n"
        for conn in werewolves:
            conn.sendall(msg.encode())

def broadcast_werewolves(sender_conn, message):
    """
    Send a message to all living werewolves except the sender.
    """
    for conn, p in state.players.items():
        if p["alive"] and p["role"] == "werewolf" and conn != sender_conn:
            try:
                conn.sendall((message if message.endswith("\n") else message + "\n").encode())
            except:
                pass