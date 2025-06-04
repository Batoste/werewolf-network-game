"""This module handles message formatting and parsing for the network protocol."""

from enum import Enum

DELIMITER = '|'

# Enum representing the different types of messages in the protocol
class MessageType(Enum):
    JOIN = "JOIN"
    MSG = "MSG"
    VOTE = "VOTE"
    ROLE = "ROLE"
    STATE = "STATE"
    KILL = "KILL"
    START = "START"
    RESTART = "RESTART"
    NIGHT_MSG = "NIGHT_MSG"
    NIGHT_VOTE = "NIGHT_VOTE"

# Encode a message type and payload into a formatted string for sending over the network
def encode_message(msg_type: str, payload: str) -> str:
    """
    Format a message string to send over the network
    Example: encode_message("MSG", "hello") => "MSG|hello"
    """
    return f"{msg_type.strip().upper()}{DELIMITER}{payload.strip()}"

# Decode a received message string into its type and payload components
def decode_message(message: str) -> tuple[str, str]:
    """
    Parse a received message string into type and payload
    Example: decode_message("ROLE|werewolf") => ("ROLE", "werewolf")
    """
    if DELIMITER not in message:
        return "INVALID", message
    msg_type, payload = message.split(DELIMITER, 1)
    return msg_type.strip().upper(), payload.strip()