"""This module provides utility functions for broadcasting messages to clients."""

from server.state import state

def broadcast(sender_conn, message):
    """
    Send a message to all clients except the sender.
    """
    # Iterate over all connected clients
    for client in state.clients:
        # Don't send to the sender
        if client != sender_conn:
            try:
                # Ensure the message ends with a newline before sending
                formatted_message = message if message.endswith("\n") else message + "\n"
                client.sendall(formatted_message.encode())
            except:
                # Ignore errors sending to disconnected clients
                pass