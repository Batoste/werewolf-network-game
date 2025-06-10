"""Game logic and state management for the Werewolf network game."""

import random
import time
from collections import Counter
from common.protocol import encode_message
from server.state import state
from utils.network import broadcast


def assign_roles():
    """
    Assign roles to players in the game.
    Balance roles based on the number of players, following standard werewolf game distributions.
    
    Distribution optimale:
    - 6 joueurs  : 1 loup-garou, 1 voyante, 1 sorcière, 3 villageois
    - 8 joueurs  : 2 loups-garous, 1 voyante, 1 sorcière, 1 chasseur, 3 villageois
    - 10 joueurs : 2 loups-garous, 1 voyante, 1 sorcière, 1 chasseur, 5 villageois
    - 12 joueurs : 3 loups-garous, 1 voyante, 1 sorcière, 1 chasseur, 6 villageois
    - 14 joueurs : 4 loups-garous, 1 voyante, 1 sorcière, 1 chasseur, 7 villageois
    - 16+ joueurs: environ 1/4 de loups-garous, tous les rôles spéciaux, reste villageois
    """
    num_players = len(state.clients)
    roles = []
    
    # Optimiser la répartition des loups-garous selon le nombre de joueurs
    if num_players <= 6:
        # 1 loup-garou pour 6 joueurs ou moins
        roles.append("werewolf")
    elif num_players <= 9:
        # 2 loups-garous pour 7-9 joueurs
        roles.extend(["werewolf", "werewolf"])
    elif num_players <= 12:
        # 3 loups-garous pour 10-12 joueurs
        roles.extend(["werewolf", "werewolf", "werewolf"])
    elif num_players <= 15:
        # 4 loups-garous pour 13-15 joueurs
        roles.extend(["werewolf", "werewolf", "werewolf", "werewolf"])
    else:
        # Pour 16+ joueurs: environ 1/4 des joueurs sont des loups-garous
        wolf_count = max(4, num_players // 4)
        roles.extend(["werewolf"] * wolf_count)
    
    # Ajouter les rôles spéciaux selon le nombre de joueurs
    if num_players >= 5:
        roles.append("voyante")  # La voyante est toujours incluse à partir de 5 joueurs
    
    if num_players >= 6:
        roles.append("sorcière")  # La sorcière est ajoutée à partir de 6 joueurs
    
    if num_players >= 7:
        roles.append("chasseur")  # Le chasseur est ajouté à partir de 7 joueurs
    
    # Compléter avec des villageois
    roles += ["villager"] * max(0, num_players - len(roles))
    
    # Mélanger les rôles pour une distribution aléatoire
    random.shuffle(roles)
    
    # Distribuer les rôles et notifier les joueurs
    for conn, role in zip(state.clients, roles):
        state.players[conn] = {
            "name": state.usernames[conn],
            "role": role,
            "alive": True
        }
        msg = encode_message("ROLE", role) + "\n"
        conn.sendall(msg.encode())
        time.sleep(0.1)
      # Logging des statistiques de distribution des rôles
    role_counts = {}
    for conn in state.players:
        role = state.players[conn]["role"]
        if role not in role_counts:
            role_counts[role] = 0
        role_counts[role] += 1
      # Envoyer la distribution des rôles à tous les joueurs
    distribution_list = [f"{count} {role}" for role, count in role_counts.items()]
    # Formater le message pour une meilleure lisibilité
    if "werewolf" in role_counts:
        wolf_count = role_counts["werewolf"]
        wolf_text = f"{wolf_count} {'loup-garou' if wolf_count == 1 else 'loups-garous'}"
        distribution_list = [wolf_text] + [item for item in distribution_list if not item.endswith("werewolf")]
    
    # Traduire "villager" en français
    distribution_list = [item.replace("villager", "villageois") for item in distribution_list]
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
        # Envoyer un message aux joueurs normaux pour qu'ils sachent qu'ils doivent attendre
        for conn, p in state.players.items():
            if p["alive"] and p["role"] not in ["voyante", "werewolf", "sorcière", "chasseur"]:
                msg = encode_message("MSG", "La nuit tombe... Vous vous endormez pendant que d'autres agissent dans l'ombre.") + "\n"
                try:
                    conn.sendall(msg.encode())
                except:
                    pass
        # Au début de la nuit, déclencher uniquement la voyante
        # Les autres actions seront déclenchées en séquence après que chaque rôle ait terminé
        time.sleep(3)
        
        # 1. Voyante (peut examiner n'importe qui)
        print("[GAME] Starting night sequence with seer phase")
        
        # Vérifier s'il y a une voyante vivante
        seer_exists = False
        for conn, p in state.players.items():
            if p["role"] == "voyante" and p["alive"]:
                seer_exists = True
                break
                
        if seer_exists:
            trigger_seer_phase()
        else:
            # S'il n'y a pas de voyante, passer directement à la phase des loups-garous
            print("[GAME] No living seer, skipping to werewolf phase")
            time.sleep(2)
            werewolf_night_phase()
            
        # Les phases suivantes sont déclenchées après la fin de l'action de la voyante
        # dans la fonction handle_seer_choice


def trigger_seer_phase():
    for conn, p in state.players.items():
        if p["role"] == "voyante" and p["alive"]:
            msg = encode_message("SEER_ACTION", "") + "\n"
            conn.sendall(msg.encode())


def handle_seer_choice(conn, target_name):
    for p in state.players.values():
        if p["name"] == target_name:
            result = f"{target_name}:{p['role']}"
            conn.sendall(encode_message("SEER_RESULT", result).encode())
            print(f"[GAME] Seer {state.usernames[conn]} examined {target_name} (role: {p['role']})")
            
            # Maintenant que la voyante a fini son action, déclencher l'action des loups-garous
            time.sleep(2)  # Petit délai pour s'assurer que le client a le temps de traiter la réponse
            print("[GAME] Seer action completed, starting werewolf phase")
            werewolf_night_phase()
            break


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


def handle_hunter_death(conn):
    """
    Permet au chasseur de tirer sur quelqu’un à sa mort.
    """
    conn.sendall(encode_message("HUNTER_SHOOT", "") + "\n")


def check_end_game():
    """
    Vérifie si le jeu est terminé.
    """
    werewolves = [p for p in state.players.values() if p["role"] == "werewolf" and p["alive"]]
    villagers = [p for p in state.players.values() if p["role"] != "werewolf" and p["alive"]]

    # Détails sur les joueurs restants pour le message de fin
    werewolf_names = ", ".join([p["name"] for p in state.players.values() if p["role"] == "werewolf"])
    special_roles = ", ".join([f"{p['name']} ({p['role']})" for p in state.players.values() 
                               if p["role"] not in ["werewolf", "villager"]])

    if not werewolves:
        state.set_game_state("end")
        broadcast(None, encode_message("STATE", "villagers_win") + "\n")
        
        # Message détaillé sur les loups-garous qui étaient dans la partie
        win_msg = f"Les villageois ont gagné! Les loups-garous ({werewolf_names}) ont été éliminés."
        if special_roles:
            win_msg += f"\nRôles spéciaux: {special_roles}"
        broadcast(None, encode_message("MSG", win_msg) + "\n")
        
    elif len(werewolves) >= len(villagers):
        state.set_game_state("end")
        broadcast(None, encode_message("STATE", "werewolves_win") + "\n")
        
        # Message détaillé sur les loups-garous qui ont gagné
        win_msg = f"Les loups-garous ({werewolf_names}) ont gagné! Ils sont désormais majoritaires."
        if special_roles:
            win_msg += f"\nRôles spéciaux qui n'ont pas réussi à les arrêter: {special_roles}"
        broadcast(None, encode_message("MSG", win_msg) + "\n")


def werewolf_night_phase():
    """
    Let werewolves communicate and vote during the night phase.
    """
    werewolves = [conn for conn, p in state.players.items() if p["role"] == "werewolf" and p["alive"]]
    
    # S'assurer que la liste des loups-garous vivants n'est pas vide
    if not werewolves:
        print("[GAME] No living werewolves to take action")
        return
    
    print(f"[GAME] Sending werewolf action to {len(werewolves)} werewolves")
    
    if len(werewolves) == 1:
        conn = werewolves[0]
        msg = encode_message("STATE", "Vous êtes le seul loup-garou. Choisissez une victime avec /nvote <nom>") + "\n"
        try:
            conn.sendall(msg.encode())
            # Pause courte pour s'assurer que les messages sont envoyés dans le bon ordre
            time.sleep(1)
            # Envoyer un message spécifique pour déclencher la popup
            msg_action = encode_message("WEREWOLF_ACTION", "") + "\n"
            conn.sendall(msg_action.encode())
            print(f"[GAME] Sent werewolf action to {state.usernames.get(conn, 'unknown')}")
        except Exception as e:
            print(f"[ERROR] Failed to send werewolf action: {e}")
    elif len(werewolves) > 1:
        msg = encode_message("STATE", "Loups-garous, débattez avec /nmsg et votez avec /nvote <nom>") + "\n"
        for conn in werewolves:
            try:
                conn.sendall(msg.encode())
                # Pause courte pour s'assurer que les messages sont envoyés dans le bon ordre
                time.sleep(1)
                # Envoyer un message spécifique pour déclencher la popup
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
