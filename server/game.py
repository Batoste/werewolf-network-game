"""Game logic and state management for the Werewolf network game."""

import random
import time
from collections import Counter
from common.protocol import encode_message, trigger_seer_phase, handle_hunter_death
from server.state import state
from utils.network import broadcast


def assign_roles():
    """
    Assign roles to players in the game.
    Balance roles based on the number of players, following standard werewolf game distributions.
    
    Optimal distribution:
    - 6 players  : 1 werewolf, 1 seer, 1 witch, 3 villagers
    - 8 players  : 2 werewolves, 1 seer, 1 witch, 1 hunter, 3 villagers
    - 10 players : 2 werewolves, 1 seer, 1 witch, 1 hunter, 5 villagers
    - 12 players : 3 werewolves, 1 seer, 1 witch, 1 hunter, 6 villagers
    - 14 players : 4 werewolves, 1 seer, 1 witch, 1 hunter, 7 villagers
    - 16+ players: about 1/4 werewolves, all special roles, remaining villagers
    """
    num_players = len(state.clients)
    roles = []
    
    # Optimize werewolf distribution based on player count
    if num_players <= 6:
        # 1 werewolf for 6 or fewer players
        roles.append("werewolf")
    elif num_players <= 9:
        # 2 werewolves for 7-9 players
        roles.extend(["werewolf", "werewolf"])
    elif num_players <= 12:
        # 3 werewolves for 10-12 players
        roles.extend(["werewolf", "werewolf", "werewolf"])
    elif num_players <= 15:
        # 4 werewolves for 13-15 players
        roles.extend(["werewolf", "werewolf", "werewolf", "werewolf"])
    else:
        # For 16+ players: about 1/4 are werewolves
        wolf_count = max(4, num_players // 4)
        roles.extend(["werewolf"] * wolf_count)
    
    # Add special roles based on player count
    if num_players >= 5:
        roles.append("voyante")  # Include the seer starting at 5 players
    
    if num_players >= 6:
        roles.append("sorcière")  # Add the witch starting at 6 players
    
    if num_players >= 7:
        roles.append("chasseur")  # Add the hunter starting at 7 players
    
    # Fill with villagers
    roles += ["villager"] * max(0, num_players - len(roles))
    
    # Shuffle roles for random distribution
    random.shuffle(roles)
    
    # Distribute roles and notify players
    for conn, role in zip(state.clients, roles):
        state.players[conn] = {
            "name": state.usernames[conn],
            "role": role,
            "alive": True
        }
        msg = encode_message("ROLE", role) + "\n"
        conn.sendall(msg.encode())
        time.sleep(0.1)
      # Log role distribution stats
    role_counts = {}
    for conn in state.players:
        role = state.players[conn]["role"]
        if role not in role_counts:
            role_counts[role] = 0
        role_counts[role] += 1
      # Send role distribution to all players
    distribution_list = [f"{count} {role}" for role, count in role_counts.items()]
    # Format the message for readability
    if "werewolf" in role_counts:
        wolf_count = role_counts["werewolf"]
        wolf_word = "werewolf" if wolf_count == 1 else "werewolves"
        distribution_list = [f"{wolf_count} {wolf_word}"] + [item for item in distribution_list if not item.endswith("werewolf")]

    role_translation = {
        "voyante": ("seer", "seers"),
        "sorcière": ("witch", "witches"),
        "chasseur": ("hunter", "hunters"),
        "villager": ("villager", "villagers"),
    }
    translated = []
    for item in distribution_list:
        count_str, role = item.split(" ", 1)
        count = int(count_str)
        if role in role_translation:
            sing, plural = role_translation[role]
            word = sing if count == 1 else plural
            translated.append(f"{count} {word}")
        else:
            translated.append(item)
    distribution_list = translated
    distribution_msg = ", ".join(distribution_list)
    
    broadcast(None, encode_message("ROLE_DISTRIBUTION", distribution_msg))
    
    print(f"[GAME] Role distribution for {num_players} players: {role_counts}")


def change_state(new_state):
    """
    Change the game state and notify all clients.
    Resets votes and broadcasts the new state.
    """
    state.game_state = new_state
    state.votes.clear()
    broadcast(None, encode_message("STATE", new_state))
    if new_state == "night":
        # Notify normal players to wait during the night
        for conn, p in state.players.items():
            if p["alive"] and p["role"] not in ["voyante", "werewolf", "sorcière", "chasseur"]:
                msg = encode_message("MSG", "Night falls... you fall asleep while others act in the shadows.") + "\n"
                try:
                    conn.sendall(msg.encode())
                except:
                    pass
        # At the start of night, trigger only the seer
        # Other actions occur sequentially after each role finishes
        time.sleep(3)
        
        # 1. Seer (can inspect anyone)
        print("[GAME] Starting night sequence with seer phase")
        
        # Check if a living seer exists
        seer_exists = False
        for conn, p in state.players.items():
            if p["role"] == "voyante" and p["alive"]:
                seer_exists = True
                break
                
        if seer_exists:
            trigger_seer_phase()
        else:
            # If no seer, skip directly to the werewolf phase
            print("[GAME] No living seer, skipping to werewolf phase")
            time.sleep(2)
            werewolf_night_phase()


def trigger_witch_phase():
    for conn, info in state.players.items():
        if info["role"] == "sorcière" and info["alive"]:
            try:
                msg = encode_message("WITCH_ACTION", "") + "\n"
                conn.sendall(msg.encode())
            except:
                pass


def tally_and_eliminate():
    """
    Tally votes and eliminate the player with the most votes.
    """
    if not state.votes:
        return

    voted_names = list(state.votes.values())
    target, _ = Counter(voted_names).most_common(1)[0]

    for conn, info in state.players.items():
        if info["name"] == target and info["alive"]:
            kill_player(conn)
            break

    check_end_game()
    change_state("night" if state.game_state == "day" else "day")


def kill_player(conn):
    """
    Elimine le joueur, envoie les messages de mort, et déclenche le pouvoir du chasseur.
    """
    info = state.players[conn]
    info["alive"] = False
    broadcast(None, encode_message("KILL", info["name"]) + "\n")

    if state.game_state == "night":
        death_msg = encode_message("STATE", "You have been killed by wolves during the night") + "\n"
    else:
        death_msg = encode_message("STATE", "You have been eliminated by the village") + "\n"
    conn.sendall(death_msg.encode())

    if info["role"] == "chasseur":
        handle_hunter_death(conn)


def check_end_game():
    """
    Check if the game is over.
    """
    werewolves = [p for p in state.players.values() if p["role"] == "werewolf" and p["alive"]]
    villagers = [p for p in state.players.values() if p["role"] != "werewolf" and p["alive"]]

    # Details about remaining players for the end message
    werewolf_names = ", ".join([p["name"] for p in state.players.values() if p["role"] == "werewolf"])
    special_roles = ", ".join([f"{p['name']} ({p['role']})" for p in state.players.values() 
                               if p["role"] not in ["werewolf", "villager"]])

    if not werewolves:
        state.set_game_state("end")
        broadcast(None, encode_message("STATE", "villagers_win") + "\n")
        
        # Detailed message listing the werewolves in the game
        win_msg = f"Villagers have won! The werewolves ({werewolf_names}) were eliminated."
        if special_roles:
            win_msg += f"\nSpecial roles: {special_roles}"
        broadcast(None, encode_message("MSG", win_msg) + "\n")
        
    elif len(werewolves) >= len(villagers):
        state.set_game_state("end")
        broadcast(None, encode_message("STATE", "werewolves_win") + "\n")
        
        # Detailed message for the winning werewolves
        win_msg = f"Werewolves ({werewolf_names}) have won! They now outnumber the villagers."
        if special_roles:
            win_msg += f"\nSpecial roles that failed to stop them: {special_roles}"
        broadcast(None, encode_message("MSG", win_msg) + "\n")


def werewolf_night_phase():
    """
    Let werewolves communicate and vote during the night phase.
    """
    werewolves = [conn for conn, p in state.players.items() if p["role"] == "werewolf" and p["alive"]]
    
    # Ensure the living werewolves list is not empty
    if not werewolves:
        print("[GAME] No living werewolves to take action")
        return
    
    print(f"[GAME] Sending werewolf action to {len(werewolves)} werewolves")
    
    if len(werewolves) == 1:
        conn = werewolves[0]
        msg = encode_message("STATE", "You are the only werewolf. Choose a victim with /nvote <name>") + "\n"
        try:
            conn.sendall(msg.encode())
            # Short pause to ensure messages are sent in order
            time.sleep(1)
            # Send a specific message to trigger the popup
            msg_action = encode_message("WEREWOLF_ACTION", "") + "\n"
            conn.sendall(msg_action.encode())
            print(f"[GAME] Sent werewolf action to {state.usernames.get(conn, 'unknown')}")
        except Exception as e:
            print(f"[ERROR] Failed to send werewolf action: {e}")
    elif len(werewolves) > 1:
        msg = encode_message("STATE", "Werewolves, chat with /nmsg and vote with /nvote <name>") + "\n"
        for conn in werewolves:
            try:
                conn.sendall(msg.encode())
                # Short pause to ensure messages are sent in order
                time.sleep(1)
                # Send a specific message to trigger the popup
                msg_action = encode_message("WEREWOLF_ACTION", "") + "\n"
                conn.sendall(msg_action.encode())
                print(f"[GAME] Sent werewolf action to {state.usernames.get(conn, 'unknown')}")
            except Exception as e:
                print(f"[ERROR] Failed to send werewolf action to {state.usernames.get(conn, 'unknown')}: {e}")


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
