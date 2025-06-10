"""Thread-safe state management for the Werewolf server."""

from __future__ import annotations

import threading
from typing import List, Dict, Any

from config import HOST, PORT


class GameState:
    """Shared game state protected by a re-entrant lock."""

    def __init__(self) -> None:
        self.HOST = HOST
        self.PORT = PORT
        self.lock = threading.RLock()
        self.clients: List[Any] = []
        self.usernames: Dict[Any, str] = {}
        self.game_state: str = "waiting"
        self.players: Dict[Any, Dict[str, Any]] = {}
        self.votes: Dict[Any, str] = {}

    # Connection management methods

    def add_client(self, conn):
        """Add a new client connection to the list of active clients."""
        with self.lock:
            self.clients.append(conn)

    def remove_client(self, conn):
        """Remove a client connection and clean up associated user and player data."""
        with self.lock:
            if conn in self.clients:
                self.clients.remove(conn)
            self.usernames.pop(conn, None)
            self.players.pop(conn, None)
            self.votes.pop(conn, None)

    # User management methods

    def set_username(self, conn, username):
        """Associate a username with a client connection."""
        with self.lock:
            self.usernames[conn] = username

    def get_username(self, conn):
        """Retrieve the username associated with a client connection."""
        with self.lock:
            return self.usernames.get(conn)

    def username_exists(self, username):
        """Check if a username is already taken."""
        with self.lock:
            return username in self.usernames.values()

    def get_conn_by_username(self, username):
        """Get the client connection object associated with a username."""
        with self.lock:
            for conn, name in self.usernames.items():
                if name == username:
                    return conn
            return None

    # Player role and status management

    def set_player_role(self, conn, role):
        """Assign a role to a player and mark them as alive."""
        with self.lock:
            if conn in self.usernames:
                self.players[conn] = {
                    "name": self.usernames[conn],
                    "role": role,
                    "alive": True,
                }

    def get_all_alive_players(self):
        """Return a list of client connections for all players currently alive."""
        with self.lock:
            return [c for c, p in self.players.items() if p["alive"]]

    # Game state handling

    def set_game_state(self, new_state):
        """Update the overall game state."""
        with self.lock:
            self.game_state = new_state

    # Voting management

    def clear_votes(self):
        """Clear all recorded votes."""
        with self.lock:
            self.votes.clear()

    def add_vote(self, conn, target):
        """Record a vote from a player towards a target."""
        with self.lock:
            self.votes[conn] = target


state = GameState()
