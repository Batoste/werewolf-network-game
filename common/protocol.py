from enum import Enum

class MessageType(Enum):
    JOIN = "JOIN"
    MSG = "MSG"
    STATE = "STATE"
    ROLE = "ROLE"
    START = "START"
    VOTE = "VOTE"
    KILL = "KILL"
    RESTART = "RESTART"
    NIGHT_VOTE = "NIGHT_VOTE"
    NIGHT_MSG = "NIGHT_MSG"
    WITCH_ACTION = "WITCH_ACTION"
    SEER_ACTION = "SEER_ACTION"
    SEER_RESULT = "SEER_RESULT"
    HUNTER_SHOOT = "HUNTER_SHOOT"
    ROLE_DISTRIBUTION = "ROLE_DISTRIBUTION"

def encode_message(msg_type, payload):
    return f"{msg_type}|{payload}\n"

def decode_message(raw_msg):
    try:
        msg_type, payload = raw_msg.split("|", 1)
        return msg_type, payload
    except ValueError:
        return "", raw_msg

# --- AJOUT POUR LA VOYANTE ---
def trigger_seer_phase(players):
    for conn, info in players.items():
        if info.get("role") == "voyante" and info.get("alive", True):
            try:
                msg = encode_message("SEER_ACTION", "")
                conn.sendall(msg.encode())
            except:
                pass

# --- AJOUT POUR LA RÉPONSE DE LA VOYANTE ---
def handle_seer_choice(players, seer_name, target_name):
    target_info = None
    for name, info in players.items():
        if name == target_name:
            target_info = info
            break
    if target_info:
        result = f"{target_name}:{target_info.get('role', '?')}"
        for name, info in players.items():
            if name == seer_name and info.get("role") == "voyante":
                try:
                    msg = encode_message("SEER_RESULT", result)
                    info["conn"].sendall(msg.encode())
                except:
                    pass

# --- AJOUT POUR LE CHASSEUR ---
def handle_hunter_death(players, hunter_name):
    for name, info in players.items():
        if name == hunter_name and info.get("role") == "chasseur":
            try:
                msg = encode_message("HUNTER_SHOOT", "")
                info["conn"].sendall(msg.encode())
            except:
                pass
