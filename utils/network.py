from server.state import state

def broadcast(sender_conn, message):
    """
    Send a message to all clients except the sender.
    """
    for client in state.clients: # Iterate over all connected clients
        if client != sender_conn: # Don't send to the sender
            try:
                client.sendall((message if message.endswith("\n") else message + "\n").encode())
            except:
                # Ignore errors sending to disconnected clients
                pass