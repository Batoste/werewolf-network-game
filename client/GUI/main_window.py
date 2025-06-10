from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
                             QLineEdit, QTextEdit, QListWidget, QMessageBox,
                             QSplitter, QHBoxLayout, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor
from .network_worker import NetworkWorker
from .utils import add_chat_message, add_to_log, add_to_command_history
from .dialogs import show_witch_dialog, show_seer_dialog, show_night_vote_dialog, show_hunter_dialog
from common.protocol import MessageType


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
        
        # Utilisation des fonctions importées de panels.py
        from .panels import create_connection_panel, create_game_info_panel, create_chat_panel
        create_connection_panel(self, main_layout)
        
        # Main splitter allowing the user to adjust panel sizes
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel for game information and player list
        left_widget = QWidget()
        left_widget.setMinimumWidth(250)
        left_layout = QVBoxLayout(left_widget)
        create_game_info_panel(self, left_layout)
        main_splitter.addWidget(left_widget)
        
        # Center panel for chat
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        create_chat_panel(self, center_layout)
        main_splitter.addWidget(center_widget)
        
        # Extended command area at the bottom
        #self.create_command_panel(main_layout)
        
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
        from .utils import add_chat_message
        add_chat_message(self, "SYSTEM", "Connected to server successfully!", "#2ed573")
        
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
            # Utilisation de la fonction importée
            from .dialogs import show_witch_dialog
            show_witch_dialog(self)
            
        elif msg_type == "SEER_ACTION":
            # Utilisation de la fonction importée
            from .dialogs import show_seer_dialog
            show_seer_dialog(self)
            
        elif msg_type == "WEREWOLF_ACTION":
            # Utilisation de la fonction importée
            from .dialogs import show_night_vote_dialog
            show_night_vote_dialog(self)

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
            # Utilisation de la fonction importée
            from .dialogs import show_hunter_dialog
            show_hunter_dialog(self)
            
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
            self.add_chat_message("COMMANDE", f"Vote against {target}", "#2ed573")
        elif command.startswith("/nvote "):
            target = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, target)
            self.add_chat_message("COMMANDE", f"Night vote against {target}", "#2ed573")
        elif command == "/start":
            self.network_worker.send_message(MessageType.START.value, "")
            self.add_chat_message("COMMANDE", "Starting game", "#2ed573")
        elif command == "/restart":
            self.network_worker.send_message(MessageType.RESTART.value, "")
            self.add_chat_message("COMMANDE", "Restarting game", "#2ed573")
        elif command.startswith("/nmsg "):
            msg = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.NIGHT_MSG.value, msg)
            self.add_chat_message("COMMANDE", "Night message", "#2ed573")
        elif command.startswith("/seer "):
            target = command.split(" ", 1)[1]
            from .actions import seer_examine_player
            seer_examine_player(self, target)
        elif command.startswith("/witch_kill "):
            target = command.split(" ", 1)[1]
            from .actions import witch_kill_player
            witch_kill_player(self, target)
        elif command == "/witch_save":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_save")
            self.add_chat_message("WITCH", "You used your healing potion to save the victim", "#ff6348")
        elif command == "/witch_none":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_none")
            self.add_chat_message("WITCH", "You didn't use any potion", "#ff6348")
        elif command.startswith("/hunter "):
            target = command.split(" ", 1)[1]
            from .actions import hunter_shoot_player
            hunter_shoot_player(self, target)
        elif command.startswith("/whisper "):
            parts = command.split(" ", 2)
            if len(parts) >= 3:
                target = parts[1]
                msg = parts[2]
                from .actions import whisper_to_player
                whisper_to_player(self, target)
            else:
                self.add_chat_message("ERREUR", "Format incorrect. Utilisez /whisper <joueur> <message>", "#ff6b6b")
        elif command == "/help":
            from .utils import show_help
            show_help(self)
        else:
            self.add_chat_message("ERREUR", "Commande inconnue. Tapez /help pour voir les commandes.", "#ff6b6b")
        
        self.command_input.clear()

    def start_game(self):
        if self.network_worker:
            self.network_worker.send_message(MessageType.START.value, "")

    def restart_game(self):
        reply = QMessageBox.question(self, "Resart", "Do you want to restart the game?",)
        if reply == QMessageBox.Yes and self.network_worker:
            self.network_worker.send_message(MessageType.RESTART.value, "")

    def set_game_controls_enabled(self, enabled):
            self.start_btn.setEnabled(enabled)
            self.vote_btn.setEnabled(enabled)
            self.night_vote_btn.setEnabled(enabled)
            self.restart_btn.setEnabled(enabled)
            self.message_input.setEnabled(enabled)
            #self.command_input.setEnabled(enabled)
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