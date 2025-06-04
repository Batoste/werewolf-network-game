#!/usr/bin/env python3
"""
Client GUI pour Werewolf Game utilisant PyQt5
Réutilise l'architecture existante avec common.protocol et server.state
"""

import sys
import os
import socket
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Ajouter le chemin du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.protocol import encode_message, decode_message, MessageType
from server.state import state

class NetworkWorker(QObject):
    """Worker pour gérer la communication réseau dans un thread séparé"""
    message_received = pyqtSignal(str, str)  # msg_type, payload
    connection_lost = pyqtSignal()
    connected = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.sock = None
        self.running = False
        self.buffer = ""
    
    def connect_to_server(self, username):
        """Se connecter au serveur"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((state.HOST, state.PORT))
            
            # Envoyer message de connexion
            join_msg = encode_message(MessageType.JOIN.value, username)
            self.sock.sendall(join_msg.encode())
            
            self.running = True
            self.connected.emit()
            return True
        except Exception as e:
            print(f"Erreur connexion: {e}")
            return False
    
    def listen_for_messages(self):
        """Écouter les messages du serveur"""
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
                print(f"Erreur réception: {e}")
                break
        
        self.connection_lost.emit()
    
    def send_message(self, msg_type, payload):
        """Envoyer un message au serveur"""
        if self.sock and self.running:
            try:
                formatted_msg = encode_message(msg_type, payload)
                self.sock.sendall(formatted_msg.encode())
            except Exception as e:
                print(f"Erreur envoi: {e}")
    
    def disconnect(self):
        """Fermer la connexion"""
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
        """Initialiser l'interface utilisateur"""
        self.setWindowTitle("🐺 Werewolf Game Client")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Barre de connexion
        self.create_connection_panel(main_layout)
        
        # Zone de jeu principale
        game_widget = QWidget()
        game_layout = QHBoxLayout(game_widget)
        main_layout.addWidget(game_widget)
        
        # Panneau gauche - Informations du jeu
        self.create_game_info_panel(game_layout)
        
        # Panneau central - Messages et chat
        self.create_chat_panel(game_layout)
        
        # Panneau droit - Actions
        self.create_actions_panel(game_layout)
        
        # Barre de commandes
        self.create_command_panel(main_layout)
        
        # Désactiver les contrôles au début
        self.set_game_controls_enabled(False)
        
        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666;
                border-radius: 5px;
                padding: 8px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 5px;
                color: #ffffff;
            }
        """)
    
    def create_connection_panel(self, parent_layout):
        """Créer le panneau de connexion"""
        conn_frame = QFrame()
        conn_frame.setFrameStyle(QFrame.StyledPanel)
        conn_layout = QHBoxLayout(conn_frame)
        
        conn_layout.addWidget(QLabel("Nom d'utilisateur:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Entrez votre nom...")
        conn_layout.addWidget(self.username_input)
        
        self.connect_btn = QPushButton("Se connecter")
        self.connect_btn.clicked.connect(self.connect_to_server)
        conn_layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("Non connecté")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        conn_layout.addWidget(self.status_label)
        
        parent_layout.addWidget(conn_frame)
    
    def create_game_info_panel(self, parent_layout):
        """Créer le panneau d'informations du jeu"""
        info_widget = QWidget()
        info_widget.setMaximumWidth(250)
        info_layout = QVBoxLayout(info_widget)
        
        # Informations du joueur
        info_layout.addWidget(QLabel("📋 Informations du jeu"))
        
        self.role_label = QLabel("Rôle: Inconnu")
        self.role_label.setStyleSheet("font-weight: bold; color: #ff9f43;")
        info_layout.addWidget(self.role_label)
        
        self.state_label = QLabel("État: En attente")
        self.state_label.setStyleSheet("font-weight: bold; color: #3742fa;")
        info_layout.addWidget(self.state_label)
        
        # Liste des joueurs
        info_layout.addWidget(QLabel("👥 Joueurs connectés"))
        self.players_list_widget = QListWidget()
        self.players_list_widget.setMaximumHeight(200)
        info_layout.addWidget(self.players_list_widget)
        
        info_layout.addStretch()
        parent_layout.addWidget(info_widget)
    
    def create_chat_panel(self, parent_layout):
        """Créer le panneau de chat"""
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        chat_layout.addWidget(QLabel("💬 Messages du jeu"))
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(self.chat_display)
        
        # Zone de saisie de message
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Tapez votre message...")
        self.message_input.returnPressed.connect(self.send_chat_message)
        
        send_btn = QPushButton("Envoyer")
        send_btn.clicked.connect(self.send_chat_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        chat_layout.addLayout(input_layout)
        
        parent_layout.addWidget(chat_widget)
    
    def create_actions_panel(self, parent_layout):
        """Créer le panneau d'actions"""
        actions_widget = QWidget()
        actions_widget.setMaximumWidth(200)
        actions_layout = QVBoxLayout(actions_widget)
        
        actions_layout.addWidget(QLabel("⚡ Actions"))
        
        # Bouton démarrer
        self.start_btn = QPushButton("🎮 Démarrer le jeu")
        self.start_btn.clicked.connect(self.start_game)
        actions_layout.addWidget(self.start_btn)
        
        # Bouton voter
        self.vote_btn = QPushButton("🗳️ Voter")
        self.vote_btn.clicked.connect(self.show_vote_dialog)
        actions_layout.addWidget(self.vote_btn)
        
        # Bouton vote de nuit
        self.night_vote_btn = QPushButton("🌙 Vote nocturne")
        self.night_vote_btn.clicked.connect(self.show_night_vote_dialog)
        actions_layout.addWidget(self.night_vote_btn)
        
        # Bouton redémarrer
        self.restart_btn = QPushButton("🔄 Redémarrer")
        self.restart_btn.clicked.connect(self.restart_game)
        actions_layout.addWidget(self.restart_btn)
        
        # Bouton aide
        help_btn = QPushButton("❓ Aide")
        help_btn.clicked.connect(self.show_help)
        actions_layout.addWidget(help_btn)
        
        actions_layout.addStretch()
        parent_layout.addWidget(actions_widget)
    
    def create_command_panel(self, parent_layout):
        """Créer le panneau de commandes rapides"""
        cmd_frame = QFrame()
        cmd_frame.setFrameStyle(QFrame.StyledPanel)
        cmd_layout = QHBoxLayout(cmd_frame)
        
        cmd_layout.addWidget(QLabel("Commande rapide:"))
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("/vote <joueur>, /help, /start, etc.")
        self.command_input.returnPressed.connect(self.process_command)
        cmd_layout.addWidget(self.command_input)
        
        exec_btn = QPushButton("Exécuter")
        exec_btn.clicked.connect(self.process_command)
        cmd_layout.addWidget(exec_btn)
        
        parent_layout.addWidget(cmd_frame)
    
    def setup_network(self):
        """Configurer le réseau"""
        self.network_thread = QThread()
        self.network_worker = NetworkWorker()
        self.network_worker.moveToThread(self.network_thread)
        
        # Connexions des signaux
        self.network_worker.message_received.connect(self.handle_server_message)
        self.network_worker.connection_lost.connect(self.handle_connection_lost)
        self.network_worker.connected.connect(self.handle_connected)
        
        self.network_thread.started.connect(self.network_worker.listen_for_messages)
    
    def connect_to_server(self):
        """Se connecter au serveur"""
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un nom d'utilisateur!")
            return
        
        self.username = username
        
        if self.network_worker.connect_to_server(username):
            self.network_thread.start()
            self.connect_btn.setText("Connexion...")
            self.connect_btn.setEnabled(False)
        else:
            QMessageBox.critical(self, "Erreur", "Impossible de se connecter au serveur!")
    
    def handle_connected(self):
        """Gérer la connexion réussie"""
        self.status_label.setText("Connecté")
        self.status_label.setStyleSheet("color: #2ed573;")
        self.connect_btn.setText("Connecté")
        self.set_game_controls_enabled(True)
        self.add_chat_message("SYSTÈME", "Connecté au serveur avec succès!", "#2ed573")
    
    def handle_connection_lost(self):
        """Gérer la perte de connexion"""
        self.status_label.setText("Connexion perdue")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        self.connect_btn.setText("Se connecter")
        self.connect_btn.setEnabled(True)
        self.set_game_controls_enabled(False)
        self.add_chat_message("SYSTÈME", "Connexion perdue avec le serveur!", "#ff6b6b")
    
    def handle_server_message(self, msg_type, payload):
        """Traiter les messages du serveur"""
        color_map = {
            "MSG": "#54a0ff",
            "VOTE": "#ffa502",
            "ROLE": "#ff6348",
            "STATE": "#2ed573",
            "JOIN": "#3742fa",
            "START": "#2ed573",
            "KILL": "#ff3838",
            "NIGHT_MSG": "#ff6b9d"
        }
        
        color = color_map.get(msg_type, "#ffffff")
        
        if msg_type == "ROLE":
            self.player_role = payload
            self.role_label.setText(f"Rôle: {payload}")
            self.add_chat_message("RÔLE", f"Vous êtes un {payload}!", color)
        
        elif msg_type == "STATE":
            self.game_state = payload
            if payload == "villagers_win":
                self.state_label.setText("État: Villageois gagnent!")
                self.add_chat_message("VICTOIRE", "🎉 Les villageois ont gagné!", "#2ed573")
            elif payload == "werewolves_win":
                self.state_label.setText("État: Loups-garous gagnent!")
                self.add_chat_message("VICTOIRE", "🐺 Les loups-garous ont gagné!", "#ff3838")
            elif payload == "day":
                self.state_label.setText("État: Jour")
                self.add_chat_message("ÉTAT", "☀️ Le jour s'est levé!", color)
            elif payload == "night":
                self.state_label.setText("État: Nuit")
                self.add_chat_message("ÉTAT", "🌙 La nuit tombe...", color)
            else:
                self.state_label.setText(f"État: {payload}")
                self.add_chat_message("ÉTAT", payload, color)
        
        else:
            self.add_chat_message(msg_type, payload, color)
    
    def add_chat_message(self, msg_type, message, color="#ffffff"):
        """Ajouter un message au chat"""
        self.chat_display.append(f'<span style="color: {color};">[{msg_type}] {message}</span>')
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
    
    def send_chat_message(self):
        """Envoyer un message de chat"""
        message = self.message_input.text().strip()
        if message and self.network_worker:
            self.network_worker.send_message(MessageType.MSG.value, message)
            self.message_input.clear()
    
    def process_command(self):
        """Traiter une commande"""
        command = self.command_input.text().strip()
        if not command or not self.network_worker:
            return
        
        if command.startswith("/vote "):
            target = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.VOTE.value, target)
        
        elif command.startswith("/nvote "):
            target = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, target)
        
        elif command == "/start":
            self.network_worker.send_message(MessageType.START.value, "")
        
        elif command == "/restart":
            self.network_worker.send_message(MessageType.RESTART.value, "")
        
        elif command.startswith("/nmsg "):
            msg = command.split(" ", 1)[1]
            self.network_worker.send_message(MessageType.NIGHT_MSG.value, msg)
        
        elif command == "/help":
            self.show_help()
        
        else:
            self.add_chat_message("ERREUR", "Commande inconnue. Tapez /help pour voir les commandes.", "#ff6b6b")
        
        self.command_input.clear()
    
    def start_game(self):
        """Démarrer le jeu"""
        if self.network_worker:
            self.network_worker.send_message(MessageType.START.value, "")
    
    def show_vote_dialog(self):
        """Afficher la boîte de dialogue de vote"""
        target, ok = QInputDialog.getText(self, "Vote", "Nom du joueur à voter:")
        if ok and target.strip():
            self.network_worker.send_message(MessageType.VOTE.value, target.strip())
    
    def show_night_vote_dialog(self):
        """Afficher la boîte de dialogue de vote nocturne"""
        target, ok = QInputDialog.getText(self, "Vote nocturne", "Nom du joueur à éliminer:")
        if ok and target.strip():
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, target.strip())
    
    def restart_game(self):
        """Redémarrer le jeu"""
        reply = QMessageBox.question(self, "Redémarrer", "Voulez-vous vraiment redémarrer le jeu?")
        if reply == QMessageBox.Yes and self.network_worker:
            self.network_worker.send_message(MessageType.RESTART.value, "")
    
    def show_help(self):
        """Afficher l'aide"""
        help_text = """
        <h3>Commandes disponibles:</h3>
        <ul>
        <li><b>/vote &lt;joueur&gt;</b> - Voter pour éliminer un joueur</li>
        <li><b>/nvote &lt;joueur&gt;</b> - Vote nocturne (loups-garous)</li>
        <li><b>/nmsg &lt;message&gt;</b> - Message nocturne</li>
        <li><b>/start</b> - Démarrer le jeu</li>
        <li><b>/restart</b> - Redémarrer le jeu</li>
        <li><b>/help</b> - Afficher cette aide</li>
        </ul>
        
        <h3>Rôles:</h3>
        <ul>
        <li><b>Villageois</b> - Éliminez tous les loups-garous</li>
        <li><b>Loup-garou</b> - Éliminez tous les villageois</li>
        <li><b>Voyante</b> - Peut voir le rôle d'un joueur chaque nuit</li>
        <li><b>Sorcière</b> - Peut sauver ou empoisonner un joueur</li>
        <li><b>Chasseur</b> - Peut éliminer un joueur en mourant</li>
        </ul>
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Aide - Werewolf Game")
        msg_box.setText(help_text)
        msg_box.exec_()
    
    def set_game_controls_enabled(self, enabled):
        """Activer/désactiver les contrôles de jeu"""
        self.start_btn.setEnabled(enabled)
        self.vote_btn.setEnabled(enabled)
        self.night_vote_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)
        self.message_input.setEnabled(enabled)
        self.command_input.setEnabled(enabled)
    
    def closeEvent(self, event):
        """Nettoyer à la fermeture"""
        if self.network_worker:
            self.network_worker.disconnect()
        if self.network_thread and self.network_thread.isRunning():
            self.network_thread.quit()
            self.network_thread.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Style moderne
    
    # Palette sombre
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    client = WerewolfClient()
    client.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()