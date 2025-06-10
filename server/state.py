"""This module defines the GameState class, which manages the state of the game server,
including connected clients, usernames, player roles, votes, and the overall game status."""

class GameState:
    def __init__(self):
        # self.HOST = '198.168.100.9'
        self.HOST = '0.0.0.0'
        self.PORT = 3001
        self.clients = []
        self.usernames = {}
        self.game_state = "waiting"
        self.players = {}
        self.votes = {}

    # Connection management methods

    def add_client(self, conn):
        """Add a new client connection to the list of active clients."""
        self.clients.append(conn)

    def remove_client(self, conn):
        """Remove a client connection and clean up associated user and player data."""
        if conn in self.clients:
            self.clients.remove(conn)
        self.usernames.pop(conn, None)
        self.players.pop(conn, None)
        self.votes.pop(conn, None)

    # User management methods

    def set_username(self, conn, username):
        """Associate a username with a client connection."""
        self.usernames[conn] = username

    def get_username(self, conn):
        """Retrieve the username associated with a client connection."""
        return self.usernames.get(conn)

    def username_exists(self, username):
        """Check if a username is already taken."""
        return username in self.usernames.values()
    
    def get_conn_by_username(self, username):
        """Get the client connection object associated with a username."""
        for conn, name in self.usernames.items():
            if name == username:
                return conn
        return None

    # Player role and status management

    def set_player_role(self, conn, role):
        """Assign a role to a player and mark them as alive."""
        if conn in self.usernames:
            self.players[conn] = {
                "name": self.usernames[conn],
                "role": role,
                "alive": True
            }

    def get_all_alive_players(self):
        """Return a list of client connections for all players currently alive."""
        return [c for c, p in self.players.items() if p["alive"]]

    # Game state handling

    def set_game_state(self, new_state):
        """Update the overall game state."""
        self.game_state = new_state

    # Voting management

    def clear_votes(self):
        """Clear all recorded votes."""
        self.votes.clear()

    def add_vote(self, conn, target):
        """Record a vote from a player towards a target."""
        self.votes[conn] = target

state = GameState()