"""Handles incoming client messages and game state transitions for the Werewolf game server."""

import time
from common.protocol import encode_message, decode_message
from server.state import state
from utils.network import broadcast
from server.game import (
    assign_roles,
    change_state,
    tally_and_eliminate,
    handle_seer_choice,
    kill_player,
    broadcast_werewolves
)


def handle_msg(conn, addr, payload):
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
    sender = state.get_username(conn)
    role = state.players.get(conn, {}).get("role")

    if not state.players.get(conn, {}).get("alive", True):
        conn.sendall((encode_message("STATE", "You are dead and cannot vote.") + "\n").encode())
        return

    if state.game_state == "night" and role != "werewolf":
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
    state.add_vote(conn, payload)
    forward = encode_message("VOTE", f"{sender} voted for {payload}")
    broadcast(conn, forward)

    alive_voters = [c for c, p in state.players.items() if p["alive"]]
    if all(c in state.votes for c in alive_voters):
        tally_and_eliminate()


def handle_role(conn, addr, payload):
    sender = state.get_username(conn)
    print(f"[ROLE] Assigned role {payload} to {sender}")
    forward = encode_message("ROLE", f"{sender} is a {payload}") + "\n"
    conn.sendall(forward.encode())


def handle_state(conn, addr, payload):
    print(f"[STATE] New game state: {payload}")
    forward = encode_message("STATE", payload) + "\n"
    broadcast(None, forward)


def handle_client(conn, addr):
    print(f"[+] New connection from {addr}")
    state.add_client(conn)
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message = data.decode().strip()
            print(f"[{addr}] {message}")
            msg_type, payload = decode_message(message)

            if msg_type == "JOIN":
                if not handle_join(conn, addr, payload):
                    return
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
                state.clear_votes()
                change_state("waiting")
            elif msg_type == "NIGHT_MSG":
                sender = state.get_username(conn)
                print(f"[NIGHT_MSG] {sender}: {payload}")
                forward = encode_message("NIGHT_MSG", f"{sender} {payload}")
                broadcast_werewolves(conn, forward)
            elif msg_type == "NIGHT_VOTE":
                handle_night_vote(conn, payload)
            elif msg_type == "SEER_ACTION":
                handle_seer_action(conn, payload)
            elif msg_type == "HUNTER_SHOOT":
                handle_hunter_shoot(conn, payload)

    except ConnectionResetError:
        print(f"[!] Connection lost with {addr}")
    finally:
        conn.close()
        state.remove_client(conn)
        print(f"[-] Disconnected {addr}")


def handle_start(conn):
    MIN_PLAYERS = 5  # Minimum absolu: 1 loup-garou, 1 voyante et 3 villageois
    RECOMMENDED_PLAYERS = 6  # Recommandé: inclut aussi la sorcière
    if state.game_state != "waiting":
        conn.sendall((encode_message("STATE", "Game already started") + "\n").encode())
        return
    elif len(state.clients) < MIN_PLAYERS:
        conn.sendall((encode_message("STATE", f"At least {MIN_PLAYERS} players are required to start the game") + "\n").encode())
        return
    elif len(state.clients) < RECOMMENDED_PLAYERS:
        # On peut démarrer, mais on avertit que c'est mieux avec plus de joueurs
        conn.sendall((encode_message("MSG", f"Note: {RECOMMENDED_PLAYERS}+ players are recommended for a balanced game with all roles") + "\n").encode())
        # On continue le démarrage

    assign_roles()
    change_state("night")


def handle_night_msg(conn, payload):
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
    # Traitement spécial pour les actions de la sorcière
    if payload.startswith("witch_"):
        if not (state.players[conn]["alive"] and state.players[conn]["role"] == "sorcière"):
            return
            
        if payload == "witch_save":
            # La sorcière sauve la victime désignée
            print(f"[WITCH] {state.get_username(conn)} saved the victim")
            # Reset des votes des loups-garous
            for wolf_conn in [c for c, p in state.players.items() if p["role"] == "werewolf"]:
                if wolf_conn in state.votes:
                    state.votes.pop(wolf_conn)
            
            # Continuer le jeu après l'action de la sorcière
            print("[GAME] Witch action completed, processing night results")
            time.sleep(2)
            tally_and_eliminate()
            return
            
        elif payload == "witch_none":
            # La sorcière ne fait rien
            print(f"[WITCH] {state.get_username(conn)} did nothing")
            
            # Continuer le jeu après l'action de la sorcière
            print("[GAME] Witch action completed, processing night results")
            time.sleep(2)
            tally_and_eliminate()
            return
            
        elif payload.startswith("witch_kill:"):
            # La sorcière tue quelqu'un
            target_name = payload.split(":")[1]
            target_conn = state.get_conn_by_username(target_name)
            if target_conn and state.players[target_conn]["alive"]:
                print(f"[WITCH] {state.get_username(conn)} killed {target_name}")
                kill_player(target_conn)
            
            # Continuer le jeu après l'action de la sorcière
            print("[GAME] Witch action completed, processing night results")
            time.sleep(2)
            tally_and_eliminate()
            return
              # Traitement normal pour les loups-garous
    target_conn = state.get_conn_by_username(payload)
    if not target_conn:
        conn.sendall((encode_message("STATE", f"Player {payload} does not exist.") + "\n").encode())
        return
    if not state.players.get(target_conn, {}).get("alive", False):
        conn.sendall((encode_message("STATE", f"{payload} is dead. Choose a living player.") + "\n").encode())
        return
    if not (state.players[conn]["alive"] and state.players[conn]["role"] == "werewolf"):
        return
    if payload == state.get_username(conn):
        conn.sendall((encode_message("STATE", "You cannot vote for yourself.") + "\n").encode())
        return
    
    state.add_vote(conn, payload)

    werewolves = [c for c, p in state.players.items() if p["alive"] and p["role"] == "werewolf"]
    if all(w in state.votes for w in werewolves):
        # Tous les loups-garous ont voté, vérifier s'il y a une sorcière dans la partie
        print("[GAME] All werewolves have voted, checking for witch...")
        
        # Vérifier s'il y a une sorcière vivante dans la partie
        witch_exists = False
        for conn, p in state.players.items():
            if p["role"] == "sorcière" and p["alive"]:
                witch_exists = True
                break
                
        if witch_exists:
            # Il y a une sorcière vivante, déclencher sa phase
            print("[GAME] Living witch found, starting witch phase")
            time.sleep(2)
            from server.game import trigger_witch_phase
            trigger_witch_phase()
        else:
            # Pas de sorcière vivante ou pas de sorcière dans la partie, continuer directement avec l'élimination
            print("[GAME] No living witch found, proceeding directly with night results")
            time.sleep(2)
            tally_and_eliminate()


def handle_seer_action(conn, payload):
    handle_seer_choice(conn, payload)


def handle_hunter_shoot(conn, payload):
    target_conn = state.get_conn_by_username(payload)
    if target_conn and state.players[target_conn]["alive"]:
        kill_player(target_conn)


def handle_join(conn, addr, payload):
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
            
            # Envoyer la liste des joueurs déjà connectés au nouveau client
            existing_players = [state.get_username(c) for c in state.clients if c != conn and state.get_username(c)]
            for player in existing_players:
                join_msg = encode_message("JOIN", player) + "\n"
                conn.sendall(join_msg.encode())
            
            # Diffuser aux autres clients qu'un nouveau joueur a rejoint
            join_broadcast = encode_message("JOIN", payload)
            broadcast(conn, join_broadcast)
            return True
