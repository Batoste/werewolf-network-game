class GameState:
    def __init__(self):
        # self.HOST = '198.168.100.9'
        self.HOST = '0.0.0.0'
        self.PORT = 3000
        self.clients = []
        self.usernames = {}
        self.game_state = "waiting"
        self.players = {}
        self.votes = {}

    def add_client(self, conn):
        self.clients.append(conn)

    def remove_client(self, conn):
        if conn in self.clients:
            self.clients.remove(conn)
        self.usernames.pop(conn, None)
        self.players.pop(conn, None)
        self.votes.pop(conn, None)

    def set_username(self, conn, username):
        self.usernames[conn] = username

    def get_username(self, conn):
        return self.usernames.get(conn)

    def set_game_state(self, new_state):
        self.game_state = new_state

    def clear_votes(self):
        self.votes.clear()

    def add_vote(self, conn, target):
        self.votes[conn] = target

    def get_all_alive_players(self):
        return [c for c, p in self.players.items() if p["alive"]]

    def set_player_role(self, conn, role):
        if conn in self.usernames:
            self.players[conn] = {
                "name": self.usernames[conn],
                "role": role,
                "alive": True
            }

    def username_exists(self, username):
        """Check if a username is already taken."""
        return username in self.usernames.values()
    
    def get_conn_by_username(self, username):
        for conn, name in self.usernames.items():
            if name == username:
                return conn
        return None

state = GameState()