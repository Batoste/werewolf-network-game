"""This module provides utility functions for broadcasting messages to clients."""

from server.state import state


def broadcast(sender_conn, message):
    """
    Send a message to all clients except the sender.
    """
    with state.lock:
        recipients = [c for c in state.clients if c != sender_conn]

    for client in recipients:
        try:
            formatted_message = (
                message if message.endswith("\n") else message + "\n"
            )
            client.sendall(formatted_message.encode())
        except Exception:
            pass
