import sys
import os
import socket
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.protocol import encode_message, decode_message, MessageType
from server.state import state

class NetworkWorker(QObject):
    message_received = pyqtSignal(str, str)
    connection_lost = pyqtSignal()
    connected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.sock = None
        self.running = False
        self.buffer = ""

    def connect_to_server(self, username):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(("localhost", state.PORT))
            join_msg = encode_message(MessageType.JOIN.value, username)
            self.sock.sendall(join_msg.encode())
            self.running = True
            self.connected.emit()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def listen_for_messages(self):
        while self.running and self.sock:
            try:
                data = self.sock.recv(1024)
                if not data:
                    break
                self.buffer += data.decode()
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line.strip():
                        msg_type, payload = decode_message(line.strip())
                        self.message_received.emit(msg_type, payload)
            except Exception as e:
                print(f"Receive error: {e}")
                break
        self.connection_lost.emit()

    def send_message(self, msg_type, payload):
        if self.sock and self.running:
            try:
                formatted_msg = encode_message(msg_type, payload)
                self.sock.sendall(formatted_msg.encode())
                
                # Record certain commands in the history
                if msg_type in [MessageType.VOTE.value, MessageType.NIGHT_VOTE.value, MessageType.START.value, MessageType.RESTART.value]:
                    cmd = f"/{msg_type.lower()}"
                    if payload:
                        cmd += f" {payload}"
                    self.message_received.emit("COMMANDE", f"Commande envoyée: {cmd}")
            except Exception as e:
                print(f"Send error: {e}")

    def disconnect(self):
        self.running = False
        if self.sock:
            self.sock.close()

class WerewolfClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.network_worker = None
        self.network_thread = None
        self.username = ""
        self.player_role = ""
        self.game_state = ""
        self.players_list = []
        self.init_ui()
        self.setup_network()

    def init_ui(self):
        self.setWindowTitle("🐺 Werewolf Game Client")
        self.setGeometry(100, 100, 1400, 900)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.create_connection_panel(main_layout)
        
        # Main splitter allowing the user to adjust panel sizes
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel for game information and player list
        left_widget = QWidget()
        left_widget.setMinimumWidth(250)
        left_layout = QVBoxLayout(left_widget)
        self.create_game_info_panel(left_layout)
        main_splitter.addWidget(left_widget)
        
        # Center panel for chat
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.create_chat_panel(center_layout)
        main_splitter.addWidget(center_widget)
        
        # Extended command area at the bottom
        self.create_command_panel(main_layout)
        
        # Set relative panel sizes
        main_splitter.setSizes([300, 800])
        
        self.set_game_controls_enabled(False)

    def setup_network(self):
        self.network_thread = QThread()
        self.network_worker = NetworkWorker()
        self.network_worker.moveToThread(self.network_thread)
        self.network_worker.message_received.connect(self.handle_server_message)
        self.network_worker.connection_lost.connect(self.handle_connection_lost)
        self.network_worker.connected.connect(self.handle_connected)
        self.network_thread.started.connect(self.network_worker.listen_for_messages)

    def connect_to_server(self):
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Error", "Please enter a username!")
            return
        self.username = username
        if self.network_worker.connect_to_server(username):
            self.network_thread.start()
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setEnabled(False)
        else:
            QMessageBox.critical(self, "Error", "Unable to connect to server!")

    def handle_connected(self):
        self.status_label.setText("Connected")
        self.status_label.setStyleSheet("color: #2ed573;")
        self.connect_btn.setText("Connected")
        self.set_game_controls_enabled(True)
        self.add_chat_message("SYSTEM", "Connected to server successfully!", "#2ed573")
        
        # Add the local player to the list
        if self.username and self.username not in [self.players_list_widget.item(i).text() for i in range(self.players_list_widget.count())]:
            self.players_list_widget.addItem(self.username)

    def handle_connection_lost(self):
        self.status_label.setText("Connection lost")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(True)
        self.set_game_controls_enabled(False)
        self.add_chat_message("SYSTEM", "Lost connection to the server!", "#ff6b6b")

    def handle_server_message(self, msg_type, payload):
        color_map = {
            "MSG": "#54a0ff",
            "VOTE": "#ffa502",
            "ROLE": "#ff6348",
            "STATE": "#2ed573",
            "JOIN": "#3742fa",
            "START": "#2ed573",
            "KILL": "#ff3838",
            "NIGHT_MSG": "#ff6b9d",
            "SEER_RESULT": "#9c88ff",
            "WITCH_ACTION": "#ff6348",
            "SEER_ACTION": "#9c88ff",
            "WEREWOLF_ACTION": "#ff6b9d",
            "HUNTER_SHOOT": "#ff9f43",
            "ROLE_DISTRIBUTION": "#3742fa"
        }
        color = color_map.get(msg_type, "#ffffff")

        # Ajouter le message au journal dans tous les cas
        self.add_to_log(msg_type, payload, color)

        if msg_type == "ROLE":
            self.player_role = payload
            self.role_label.setText(payload)
            self.add_chat_message("ROLE", f"You are a {payload}!", color)
            
            # Mise à jour de la description du rôle
            role_descriptions = {
                "villager": "You are a simple villager. Your goal is to find the werewolves and eliminate them during village votes.",
                "werewolf": "You are a werewolf! Each night you may vote to devour a villager. During the day, hide your identity.",
                "voyante": "You are the seer. Each night you can discover the true identity of a player of your choice.",
                "sorcière": "You are the witch. You have two potions: one to save a victim, the other to eliminate a player.",
                "chasseur": "You are the hunter. If eliminated, you can immediately shoot another player who will also die."
            }
            self.role_desc_label.setText(role_descriptions.get(payload, "Unknown role"))

        elif msg_type == "STATE":
            self.game_state = payload
            
            # Traitement spécial pour certains états
            if payload == "villagers_win":
                self.state_label.setText("Villagers Victory")
                self.add_chat_message("VICTORY", "🎉 Villagers have won!", "#2ed573")
                QMessageBox.information(self, "Game Over", "Villagers have won! The werewolves were eliminated.")
                
            elif payload == "werewolves_win":
                self.state_label.setText("Werewolves Victory")
                self.add_chat_message("VICTORY", "🐺 Werewolves have won!", "#ff3838")
                QMessageBox.information(self, "Game Over", "Werewolves have won! They devoured all the villagers.")
                
            elif payload == "day":
                self.state_label.setText("Day")
                self.add_chat_message("STATE", "☀️ Day breaks! Discuss and vote to eliminate a suspect.", color)
                # Update the interface for day (optional)
                # self.setStyleSheet("background-color: #87CEEB;") 
                
            elif payload == "night":
                self.state_label.setText("Night")
                self.add_chat_message("STATE", "🌙 Night falls... Special roles act in the shadows.", color)
                # Update the interface for night (optional)
                # self.setStyleSheet("background-color: #2C3E50;")
                
            else:
                self.state_label.setText(payload)
                self.add_chat_message("STATE", payload, color)
                
            # Update controls only
            # Popups are triggered by specific server messages
            self.update_buttons_visibility()

        elif msg_type == "WITCH_ACTION":
            self.show_witch_dialog()
            
        elif msg_type == "SEER_ACTION":
            self.show_seer_dialog()
            
        elif msg_type == "WEREWOLF_ACTION":
            self.show_night_vote_dialog()

        elif msg_type == "SEER_RESULT":
            # Format: player_name:role
            try:
                name, role = payload.split(":")
                self.add_chat_message("SEER", f"💫 You discovered that {name} is a {role}!", "#9c88ff")
                # Show a more visible message
                QMessageBox.information(self, "Seer's Vision", f"You discovered that {name} is a {role}!")
            except Exception as e:
                print(f"Erreur traitement SEER_RESULT: {e}, payload: {payload}")
                self.add_chat_message("VOYANTE", f"Result: {payload}", "#9c88ff")

        elif msg_type == "HUNTER_SHOOT":
            self.show_hunter_dialog()
            
        elif msg_type == "JOIN":
            # Ajouter le joueur à la liste
            if payload not in [self.players_list_widget.item(i).text() for i in range(self.players_list_widget.count())]:
                self.players_list_widget.addItem(payload)
                self.add_chat_message("PLAYER", f"👋 {payload} joined the game!", "#3742fa")
                
        elif msg_type == "ROLE_DISTRIBUTION":
            # Afficher la répartition des rôles
            self.add_chat_message("INFO", f"📊 Role distribution for this game: {payload}", "#3742fa")
            # Show a popup highlighting this information
            QMessageBox.information(self, "Role distribution",
                                    f"Here is the role distribution for this game:\n\n{payload}")
                
        elif msg_type == "KILL":
            # Mark the player as dead in the list
            self.add_chat_message("DEATH", f"☠️ {payload} was eliminated!", "#ff3838")
            
            # Update the player's status in the list (italic or strikethrough)
            for i in range(self.players_list_widget.count()):
                if self.players_list_widget.item(i).text() == payload or self.players_list_widget.item(i).text().startswith(payload + " "):
                    item = self.players_list_widget.item(i)
                    # Add a clear indicator to the text
                    current_text = item.text()
                    if " (mort)" not in current_text:
                        item.setText(f"{payload} (mort)")
                    
                    # Also apply a visual style
                    font = item.font()
                    font.setStrikeOut(True)
                    font.setItalic(True)
                    item.setFont(font)
                    item.setForeground(QColor("#ff3838"))
                    break
                    
            # Check if it is us who died
            if payload == self.username:
                if self.player_role == "chasseur":
                    QMessageBox.information(self, "You are dead",
                                          "You have been eliminated! As the hunter you may still shoot someone.")
                else:
                    QMessageBox.information(self, "You are dead",
                                          "You have been eliminated! You can no longer vote or speak but you may continue to observe the game.")
                
        elif msg_type == "MSG":
            # Handle chat messages
            self.add_chat_message("MSG", payload, color)
            
        elif msg_type == "NIGHT_MSG":
            # Werewolf messages during the night
            if self.player_role == "werewolf":
                self.add_chat_message("LOUPS", f"🐺 {payload}", "#ff6b9d")
            
        else:
            self.add_chat_message(msg_type, payload, color)

    def update_buttons_visibility(self):
        is_alive = True  # Could be improved later
        self.vote_btn.setVisible(self.game_state == "day" and is_alive)
        self.night_vote_btn.setVisible(self.game_state == "night" and self.player_role == "werewolf" and is_alive)

    def check_auto_popups(self):
        """Automatically display appropriate popups based on game state and role"""
        # Popups are now managed directly by server signals
        # and are only shown when specific signals are received
        # SEER_ACTION, WITCH_ACTION, HUNTER_SHOOT, etc.
        pass

    def create_connection_panel(self, parent_layout):
        conn_frame = QFrame()
        conn_layout = QHBoxLayout(conn_frame)
        conn_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your name...")
        conn_layout.addWidget(self.username_input)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_to_server)
        conn_layout.addWidget(self.connect_btn)
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        conn_layout.addWidget(self.status_label)
        parent_layout.addWidget(conn_frame)

    def create_game_info_panel(self, parent_layout):
        # Informations du jeu - cadre avec un titre stylisé
        info_group = QGroupBox("📋 Informations du jeu")
        info_layout = QVBoxLayout(info_group)
        
        # Rôle et état du jeu dans un layout en grille pour plus de clarté
        status_layout = QGridLayout()
        status_layout.addWidget(QLabel("Rôle:"), 0, 0)
        self.role_label = QLabel("Inconnu")
        self.role_label.setStyleSheet("font-weight: bold; color: #ff9f43; font-size: 14px;")
        status_layout.addWidget(self.role_label, 0, 1)
        
        status_layout.addWidget(QLabel("État:"), 1, 0)
        self.state_label = QLabel("En attente")
        self.state_label.setStyleSheet("font-weight: bold; color: #3742fa; font-size: 14px;")
        status_layout.addWidget(self.state_label, 1, 1)
        info_layout.addLayout(status_layout)
        
        # Description du rôle avec plus de détails selon le rôle
        role_desc_frame = QFrame()
        role_desc_frame.setFrameShape(QFrame.StyledPanel)
        role_desc_frame.setStyleSheet("background-color: #2f3542; border-radius: 5px;")
        role_desc_layout = QVBoxLayout(role_desc_frame)
        
        role_desc_title = QLabel("Description du rôle:")
        role_desc_title.setStyleSheet("color: #ffa502; font-weight: bold;")
        role_desc_layout.addWidget(role_desc_title)
        
        self.role_desc_label = QLabel("-")
        self.role_desc_label.setWordWrap(True)
        self.role_desc_label.setStyleSheet("font-style: italic; color: #f1f2f6;")
        role_desc_layout.addWidget(self.role_desc_label)
        info_layout.addWidget(role_desc_frame)
        
        # Actions de jeu - boutons de contrôle principal
        action_box = QGroupBox("Actions de jeu")
        action_layout = QVBoxLayout(action_box)
        
        self.start_btn = QPushButton("🎮 Démarrer le jeu")
        self.start_btn.clicked.connect(self.start_game)
        self.start_btn.setStyleSheet("background-color: #2ed573; font-weight: bold;")
        
        self.restart_btn = QPushButton("🔄 Redémarrer le jeu")
        self.restart_btn.clicked.connect(self.restart_game)
        self.restart_btn.setStyleSheet("background-color: #ff7f50; font-weight: bold;")
        
        # Add the buttons to the layout
        action_layout.addWidget(self.start_btn)
        action_layout.addWidget(self.restart_btn)
        info_layout.addWidget(action_box)

        # Liste des joueurs interactive
        player_box = QGroupBox("👥 Joueurs connectés")
        player_layout = QVBoxLayout(player_box)
        
        # Liste avec sélection et menu contextuel
        self.players_list_widget = QListWidget()
        self.players_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.players_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.players_list_widget.customContextMenuRequested.connect(self.show_player_context_menu)
        self.players_list_widget.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
        
        # Instructions pour la liste des joueurs
        player_info_label = QLabel("Cliquez-droit sur un joueur pour agir")
        player_info_label.setStyleSheet("font-style: italic; color: #a4b0be; font-size: 11px;")
        
        # Add the widgets to the layout
        player_layout.addWidget(self.players_list_widget)
        player_layout.addWidget(player_info_label)
        
        # Add the player group to the main layout
        info_layout.addWidget(player_box)
        
        # Add final element to the parent layout
        parent_layout.addWidget(info_group)

    def create_chat_panel(self, parent_layout):
        # Main chat area with tabs
        chat_tabs = QTabWidget()
        chat_tabs.setStyleSheet("QTabBar::tab:selected {background-color: #3742fa; color: white; font-weight: bold;}")
        
        # Main chat tab
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        # Header with title and action buttons
        chat_header = QHBoxLayout()
        chat_title = QLabel("💬 Messages du jeu")
        chat_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        chat_header.addWidget(chat_title)
        
        # Quick action buttons for chat
        chat_header_btn_layout = QHBoxLayout()
        chat_header_btn_layout.addStretch()
        
        help_btn = QPushButton("❓ Aide")
        help_btn.setMaximumWidth(60)
        help_btn.clicked.connect(self.show_help)
        help_btn.setStyleSheet("background-color: #54a0ff;")
        
        chat_header_btn_layout.addWidget(help_btn)
        chat_header.addLayout(chat_header_btn_layout)
        chat_layout.addLayout(chat_header)
        
        # Chat display area with HTML formatting
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
        self.chat_display.setAcceptRichText(True)
        self.chat_display.document().setDefaultStyleSheet("a {color: #54a0ff;}")
        chat_layout.addWidget(self.chat_display)
        
        # Chat input area with action buttons
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message or a command /...")
        self.message_input.returnPressed.connect(self.send_chat_message)
        self.message_input.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px; padding: 5px;")
        
        # Contextual quick action buttons
        self.vote_btn = QPushButton("☀️ Vote")
        self.vote_btn.setToolTip("Day vote (eliminate a player)")
        self.vote_btn.clicked.connect(self.show_vote_dialog)
        self.vote_btn.setStyleSheet("background-color: #ffa502;")
        
        self.night_vote_btn = QPushButton("🌙 Night action")
        self.night_vote_btn.setToolTip("Night special action according to your role")
        self.night_vote_btn.clicked.connect(self.show_night_action_dialog)
        self.night_vote_btn.setStyleSheet("background-color: #9c88ff;")
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_chat_message)
        send_btn.setStyleSheet("background-color: #2ed573;")
        
        # Add components to the layout
        input_layout.addWidget(self.message_input, 7)
        input_layout.addWidget(self.vote_btn, 1)
        input_layout.addWidget(self.night_vote_btn, 1)
        input_layout.addWidget(send_btn, 1)
        
        chat_layout.addLayout(input_layout)
        
        # Add the main tab
        chat_tabs.addTab(chat_widget, "Chat général")
        
        # Log tab with event history
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        log_title = QLabel("📜 Journal des événements")
        log_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        log_layout.addWidget(log_title)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
        log_layout.addWidget(self.log_display)
        
        # Log filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        filter_all = QPushButton("All")
        filter_all.clicked.connect(lambda: self.filter_log("all"))
        filter_layout.addWidget(filter_all)
        
        filter_votes = QPushButton("Votes")
        filter_votes.clicked.connect(lambda: self.filter_log("vote"))
        filter_layout.addWidget(filter_votes)
        
        filter_deaths = QPushButton("Deaths")
        filter_deaths.clicked.connect(lambda: self.filter_log("death"))
        filter_layout.addWidget(filter_deaths)
        
        log_layout.addLayout(filter_layout)
        
        # Ajout de l'onglet journal
        chat_tabs.addTab(log_widget, "Log")
        
        # Game rules tab for quick reference
        rules_widget = QWidget()
        rules_layout = QVBoxLayout(rules_widget)
        
        rules_title = QLabel("📋 Game Rules")
        rules_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        rules_layout.addWidget(rules_title)
        
        rules_text = QTextEdit()
        rules_text.setReadOnly(True)
        rules_text.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
        rules_text.setHtml("""
            <h3>Game Roles</h3>
            <p><b>🐺 Werewolf</b>: Devours one villager each night</p>
            <p><b>👁️ Seer</b>: Can discover a player's identity each night</p>
            <p><b>🧙‍♀️ Witch</b>: Can save or kill a player with her potions</p>
            <p><b>🔫 Hunter</b>: Upon death can take another player down</p>
            <p><b>👨‍🌾 Villager</b>: Must find out who the werewolves are</p>

            <h3>Optimal role distribution</h3>
            <p>Role distribution is automatically optimized based on player count:</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse; color: #f1f2f6; width: 100%;">
                <tr style="background-color: #3742fa;">
                    <th>Players</th>
                    <th>🐺 Werewolves</th>
                    <th>👁️ Seer</th>
                    <th>🧙‍♀️ Witch</th>
                    <th>🔫 Hunter</th>
                    <th>👨‍🌾 Villagers</th>
                </tr>
                <tr>
                    <td align="center">6</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">-</td>
                    <td align="center">3</td>
                </tr>
                <tr>
                    <td align="center">8</td>
                    <td align="center">2</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">3</td>
                </tr>
                <tr>
                    <td align="center">10</td>
                    <td align="center">2</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">5</td>
                </tr>
                <tr>
                    <td align="center">12</td>
                    <td align="center">3</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">6</td>
                </tr>
                <tr>
                    <td align="center">14+</td>
                    <td align="center">~25%</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">1</td>
                    <td align="center">Rest</td>
                </tr>
            </table>

            <h3>Gameplay</h3>
            <p><b>Day</b>: Villagers debate and vote to eliminate a suspect</p>
            <p><b>Night</b>: Werewolves choose a victim, then special roles act</p>

            <h3>Victory</h3>
            <p><b>Villagers</b> win if they eliminate all werewolves</p>
            <p><b>Werewolves</b> win if they are at least as numerous as the villagers</p>
        """)
        rules_layout.addWidget(rules_text)
        
        # Add the rules tab
        chat_tabs.addTab(rules_widget, "Rules")
        
        # Ajout des onglets au layout principal
        parent_layout.addWidget(chat_tabs, 1)

    # The create_actions_panel function is no longer needed puisqu'on a intégré
    # les actions dans le panel d'information et dans la zone de chat

    def create_command_panel(self, parent_layout):
    
        cmd_group = QGroupBox("Command Terminal")
        cmd_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
        cmd_group_layout = QVBoxLayout(cmd_group)
        
        # Display previous commands with an improved design
        history_label = QLabel("Command history:")
        history_label.setStyleSheet("font-weight: bold; color: #dfe4ea;")
        cmd_group_layout.addWidget(history_label)
        
        self.cmd_history = QTextEdit()
        self.cmd_history.setReadOnly(True)
        self.cmd_history.setMaximumHeight(100)
        self.cmd_history.setStyleSheet("background-color: #2f3542; color: #a4b0be; border-radius: 5px; font-family: 'Consolas', monospace;")
        self.cmd_history.setPlaceholderText("Executed commands will appear here...")
        cmd_group_layout.addWidget(self.cmd_history)
        
        # Command input area styled like a console
        cmd_input_layout = QHBoxLayout()
        prompt_label = QLabel(">")
        prompt_label.setStyleSheet("color: #2ed573; font-weight: bold; font-size: 14px; font-family: 'Consolas', monospace;")
        cmd_input_layout.addWidget(prompt_label)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("/vote <player>, /nvote <player>, /start, /restart, /help")
        self.command_input.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px; padding: 5px; font-family: 'Consolas', monospace;")
        self.command_input.returnPressed.connect(self.process_command)
        cmd_input_layout.addWidget(self.command_input)
        
        # Run button
        exec_btn = QPushButton("▶️ Run")
        exec_btn.clicked.connect(self.process_command)
        exec_btn.setStyleSheet("background-color: #2ed573; font-weight: bold;")
        cmd_input_layout.addWidget(exec_btn)
        
        cmd_group_layout.addLayout(cmd_input_layout)
        
        # Grid layout of quick commands for more actions
        command_grid_layout = QGridLayout()
        
        # Game commands
        cmd_start = QPushButton("/start")
        cmd_start.clicked.connect(lambda: self.execute_quick_command("/start"))
        cmd_start.setStyleSheet("background-color: #2ed573;")
        command_grid_layout.addWidget(cmd_start, 0, 0)
        
        cmd_restart = QPushButton("/restart")
        cmd_restart.clicked.connect(lambda: self.execute_quick_command("/restart"))
        cmd_restart.setStyleSheet("background-color: #ff7f50;")
        command_grid_layout.addWidget(cmd_restart, 0, 1)
        
        # Vote commands
        cmd_vote = QPushButton("/vote")
        cmd_vote.clicked.connect(lambda: self.show_vote_dialog())
        cmd_vote.setStyleSheet("background-color: #ffa502;")
        command_grid_layout.addWidget(cmd_vote, 0, 2)
        
        cmd_nvote = QPushButton("/nvote")
        cmd_nvote.clicked.connect(lambda: self.show_night_vote_dialog())
        cmd_nvote.setStyleSheet("background-color: #9c88ff;")
        command_grid_layout.addWidget(cmd_nvote, 0, 3)
        
        # Night message commands
        cmd_nmsg = QPushButton("/nmsg")
        cmd_nmsg.clicked.connect(lambda: self.command_input.setText("/nmsg "))
        cmd_nmsg.setStyleSheet("background-color: #ff6b9d;")
        command_grid_layout.addWidget(cmd_nmsg, 1, 0)
        
        # Commands for special roles
        cmd_seer = QPushButton("Seer")
        cmd_seer.clicked.connect(lambda: self.show_seer_dialog())
        cmd_seer.setStyleSheet("background-color: #9c88ff;")
        command_grid_layout.addWidget(cmd_seer, 1, 1)
        
        cmd_witch = QPushButton("Witch")
        cmd_witch.clicked.connect(lambda: self.show_witch_dialog())
        cmd_witch.setStyleSheet("background-color: #ff6348;")
        command_grid_layout.addWidget(cmd_witch, 1, 2)
        
        cmd_help = QPushButton("/help")
        cmd_help.clicked.connect(lambda: self.execute_quick_command("/help"))
        cmd_help.setStyleSheet("background-color: #54a0ff;")
        command_grid_layout.addWidget(cmd_help, 1, 3)
        
        # Add the quick commands layout
        cmd_group_layout.addLayout(command_grid_layout)
        
        # Add the list of available commands
        help_layout = QHBoxLayout()
        help_layout.addWidget(QLabel("💡 Commands:"))
        help_text = QLabel("/vote, /nvote, /start, /restart, /nmsg, /help")
        help_text.setStyleSheet("font-style: italic; color: #a4b0be;")
        help_layout.addWidget(help_text)
        help_layout.addStretch()
        cmd_group_layout.addLayout(help_layout)
        
        # Add the command group to the main layout
        parent_layout.addWidget(cmd_group)
        
    def execute_quick_command(self, cmd):
        self.command_input.setText(cmd)
        self.process_command()
    
    def show_player_context_menu(self, position):
        menu = QMenu()
        selected_player = self.players_list_widget.currentItem()
        
        if not selected_player:
            return
            
        player_name = selected_player.text()
        
        # Actions based on game state and role
        if self.game_state == "day":
            vote_action = menu.addAction(f"🗳️ Vote against {player_name}")
            vote_action.triggered.connect(lambda: self.vote_for_player(player_name))
            
        elif self.game_state == "night":
            if self.player_role == "werewolf":
                night_vote_action = menu.addAction(f"🐺 Attack {player_name}")
                night_vote_action.triggered.connect(lambda: self.night_vote_for_player(player_name))
                
            elif self.player_role == "voyante":
                see_action = menu.addAction(f"👁️ Inspect {player_name}")
                see_action.triggered.connect(lambda: self.seer_examine_player(player_name))
                
            elif self.player_role == "sorcière":
                kill_action = menu.addAction(f"☠️ Poison {player_name}")
                kill_action.triggered.connect(lambda: self.witch_kill_player(player_name))
                
            elif self.player_role == "chasseur":
                shoot_action = menu.addAction(f"🔫 Shoot {player_name}")
                shoot_action.triggered.connect(lambda: self.hunter_shoot_player(player_name))
            
        # Private message action (feature to implement later)
        whisper_action = menu.addAction(f"💬 Private message to {player_name}")
        whisper_action.triggered.connect(lambda: self.whisper_to_player(player_name))
        
        # Show the menu
        menu.exec_(self.players_list_widget.mapToGlobal(position))
    
    def vote_for_player(self, player_name):
        reply = QMessageBox.question(self, "Vote confirmation",
                                     f"Do you want to vote against {player_name}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.network_worker.send_message(MessageType.VOTE.value, player_name)
            self.add_chat_message("VOTE", f"You voted against {player_name}", "#ffa502")
            self.add_to_command_history(f"/vote {player_name}")
    
    def night_vote_for_player(self, player_name):
        reply = QMessageBox.question(self, "Attack confirmation",
                                     f"Do you want to attack {player_name} tonight?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, player_name)
            self.add_chat_message("NIGHT VOTE", f"You chose to attack {player_name}", "#ff6b9d")
            self.add_to_command_history(f"/nvote {player_name}")
    
    def seer_examine_player(self, player_name):
        self.network_worker.send_message(MessageType.SEER_ACTION.value, player_name)
        self.add_chat_message("SEER", f"You examine {player_name}...", "#9c88ff")
        # Waiting for server response with SEER_RESULT - see handle_server_message
    
    def witch_kill_player(self, player_name):
        self.network_worker.send_message(MessageType.NIGHT_VOTE.value, f"witch_kill:{player_name}")
        self.add_chat_message("WITCH", f"You poisoned {player_name}", "#ff6348")
    
    def hunter_shoot_player(self, player_name):
        self.network_worker.send_message(MessageType.HUNTER_SHOOT.value, player_name)
        self.add_chat_message("HUNTER", f"You shot {player_name}", "#ff9f43")
    
    def whisper_to_player(self, player_name):
        # Feature to implement later
        self.add_chat_message("SYSTEM", f"Private messages are not implemented yet", "#ff6b6b")
    
    def show_vote_dialog(self):
        if not self.players_list_widget.count():
            QMessageBox.warning(self, "Unable to vote", "No players available for voting.")
            return
            
        players = []
        for i in range(self.players_list_widget.count()):
            players.append(self.players_list_widget.item(i).text())
            
        target, ok = QInputDialog.getItem(self, "Vote", "Choose a player to eliminate:",
                                        players, 0, False)
        if ok and target:
            self.vote_for_player(target)

    def show_night_action_dialog(self):
        # This dialog is triggered manually by the "Night action" button or the menu
        # But normally actions are triggered automatically by server messages
        
        # Check if it is currently night
        if self.game_state != "night":
            QMessageBox.information(self, "Night action",
                                   "Special actions can only be performed at night.")
            return
        
        # Show the appropriate dialog according to the role
        if self.player_role == "werewolf":
            self.show_night_vote_dialog()
        elif self.player_role == "voyante":
            self.show_seer_dialog()
        elif self.player_role == "sorcière":
            self.show_witch_dialog()
        elif self.player_role == "chasseur":
            self.show_hunter_dialog()
        else:
            QMessageBox.information(self, "Night action",
                                   "You have no special action tonight. Wait for the other players to finish their actions.")

    def show_night_vote_dialog(self):
        # Retrieve the list of living players from the list widget
        players = []
        
        # Debug info
        print(f"DEBUG - Construire la liste des joueurs pour le vote de nuit")
        print(f"DEBUG - Nombre total de joueurs: {self.players_list_widget.count()}")
        
        # Exclude the player themselves and those marked as dead
        for i in range(self.players_list_widget.count()):
            item = self.players_list_widget.item(i)
            if item:
                player_name = item.text()
                print(f"DEBUG - Joueur trouvé: '{player_name}'")
                
                # Vérifier si c'est un joueur vivant qui n'est pas le joueur actuel
                if not "(mort)" in player_name and player_name != self.username:
                    clean_name = player_name.split(" (")[0]  # Ne garder que le nom sans les annotations
                    players.append(clean_name)
                    print(f"DEBUG - Ajouté à la liste: '{clean_name}'")
                else:
                    print(f"DEBUG - Exclu de la liste: '{player_name}'")
        
        # Check that the list is not empty
        if not players:
            print("DEBUG - Liste des joueurs vide pour le vote nocturne!")
            QMessageBox.warning(self, "Unable to vote", "No players available for voting.")
            
            # Display all players for debugging
            all_players = [self.players_list_widget.item(i).text() for i in range(self.players_list_widget.count())]
            print(f"DEBUG - Tous les joueurs: {all_players}")
            return
        
        print(f"DEBUG - Liste finale des joueurs pour le vote: {players}")
        target, ok = QInputDialog.getItem(self, "Night Vote",
                                       "Choose a victim for tonight:",
                                       players, 0, False)
        if ok and target:
            self.night_vote_for_player(target)
    
    def show_witch_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Witch Actions")
        layout = QVBoxLayout(dialog)
        
        # Image or icon for the witch
        witch_icon_label = QLabel()
        witch_icon = QPixmap("witch_icon.png") # You can add an image later
        if not witch_icon.isNull():
            witch_icon_label.setPixmap(witch_icon.scaled(64, 64, Qt.KeepAspectRatio))
        else:
            witch_icon_label.setText("🧙‍♀️")
            witch_icon_label.setStyleSheet("font-size: 32px;")
        witch_icon_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(witch_icon_label)
        
        layout.addWidget(QLabel("You are the witch. What do you want to do?"))
        
        # Witch options
        no_action_btn = QPushButton("Do nothing")
        save_btn = QPushButton("Save the victim")
        kill_btn = QPushButton("Poison a player")
        
        layout.addWidget(no_action_btn)
        layout.addWidget(save_btn)
        layout.addWidget(kill_btn)
        
        no_action_btn.clicked.connect(lambda: self.witch_action("none", dialog))
        save_btn.clicked.connect(lambda: self.witch_action("save", dialog))
        kill_btn.clicked.connect(lambda: self.witch_select_target(dialog))
        
        dialog.exec_()
    
    def witch_action(self, action, dialog):
        if action == "none":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_none")
            self.add_chat_message("WITCH", "You didn't use any potion", "#ff6348")
        elif action == "save":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_save")
            self.add_chat_message("WITCH", "You used your healing potion to save the victim", "#ff6348")
        dialog.accept()
    
    def witch_select_target(self, parent_dialog):
        parent_dialog.accept()
        
        # Retrieve the list of living players
        players = []
        for i in range(self.players_list_widget.count()):
            item = self.players_list_widget.item(i)
            if item and not "(mort)" in item.text():
                players.append(item.text().split(" (")[0])  # Keep only the name without the role
        
        # Check that the list is not empty
        if not players:
            QMessageBox.warning(self, "Action impossible", "No player available to poison.")
            return
            
        target, ok = QInputDialog.getItem(self, "Poison",
                                       "Choose a player to poison:",
                                       players, 0, False)
        if ok and target:
            self.witch_kill_player(target)
    
    def show_seer_dialog(self):
        # Retrieve the list of living players
        players = []
        
        print(f"DEBUG - Construire la liste des joueurs pour la voyante")
        print(f"DEBUG - Nombre total de joueurs: {self.players_list_widget.count()}")
        
        for i in range(self.players_list_widget.count()):
            item = self.players_list_widget.item(i)
            if item:
                player_name = item.text()
                print(f"DEBUG - Joueur trouvé: '{player_name}'")
                
                # Vérifier si c'est un joueur vivant qui n'est pas le joueur actuel
                if not "(mort)" in player_name and player_name != self.username:
                    clean_name = player_name.split(" (")[0]  # Ne garder que le nom sans les annotations
                    players.append(clean_name)
                    print(f"DEBUG - Ajouté à la liste: '{clean_name}'")
                else:
                    print(f"DEBUG - Exclu de la liste: '{player_name}'")
        
        # If no player is found, try a less strict search
        if not players:
            print("DEBUG - Aucun joueur trouvé, essayons une méthode alternative")
            # Alternative method: include all players except yourself
            for i in range(self.players_list_widget.count()):
                item = self.players_list_widget.item(i)
                if item and item.text() != self.username:
                    players.append(item.text())
                    print(f"DEBUG - Ajouté (méthode alt): '{item.text()}'")
        
        # Check that the list is not empty
        if not players:
            print("DEBUG - Liste des joueurs vide pour la voyante!")
            QMessageBox.warning(self, "Action impossible", "No player available to inspect.")
            return
            
        print(f"DEBUG - Liste finale pour la voyante: {players}")
        target, ok = QInputDialog.getItem(self, "Seer Vision",
                                       "Choose a player to inspect:",
                                       players, 0, False)
        if ok and target:
            self.seer_examine_player(target)
    
    def show_hunter_dialog(self):
        # Retrieve the list of living players
        players = []
        for i in range(self.players_list_widget.count()):
            item = self.players_list_widget.item(i)
            if item and not "(mort)" in item.text():
                players.append(item.text().split(" (")[0])  # Keep only the name without the role
        
        # Check that the list is not empty
        if not players:
            QMessageBox.warning(self, "Action impossible", "No player available to shoot.")
            return
            
        target, ok = QInputDialog.getItem(self, "Hunter Shot",
                                       "Choose a player to shoot:",
                                       players, 0, False)
        if ok and target:
            self.hunter_shoot_player(target)


    def send_chat_message(self):
        message = self.message_input.text().strip()
        if message and self.network_worker:
            self.network_worker.send_message(MessageType.MSG.value, message)
            self.message_input.clear()

    def process_command(self):
        command = self.command_input.text().strip()
        if not command or not self.network_worker:
            return
        
        # Log the command in the command history
        self.cmd_history.append(f"> {command}")
        
        if command.startswith("/vote "):
            target = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.VOTE.value, target)
            self.add_chat_message("COMMANDE", f"Vote contre {target}", "#2ed573")
        elif command.startswith("/nvote "):
            target = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, target)
            self.add_chat_message("COMMANDE", f"Vote de nuit contre {target}", "#2ed573")
        elif command == "/start":
            self.network_worker.send_message(MessageType.START.value, "")
            self.add_chat_message("COMMANDE", "Démarrage de la partie", "#2ed573")
        elif command == "/restart":
            self.network_worker.send_message(MessageType.RESTART.value, "")
            self.add_chat_message("COMMANDE", "Redémarrage de la partie", "#2ed573")
        elif command.startswith("/nmsg "):
            msg = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.NIGHT_MSG.value, msg)
            self.add_chat_message("COMMANDE", "Message de nuit envoyé", "#2ed573")
        elif command.startswith("/seer "):
            target = command.split(" ", 1)[1]
            self.seer_examine_player(target)
        elif command.startswith("/witch_kill "):
            target = command.split(" ", 1)[1]
            self.witch_kill_player(target)
        elif command == "/witch_save":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_save")
            self.add_chat_message("WITCH", "You used your healing potion to save the victim", "#ff6348")
        elif command == "/witch_none":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_none")
            self.add_chat_message("WITCH", "You didn't use any potion", "#ff6348")
        elif command.startswith("/hunter "):
            target = command.split(" ", 1)[1]
            self.hunter_shoot_player(target)
        elif command.startswith("/whisper "):
            parts = command.split(" ", 2)
            if len(parts) >= 3:
                target = parts[1]
                msg = parts[2]
                self.whisper_to_player(target)
            else:
                self.add_chat_message("ERREUR", "Format incorrect. Utilisez /whisper <joueur> <message>", "#ff6b6b")
        elif command == "/help":
            self.show_help()
        else:
            self.add_chat_message("ERREUR", "Commande inconnue. Tapez /help pour voir les commandes.", "#ff6b6b")
        
        self.command_input.clear()

    def start_game(self):
        if self.network_worker:
            self.network_worker.send_message(MessageType.START.value, "")

    def restart_game(self):
        reply = QMessageBox.question(self, "Redémarrer", "Voulez-vous vraiment redémarrer le jeu?")
        if reply == QMessageBox.Yes and self.network_worker:
            self.network_worker.send_message(MessageType.RESTART.value, "")

    def show_help(self):
        help_text = (
            "General commands:\n"
            "/vote <player> - Vote against a player (day)\n"
            "/nvote <player> - Vote against a player (night, werewolf)\n"
            "/start - Start the game\n"
            "/restart - Restart the game\n\n"

            "Role commands:\n"
            "/seer <player> - Inspect a player (seer)\n"
            "/witch_kill <player> - Poison a player (witch)\n"
            "/witch_save - Save the werewolves' victim (witch)\n"
            "/witch_none - Do nothing (witch)\n"
            "/hunter <player> - Shoot a player (hunter)\n\n"

            "Other commands:\n"
            "/nmsg <message> - Send a night message\n"
            "/whisper <player> <message> - Send a private message to a player\n"
            "/help - Show this help"
        )
        QMessageBox.information(self, "Help", help_text)

    def set_game_controls_enabled(self, enabled):
        self.start_btn.setEnabled(enabled)
        self.vote_btn.setEnabled(enabled)
        self.night_vote_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)
        self.message_input.setEnabled(enabled)
        self.command_input.setEnabled(enabled)

    def add_chat_message(self, msg_type, message, color="#ffffff"):
        """Add a message to the chat with HTML formatting"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.chat_display.append(f'<span style="color: #a4b0be;">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">[{msg_type}]</span> {message}')
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
        
    def add_to_log(self, msg_type, message, color="#ffffff"):
        """Add an entry to the event log"""
        timestamp = QDateTime.currentDateTime().toString("dd/MM hh:mm:ss")
        self.log_display.append(f'<span style="color: #a4b0be;">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">[{msg_type}]</span> {message}')
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())
    
    def add_to_command_history(self, command):
        """Add a command to the terminal history"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.cmd_history.append(f'<span style="color: #a4b0be;">[{timestamp}]</span> <span style="color: #2ed573;">{command}</span>')
        self.cmd_history.verticalScrollBar().setValue(self.cmd_history.verticalScrollBar().maximum())
    
    def filter_log(self, filter_type):
        """Filtre les entrées du journal selon le type"""
        # This feature could be implemented later
        pass
    
    def update_buttons_visibility(self):
        """Met à jour la visibilité des boutons en fonction de l'état du jeu et du rôle"""
        is_alive = True  # To improve later with a real status
        
        # Day voting buttons
        self.vote_btn.setVisible(self.game_state == "day" and is_alive)
        
        # Night action buttons depending on the role
        self.night_vote_btn.setVisible(self.game_state == "night" and is_alive and 
                                       self.player_role in ["werewolf", "voyante", "sorcière", "chasseur"])
        
        # Update the role label with an icon
        role_icons = {
            "werewolf": "🐺",
            "villager": "👨‍🌾", 
            "voyante": "👁️",
            "sorcière": "🧙‍♀️",
            "chasseur": "🔫"
        }
        
        if self.player_role in role_icons:
            self.role_label.setText(f"{role_icons[self.player_role]} {self.player_role}")

    def check_auto_popups(self):
        """Automatically display appropriate popups based on game state and role"""
        # Popups are now managed directly by server signals
        # and are only shown when specific signals are received
        # SEER_ACTION, WITCH_ACTION, HUNTER_SHOOT, etc.
        pass
    def closeEvent(self, event):
        """Handle clean application shutdown"""
        reply = QMessageBox.question(self, 'Confirmation',
                                     'Are you sure you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                                      
        if reply == QMessageBox.Yes:
            if self.network_worker:
                self.network_worker.disconnect()
            if self.network_thread and self.network_thread.isRunning():
                self.network_thread.quit()
                self.network_thread.wait()
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    app.setPalette(palette)
    client = WerewolfClient()
    client.show()
    sys.exit(app.exec_())
