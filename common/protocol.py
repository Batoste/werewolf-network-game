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


