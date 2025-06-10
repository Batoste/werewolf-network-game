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
            print(f"Erreur connexion: {e}")
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
                print(f"Erreur réception: {e}")
                break
        self.connection_lost.emit()

    def send_message(self, msg_type, payload):
        if self.sock and self.running:
            try:
                formatted_msg = encode_message(msg_type, payload)
                self.sock.sendall(formatted_msg.encode())
                
                # Enregistrer certaines commandes dans l'historique
                if msg_type in [MessageType.VOTE.value, MessageType.NIGHT_VOTE.value, MessageType.START.value, MessageType.RESTART.value]:
                    cmd = f"/{msg_type.lower()}"
                    if payload:
                        cmd += f" {payload}"
                    self.message_received.emit("COMMANDE", f"Commande envoyée: {cmd}")
            except Exception as e:
                print(f"Erreur envoi: {e}")

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
        
        # Splitter principal pour permettre à l'utilisateur d'ajuster les tailles
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Panel gauche pour les informations et liste des joueurs
        left_widget = QWidget()
        left_widget.setMinimumWidth(250)
        left_layout = QVBoxLayout(left_widget)
        self.create_game_info_panel(left_layout)
        main_splitter.addWidget(left_widget)
        
        # Panel central pour le chat
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.create_chat_panel(center_layout)
        main_splitter.addWidget(center_widget)
        
        # Zone de commande étendue en bas
        self.create_command_panel(main_layout)
        
        # Définir les tailles relatives des panneaux
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
        self.status_label.setText("Connecté")
        self.status_label.setStyleSheet("color: #2ed573;")
        self.connect_btn.setText("Connecté")
        self.set_game_controls_enabled(True)
        self.add_chat_message("SYSTÈME", "Connecté au serveur avec succès!", "#2ed573")
        
        # Ajouter le joueur local à sa propre liste
        if self.username and self.username not in [self.players_list_widget.item(i).text() for i in range(self.players_list_widget.count())]:
            self.players_list_widget.addItem(self.username)

    def handle_connection_lost(self):
        self.status_label.setText("Connexion perdue")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        self.connect_btn.setText("Se connecter")
        self.connect_btn.setEnabled(True)
        self.set_game_controls_enabled(False)
        self.add_chat_message("SYSTÈME", "Connexion perdue avec le serveur!", "#ff6b6b")

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
            self.add_chat_message("RÔLE", f"Vous êtes un {payload}!", color)
            
            # Mise à jour de la description du rôle
            role_descriptions = {
                "villager": "Vous êtes un simple villageois. Votre but est de découvrir qui sont les loups-garous et de les éliminer lors des votes du village.",
                "werewolf": "Vous êtes un loup-garou! Chaque nuit, vous pouvez voter pour dévorer un villageois. Durant le jour, cachez votre identité.",
                "voyante": "Vous êtes la voyante. Chaque nuit, vous pouvez découvrir la véritable identité d'un joueur de votre choix.",
                "sorcière": "Vous êtes la sorcière. Vous possédez deux potions: l'une pour sauver une victime, l'autre pour éliminer un joueur.",
                "chasseur": "Vous êtes le chasseur. Si vous êtes éliminé, vous pouvez immédiatement tirer sur un autre joueur qui mourra aussi."
            }
            self.role_desc_label.setText(role_descriptions.get(payload, "Rôle inconnu"))

        elif msg_type == "STATE":
            self.game_state = payload
            
            # Traitement spécial pour certains états
            if payload == "villagers_win":
                self.state_label.setText("Victoire des Villageois")
                self.add_chat_message("VICTOIRE", "🎉 Les Villageois ont gagné!", "#2ed573")
                QMessageBox.information(self, "Fin de partie", "Les villageois ont gagné! Les loups-garous ont été éliminés.")
                
            elif payload == "werewolves_win":
                self.state_label.setText("Victoire des Loups-garous")
                self.add_chat_message("VICTOIRE", "🐺 Les Loups-garous ont gagné!", "#ff3838")
                QMessageBox.information(self, "Fin de partie", "Les loups-garous ont gagné! Ils ont dévoré tous les villageois.")
                
            elif payload == "day":
                self.state_label.setText("Jour")
                self.add_chat_message("ÉTAT", "☀️ Le jour se lève! Débattez et votez pour éliminer un suspect.", color)
                # Mettre à jour l'interface pour le jour (en option)
                # self.setStyleSheet("background-color: #87CEEB;") 
                
            elif payload == "night":
                self.state_label.setText("Nuit")
                self.add_chat_message("ÉTAT", "🌙 La nuit tombe... Les rôles spéciaux agissent dans l'ombre.", color)
                # Mettre à jour l'interface pour la nuit (en option)
                # self.setStyleSheet("background-color: #2C3E50;")
                
            else:
                self.state_label.setText(payload)
                self.add_chat_message("ÉTAT", payload, color)
                
            # Mise à jour des contrôles uniquement
            # Les popups sont déclenchés par les messages spécifiques du serveur
            self.update_buttons_visibility()

        elif msg_type == "WITCH_ACTION":
            self.show_witch_dialog()
            
        elif msg_type == "SEER_ACTION":
            self.show_seer_dialog()
            
        elif msg_type == "WEREWOLF_ACTION":
            self.show_night_vote_dialog()

        elif msg_type == "SEER_RESULT":
            # Format: nom_joueur:role
            try:
                name, role = payload.split(":")
                self.add_chat_message("VOYANTE", f"💫 Vous avez découvert que {name} est un {role}!", "#9c88ff")
                # Afficher un message plus visible
                QMessageBox.information(self, "Vision de la Voyante", f"Vous avez découvert que {name} est un {role}!")
            except Exception as e:
                print(f"Erreur traitement SEER_RESULT: {e}, payload: {payload}")
                self.add_chat_message("VOYANTE", f"Résultat: {payload}", "#9c88ff")

        elif msg_type == "HUNTER_SHOOT":
            self.show_hunter_dialog()
            
        elif msg_type == "JOIN":
            # Ajouter le joueur à la liste
            if payload not in [self.players_list_widget.item(i).text() for i in range(self.players_list_widget.count())]:
                self.players_list_widget.addItem(payload)
                self.add_chat_message("JOUEUR", f"👋 {payload} a rejoint la partie!", "#3742fa")
                
        elif msg_type == "ROLE_DISTRIBUTION":
            # Afficher la répartition des rôles
            self.add_chat_message("INFORMATION", f"📊 Répartition des rôles dans cette partie: {payload}", "#3742fa")
            # Afficher une fenêtre pop-up pour mettre en évidence cette information
            QMessageBox.information(self, "Répartition des rôles", 
                                    f"Voici la répartition des rôles dans cette partie:\n\n{payload}")
                
        elif msg_type == "KILL":
            # Marquer le joueur comme mort dans la liste
            self.add_chat_message("MORT", f"☠️ {payload} a été éliminé!", "#ff3838")
            
            # Actualiser l'état du joueur dans la liste (en italique ou barré)
            for i in range(self.players_list_widget.count()):
                if self.players_list_widget.item(i).text() == payload or self.players_list_widget.item(i).text().startswith(payload + " "):
                    item = self.players_list_widget.item(i)
                    # Ajouter un indicateur clair au texte
                    current_text = item.text()
                    if " (mort)" not in current_text:
                        item.setText(f"{payload} (mort)")
                    
                    # Appliquer aussi un style visuel
                    font = item.font()
                    font.setStrikeOut(True)
                    font.setItalic(True)
                    item.setFont(font)
                    item.setForeground(QColor("#ff3838"))
                    break
                    
            # Vérifier si c'est nous qui sommes morts
            if payload == self.username:
                if self.player_role == "chasseur":
                    QMessageBox.information(self, "Vous êtes mort", 
                                          "Vous avez été éliminé! En tant que chasseur, vous pouvez encore tirer sur quelqu'un.")
                else:
                    QMessageBox.information(self, "Vous êtes mort", 
                                          "Vous avez été éliminé! Vous ne pouvez plus voter ni parler, mais vous pouvez continuer à observer la partie.")
                
        elif msg_type == "MSG":
            # Traiter les messages de chat
            self.add_chat_message("MSG", payload, color)
            
        elif msg_type == "NIGHT_MSG":
            # Messages des loups-garous pendant la nuit
            if self.player_role == "werewolf":
                self.add_chat_message("LOUPS", f"🐺 {payload}", "#ff6b9d")
            
        else:
            self.add_chat_message(msg_type, payload, color)

    def update_buttons_visibility(self):
        is_alive = True  # Amélioration possible plus tard
        self.vote_btn.setVisible(self.game_state == "day" and is_alive)
        self.night_vote_btn.setVisible(self.game_state == "night" and self.player_role == "werewolf" and is_alive)

    def check_auto_popups(self):
        """Affiche automatiquement les popups appropriés selon l'état du jeu et le rôle"""
        # Les popups sont maintenant gérés directement par les signaux du serveur
        # et ne s'affichent que lorsqu'on reçoit les signaux spécifiques
        # SEER_ACTION, WITCH_ACTION, HUNTER_SHOOT, etc.
        pass

    def create_connection_panel(self, parent_layout):
        conn_frame = QFrame()
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
        
        # Ajout des boutons au layout
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
        
        # Ajout des widgets au layout
        player_layout.addWidget(self.players_list_widget)
        player_layout.addWidget(player_info_label)
        
        # Ajout du groupe de joueurs au layout principal
        info_layout.addWidget(player_box)
        
        # Ajout final au layout parent
        parent_layout.addWidget(info_group)

    def create_chat_panel(self, parent_layout):
        # Zone principale de chat avec onglets
        chat_tabs = QTabWidget()
        chat_tabs.setStyleSheet("QTabBar::tab:selected {background-color: #3742fa; color: white; font-weight: bold;}")
        
        # Onglet de chat général
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        # En-tête avec titre et boutons d'action
        chat_header = QHBoxLayout()
        chat_title = QLabel("💬 Messages du jeu")
        chat_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        chat_header.addWidget(chat_title)
        
        # Boutons d'action rapide pour le chat
        chat_header_btn_layout = QHBoxLayout()
        chat_header_btn_layout.addStretch()
        
        help_btn = QPushButton("❓ Aide")
        help_btn.setMaximumWidth(60)
        help_btn.clicked.connect(self.show_help)
        help_btn.setStyleSheet("background-color: #54a0ff;")
        
        chat_header_btn_layout.addWidget(help_btn)
        chat_header.addLayout(chat_header_btn_layout)
        chat_layout.addLayout(chat_header)
        
        # Zone d'affichage du chat avec formatage HTML
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
        self.chat_display.setAcceptRichText(True)
        self.chat_display.document().setDefaultStyleSheet("a {color: #54a0ff;}")
        chat_layout.addWidget(self.chat_display)
        
        # Zone d'entrée pour le chat avec boutons d'action
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Tapez votre message ou une commande /...")
        self.message_input.returnPressed.connect(self.send_chat_message)
        self.message_input.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px; padding: 5px;")
        
        # Boutons d'action rapide selon le contexte
        self.vote_btn = QPushButton("☀️ Vote")
        self.vote_btn.setToolTip("Vote du jour (éliminer un joueur)")
        self.vote_btn.clicked.connect(self.show_vote_dialog)
        self.vote_btn.setStyleSheet("background-color: #ffa502;")
        
        self.night_vote_btn = QPushButton("🌙 Action nocturne")
        self.night_vote_btn.setToolTip("Action spéciale de nuit selon votre rôle")
        self.night_vote_btn.clicked.connect(self.show_night_action_dialog)
        self.night_vote_btn.setStyleSheet("background-color: #9c88ff;")
        
        send_btn = QPushButton("Envoyer")
        send_btn.clicked.connect(self.send_chat_message)
        send_btn.setStyleSheet("background-color: #2ed573;")
        
        # Ajout des composants au layout
        input_layout.addWidget(self.message_input, 7)
        input_layout.addWidget(self.vote_btn, 1)
        input_layout.addWidget(self.night_vote_btn, 1)
        input_layout.addWidget(send_btn, 1)
        
        chat_layout.addLayout(input_layout)
        
        # Ajout de l'onglet principal
        chat_tabs.addTab(chat_widget, "Chat général")
        
        # Onglet journal avec historique des événements
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        log_title = QLabel("📜 Journal des événements")
        log_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        log_layout.addWidget(log_title)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
        log_layout.addWidget(self.log_display)
        
        # Filtres pour le journal
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrer:"))
        
        filter_all = QPushButton("Tout")
        filter_all.clicked.connect(lambda: self.filter_log("all"))
        filter_layout.addWidget(filter_all)
        
        filter_votes = QPushButton("Votes")
        filter_votes.clicked.connect(lambda: self.filter_log("vote"))
        filter_layout.addWidget(filter_votes)
        
        filter_deaths = QPushButton("Morts")
        filter_deaths.clicked.connect(lambda: self.filter_log("death"))
        filter_layout.addWidget(filter_deaths)
        
        log_layout.addLayout(filter_layout)
        
        # Ajout de l'onglet journal
        chat_tabs.addTab(log_widget, "Journal")
        
        # Onglet règles du jeu pour référence rapide
        rules_widget = QWidget()
        rules_layout = QVBoxLayout(rules_widget)
        
        rules_title = QLabel("📋 Règles du jeu")
        rules_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        rules_layout.addWidget(rules_title)
        
        rules_text = QTextEdit()
        rules_text.setReadOnly(True)
        rules_text.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
        rules_text.setHtml("""
            <h3>Rôles du jeu</h3>
            <p><b>🐺 Loup-garou</b>: Dévore un villageois chaque nuit</p>
            <p><b>👁️ Voyante</b>: Peut découvrir l'identité d'un joueur chaque nuit</p>
            <p><b>🧙‍♀️ Sorcière</b>: Peut sauver ou tuer un joueur avec ses potions</p>
            <p><b>🔫 Chasseur</b>: À sa mort, peut emmener un autre joueur avec lui</p>
            <p><b>👨‍🌾 Villageois</b>: Doit découvrir qui sont les loups-garous</p>
            
            <h3>Distribution optimale des rôles</h3>
            <p>La répartition des rôles est automatiquement optimisée selon le nombre de joueurs:</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse; color: #f1f2f6; width: 100%;">
                <tr style="background-color: #3742fa;">
                    <th>Joueurs</th>
                    <th>🐺 Loups-garous</th>
                    <th>👁️ Voyante</th>
                    <th>🧙‍♀️ Sorcière</th>
                    <th>🔫 Chasseur</th>
                    <th>👨‍🌾 Villageois</th>
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
                    <td align="center">Reste</td>
                </tr>
            </table>
            
            <h3>Déroulement</h3>
            <p><b>Jour</b>: Les villageois débattent et votent pour éliminer un suspect</p>
            <p><b>Nuit</b>: Les loups-garous choisissent une victime, puis les rôles spéciaux agissent</p>
            
            <h3>Victoire</h3>
            <p>Les <b>villageois</b> gagnent s'ils éliminent tous les loups-garous</p>
            <p>Les <b>loups-garous</b> gagnent s'ils sont en nombre égal ou supérieur aux villageois</p>
        """)
        rules_layout.addWidget(rules_text)
        
        # Ajout de l'onglet règles
        chat_tabs.addTab(rules_widget, "Règles")
        
        # Ajout des onglets au layout principal
        parent_layout.addWidget(chat_tabs, 1)

    # La fonction create_actions_panel n'est plus nécessaire puisqu'on a intégré
    # les actions dans le panel d'information et dans la zone de chat

    def create_command_panel(self, parent_layout):
    
        cmd_group = QGroupBox("Terminal de commandes")
        cmd_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
        cmd_group_layout = QVBoxLayout(cmd_group)
        
        # Affichage des commandes précédentes avec design amélioré
        history_label = QLabel("Historique des commandes:")
        history_label.setStyleSheet("font-weight: bold; color: #dfe4ea;")
        cmd_group_layout.addWidget(history_label)
        
        self.cmd_history = QTextEdit()
        self.cmd_history.setReadOnly(True)
        self.cmd_history.setMaximumHeight(100)
        self.cmd_history.setStyleSheet("background-color: #2f3542; color: #a4b0be; border-radius: 5px; font-family: 'Consolas', monospace;")
        self.cmd_history.setPlaceholderText("Les commandes exécutées s'afficheront ici...")
        cmd_group_layout.addWidget(self.cmd_history)
        
        # Zone de saisie des commandes avec style console
        cmd_input_layout = QHBoxLayout()
        prompt_label = QLabel(">")
        prompt_label.setStyleSheet("color: #2ed573; font-weight: bold; font-size: 14px; font-family: 'Consolas', monospace;")
        cmd_input_layout.addWidget(prompt_label)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("/vote <joueur>, /nvote <joueur>, /start, /restart, /help")
        self.command_input.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px; padding: 5px; font-family: 'Consolas', monospace;")
        self.command_input.returnPressed.connect(self.process_command)
        cmd_input_layout.addWidget(self.command_input)
        
        # Bouton d'exécution
        exec_btn = QPushButton("▶️ Exécuter")
        exec_btn.clicked.connect(self.process_command)
        exec_btn.setStyleSheet("background-color: #2ed573; font-weight: bold;")
        cmd_input_layout.addWidget(exec_btn)
        
        cmd_group_layout.addLayout(cmd_input_layout)
        
        # Layout de commandes rapides en grid pour plus de commandes
        command_grid_layout = QGridLayout()
        
        # Commandes de jeu
        cmd_start = QPushButton("/start")
        cmd_start.clicked.connect(lambda: self.execute_quick_command("/start"))
        cmd_start.setStyleSheet("background-color: #2ed573;")
        command_grid_layout.addWidget(cmd_start, 0, 0)
        
        cmd_restart = QPushButton("/restart")
        cmd_restart.clicked.connect(lambda: self.execute_quick_command("/restart"))
        cmd_restart.setStyleSheet("background-color: #ff7f50;")
        command_grid_layout.addWidget(cmd_restart, 0, 1)
        
        # Commandes de vote
        cmd_vote = QPushButton("/vote")
        cmd_vote.clicked.connect(lambda: self.show_vote_dialog())
        cmd_vote.setStyleSheet("background-color: #ffa502;")
        command_grid_layout.addWidget(cmd_vote, 0, 2)
        
        cmd_nvote = QPushButton("/nvote")
        cmd_nvote.clicked.connect(lambda: self.show_night_vote_dialog())
        cmd_nvote.setStyleSheet("background-color: #9c88ff;")
        command_grid_layout.addWidget(cmd_nvote, 0, 3)
        
        # Commandes de message nocturne
        cmd_nmsg = QPushButton("/nmsg")
        cmd_nmsg.clicked.connect(lambda: self.command_input.setText("/nmsg "))
        cmd_nmsg.setStyleSheet("background-color: #ff6b9d;")
        command_grid_layout.addWidget(cmd_nmsg, 1, 0)
        
        # Commandes pour les rôles spéciaux
        cmd_seer = QPushButton("Voyante")
        cmd_seer.clicked.connect(lambda: self.show_seer_dialog())
        cmd_seer.setStyleSheet("background-color: #9c88ff;")
        command_grid_layout.addWidget(cmd_seer, 1, 1)
        
        cmd_witch = QPushButton("Sorcière")
        cmd_witch.clicked.connect(lambda: self.show_witch_dialog())
        cmd_witch.setStyleSheet("background-color: #ff6348;")
        command_grid_layout.addWidget(cmd_witch, 1, 2)
        
        cmd_help = QPushButton("/help")
        cmd_help.clicked.connect(lambda: self.execute_quick_command("/help"))
        cmd_help.setStyleSheet("background-color: #54a0ff;")
        command_grid_layout.addWidget(cmd_help, 1, 3)
        
        # Ajout du layout de commandes rapides
        cmd_group_layout.addLayout(command_grid_layout)
        
        # Ajouter la liste des commandes disponibles
        help_layout = QHBoxLayout()
        help_layout.addWidget(QLabel("💡 Commandes:"))
        help_text = QLabel("/vote, /nvote, /start, /restart, /nmsg, /help")
        help_text.setStyleSheet("font-style: italic; color: #a4b0be;")
        help_layout.addWidget(help_text)
        help_layout.addStretch()
        cmd_group_layout.addLayout(help_layout)
        
        # Ajouter le groupe de commandes au layout principal
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
        
        # Actions en fonction de l'état du jeu et du rôle
        if self.game_state == "day":
            vote_action = menu.addAction(f"🗳️ Voter contre {player_name}")
            vote_action.triggered.connect(lambda: self.vote_for_player(player_name))
            
        elif self.game_state == "night":
            if self.player_role == "werewolf":
                night_vote_action = menu.addAction(f"🐺 Attaquer {player_name}")
                night_vote_action.triggered.connect(lambda: self.night_vote_for_player(player_name))
                
            elif self.player_role == "voyante":
                see_action = menu.addAction(f"👁️ Examiner {player_name}")
                see_action.triggered.connect(lambda: self.seer_examine_player(player_name))
                
            elif self.player_role == "sorcière":
                kill_action = menu.addAction(f"☠️ Empoisonner {player_name}")
                kill_action.triggered.connect(lambda: self.witch_kill_player(player_name))
                
            elif self.player_role == "chasseur":
                shoot_action = menu.addAction(f"🔫 Tirer sur {player_name}")
                shoot_action.triggered.connect(lambda: self.hunter_shoot_player(player_name))
            
        # Action de message privé (fonctionnalité à implémenter plus tard)
        whisper_action = menu.addAction(f"💬 Message privé à {player_name}")
        whisper_action.triggered.connect(lambda: self.whisper_to_player(player_name))
        
        # Afficher le menu
        menu.exec_(self.players_list_widget.mapToGlobal(position))
    
    def vote_for_player(self, player_name):
        reply = QMessageBox.question(self, "Confirmation de vote", 
                                     f"Voulez-vous voter contre {player_name}?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.network_worker.send_message(MessageType.VOTE.value, player_name)
            self.add_chat_message("VOTE", f"Vous avez voté contre {player_name}", "#ffa502")
            self.add_to_command_history(f"/vote {player_name}")
    
    def night_vote_for_player(self, player_name):
        reply = QMessageBox.question(self, "Confirmation d'attaque", 
                                     f"Voulez-vous attaquer {player_name} cette nuit?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, player_name)
            self.add_chat_message("VOTE NOCTURNE", f"Vous avez choisi d'attaquer {player_name}", "#ff6b9d")
            self.add_to_command_history(f"/nvote {player_name}")
    
    def seer_examine_player(self, player_name):
        self.network_worker.send_message(MessageType.SEER_ACTION.value, player_name)
        self.add_chat_message("VOYANTE", f"Vous examinez {player_name}...", "#9c88ff")
        # On attend la réponse du serveur avec SEER_RESULT - voir handle_server_message
    
    def witch_kill_player(self, player_name):
        self.network_worker.send_message(MessageType.NIGHT_VOTE.value, f"witch_kill:{player_name}")
        self.add_chat_message("SORCIÈRE", f"Vous avez empoisonné {player_name}", "#ff6348")
    
    def hunter_shoot_player(self, player_name):
        self.network_worker.send_message(MessageType.HUNTER_SHOOT.value, player_name)
        self.add_chat_message("CHASSEUR", f"Vous avez tiré sur {player_name}", "#ff9f43")
    
    def whisper_to_player(self, player_name):
        # Fonctionnalité à implémenter plus tard
        self.add_chat_message("SYSTÈME", f"Les messages privés ne sont pas encore implémentés", "#ff6b6b")
    
    def show_vote_dialog(self):
        if not self.players_list_widget.count():
            QMessageBox.warning(self, "Vote impossible", "Aucun joueur disponible pour le vote.")
            return
            
        players = []
        for i in range(self.players_list_widget.count()):
            players.append(self.players_list_widget.item(i).text())
            
        target, ok = QInputDialog.getItem(self, "Vote", "Choisissez un joueur à éliminer:", 
                                        players, 0, False)
        if ok and target:
            self.vote_for_player(target)

    def show_night_action_dialog(self):
        # Ce dialogue est déclenché manuellement par le bouton "Action nocturne" ou le menu
        # Mais normalement, les actions sont déclenchées automatiquement par les messages du serveur
        
        # Vérifier si c'est actuellement la nuit
        if self.game_state != "night":
            QMessageBox.information(self, "Action nocturne", 
                                   "Les actions spéciales ne peuvent être effectuées que durant la nuit.")
            return
        
        # Afficher le dialogue approprié selon le rôle
        if self.player_role == "werewolf":
            self.show_night_vote_dialog()
        elif self.player_role == "voyante":
            self.show_seer_dialog()
        elif self.player_role == "sorcière":
            self.show_witch_dialog()
        elif self.player_role == "chasseur":
            self.show_hunter_dialog()
        else:
            QMessageBox.information(self, "Action nocturne", 
                                   "Vous n'avez pas d'action spéciale durant la nuit. Attendez que les autres joueurs finissent leurs actions.")

    def show_night_vote_dialog(self):
        # Récupérer la liste des joueurs vivants depuis le widget de liste
        players = []
        
        # Debug info
        print(f"DEBUG - Construire la liste des joueurs pour le vote de nuit")
        print(f"DEBUG - Nombre total de joueurs: {self.players_list_widget.count()}")
        
        # Exclure le joueur lui-même et les joueurs marqués comme morts
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
        
        # Vérifier si la liste n'est pas vide
        if not players:
            print("DEBUG - Liste des joueurs vide pour le vote nocturne!")
            QMessageBox.warning(self, "Vote impossible", "Aucun joueur disponible pour le vote.")
            
            # Afficher tous les joueurs pour le débogage
            all_players = [self.players_list_widget.item(i).text() for i in range(self.players_list_widget.count())]
            print(f"DEBUG - Tous les joueurs: {all_players}")
            return
        
        print(f"DEBUG - Liste finale des joueurs pour le vote: {players}")
        target, ok = QInputDialog.getItem(self, "Vote Nocturne", 
                                       "Choisissez une victime pour cette nuit:", 
                                       players, 0, False)
        if ok and target:
            self.night_vote_for_player(target)
    
    def show_witch_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Actions de la Sorcière")
        layout = QVBoxLayout(dialog)
        
        # Image ou icône pour la sorcière
        witch_icon_label = QLabel()
        witch_icon = QPixmap("witch_icon.png") # Vous pouvez ajouter une image plus tard
        if not witch_icon.isNull():
            witch_icon_label.setPixmap(witch_icon.scaled(64, 64, Qt.KeepAspectRatio))
        else:
            witch_icon_label.setText("🧙‍♀️")
            witch_icon_label.setStyleSheet("font-size: 32px;")
        witch_icon_label.setAlignment(Qt.AlignHCenter)
        layout.addWidget(witch_icon_label)
        
        layout.addWidget(QLabel("Vous êtes la sorcière. Que souhaitez-vous faire?"))
        
        # Options de la sorcière
        no_action_btn = QPushButton("Ne rien faire")
        save_btn = QPushButton("Sauver la victime")
        kill_btn = QPushButton("Empoisonner un joueur")
        
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
            self.add_chat_message("SORCIÈRE", "Vous n'avez utilisé aucune potion", "#ff6348")
        elif action == "save":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_save")
            self.add_chat_message("SORCIÈRE", "Vous avez utilisé votre potion de vie pour sauver la victime", "#ff6348")
        dialog.accept()
    
    def witch_select_target(self, parent_dialog):
        parent_dialog.accept()
        
        # Récupérer la liste des joueurs vivants
        players = []
        for i in range(self.players_list_widget.count()):
            item = self.players_list_widget.item(i)
            if item and not "(mort)" in item.text():
                players.append(item.text().split(" (")[0])  # Ne garder que le nom sans le rôle
        
        # Vérifier si la liste n'est pas vide
        if not players:
            QMessageBox.warning(self, "Action impossible", "Aucun joueur disponible à empoisonner.")
            return
            
        target, ok = QInputDialog.getItem(self, "Empoisonnement", 
                                       "Choisissez un joueur à empoisonner:", 
                                       players, 0, False)
        if ok and target:
            self.witch_kill_player(target)
    
    def show_seer_dialog(self):
        # Récupérer la liste des joueurs vivants
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
        
        # Si aucun joueur n'est trouvé, essayer une recherche moins stricte
        if not players:
            print("DEBUG - Aucun joueur trouvé, essayons une méthode alternative")
            # Méthode alternative: inclure tous les joueurs sauf soi-même
            for i in range(self.players_list_widget.count()):
                item = self.players_list_widget.item(i)
                if item and item.text() != self.username:
                    players.append(item.text())
                    print(f"DEBUG - Ajouté (méthode alt): '{item.text()}'")
        
        # Vérifier si la liste n'est pas vide
        if not players:
            print("DEBUG - Liste des joueurs vide pour la voyante!")
            QMessageBox.warning(self, "Action impossible", "Aucun joueur disponible à examiner.")
            return
            
        print(f"DEBUG - Liste finale pour la voyante: {players}")
        target, ok = QInputDialog.getItem(self, "Vision de la Voyante", 
                                       "Choisissez un joueur à examiner:", 
                                       players, 0, False)
        if ok and target:
            self.seer_examine_player(target)
    
    def show_hunter_dialog(self):
        # Récupérer la liste des joueurs vivants
        players = []
        for i in range(self.players_list_widget.count()):
            item = self.players_list_widget.item(i)
            if item and not "(mort)" in item.text():
                players.append(item.text().split(" (")[0])  # Ne garder que le nom sans le rôle
        
        # Vérifier si la liste n'est pas vide
        if not players:
            QMessageBox.warning(self, "Action impossible", "Aucun joueur disponible sur qui tirer.")
            return
            
        target, ok = QInputDialog.getItem(self, "Tir du Chasseur", 
                                       "Choisissez un joueur sur qui tirer:", 
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
            self.add_chat_message("SORCIÈRE", "Vous avez utilisé votre potion de vie pour sauver la victime", "#ff6348")
        elif command == "/witch_none":
            self.network_worker.send_message(MessageType.NIGHT_VOTE.value, "witch_none")
            self.add_chat_message("SORCIÈRE", "Vous n'avez utilisé aucune potion", "#ff6348")
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
            "Commandes générales:\n"
            "/vote <joueur> - Voter contre un joueur (jour)\n"
            "/nvote <joueur> - Voter contre un joueur (nuit, loup-garou)\n"
            "/start - Démarrer la partie\n"
            "/restart - Redémarrer la partie\n\n"
            
            "Commandes de rôle:\n"
            "/seer <joueur> - Examiner un joueur (voyante)\n"
            "/witch_kill <joueur> - Empoisonner un joueur (sorcière)\n"
            "/witch_save - Sauver la victime des loups (sorcière)\n"
            "/witch_none - Ne rien faire (sorcière)\n"
            "/hunter <joueur> - Tirer sur un joueur (chasseur)\n\n"
            
            "Autres commandes:\n"
            "/nmsg <message> - Envoyer un message de nuit\n"
            "/whisper <joueur> <message> - Envoyer un message privé à un joueur\n"
            "/help - Afficher cette aide"
        )
        QMessageBox.information(self, "Aide", help_text)

    def set_game_controls_enabled(self, enabled):
        self.start_btn.setEnabled(enabled)
        self.vote_btn.setEnabled(enabled)
        self.night_vote_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)
        self.message_input.setEnabled(enabled)
        self.command_input.setEnabled(enabled)

    def add_chat_message(self, msg_type, message, color="#ffffff"):
        """Ajoute un message au chat avec formatage HTML"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.chat_display.append(f'<span style="color: #a4b0be;">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">[{msg_type}]</span> {message}')
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
        
    def add_to_log(self, msg_type, message, color="#ffffff"):
        """Ajoute une entrée au journal des événements"""
        timestamp = QDateTime.currentDateTime().toString("dd/MM hh:mm:ss")
        self.log_display.append(f'<span style="color: #a4b0be;">[{timestamp}]</span> <span style="color: {color}; font-weight: bold;">[{msg_type}]</span> {message}')
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())
    
    def add_to_command_history(self, command):
        """Ajoute une commande à l'historique du terminal"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.cmd_history.append(f'<span style="color: #a4b0be;">[{timestamp}]</span> <span style="color: #2ed573;">{command}</span>')
        self.cmd_history.verticalScrollBar().setValue(self.cmd_history.verticalScrollBar().maximum())
    
    def filter_log(self, filter_type):
        """Filtre les entrées du journal selon le type"""
        # Cette fonctionnalité pourrait être implémentée ultérieurement
        pass
    
    def update_buttons_visibility(self):
        """Met à jour la visibilité des boutons en fonction de l'état du jeu et du rôle"""
        is_alive = True  # À améliorer plus tard avec un statut réel
        
        # Boutons de vote du jour
        self.vote_btn.setVisible(self.game_state == "day" and is_alive)
        
        # Boutons d'action de nuit selon le rôle
        self.night_vote_btn.setVisible(self.game_state == "night" and is_alive and 
                                       self.player_role in ["werewolf", "voyante", "sorcière", "chasseur"])
        
        # Mise à jour du label de rôle avec une icône
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
        """Affiche automatiquement les popups appropriés selon l'état du jeu et le rôle"""
        # Les popups sont maintenant gérés directement par les signaux du serveur
        # et ne s'affichent que lorsqu'on reçoit les signaux spécifiques
        # SEER_ACTION, WITCH_ACTION, HUNTER_SHOOT, etc.
        pass
    def closeEvent(self, event):
        """Gère la fermeture propre de l'application"""
        reply = QMessageBox.question(self, 'Confirmation', 
                                     'Êtes-vous sûr de vouloir quitter?',
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
