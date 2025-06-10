from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

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
    info_group = QGroupBox("📋 Information")
    info_layout = QVBoxLayout(info_group)
    
    # Rôle et état du jeu dans un layout en grille pour plus de clarté
    status_layout = QGridLayout()
    status_layout.addWidget(QLabel("Role:"), 0, 0)
    self.role_label = QLabel("Unknown")
    self.role_label.setStyleSheet("font-weight: bold; color: #ff9f43; font-size: 14px;")
    status_layout.addWidget(self.role_label, 0, 1)
    
    status_layout.addWidget(QLabel("State:"), 1, 0)
    self.state_label = QLabel("Waiting")
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
    action_box = QGroupBox("Game Actions")
    action_layout = QVBoxLayout(action_box)
    
    self.start_btn = QPushButton("Game Start")
    self.start_btn.clicked.connect(self.start_game)
    self.start_btn.setStyleSheet("background-color: #2ed573; font-weight: bold;")
    
    self.restart_btn = QPushButton("Restart Game")
    self.restart_btn.clicked.connect(self.restart_game)
    self.restart_btn.setStyleSheet("background-color: #ff7f50; font-weight: bold;")
    
    # Add the buttons to the layout
    action_layout.addWidget(self.start_btn)
    action_layout.addWidget(self.restart_btn)
    info_layout.addWidget(action_box)

    # Liste des joueurs interactive
    player_box = QGroupBox("👥 Players connected")
    player_layout = QVBoxLayout(player_box)
    
    # Liste avec sélection et menu contextuel
    self.players_list_widget = QListWidget()
    self.players_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
    self.players_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
    
    # Importer la fonction show_player_context_menu du module actions
    from .actions import show_player_context_menu
    self.players_list_widget.customContextMenuRequested.connect(lambda pos: show_player_context_menu(self, pos))
    
    self.players_list_widget.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px;")
    
    # Instructions pour la liste des joueurs
    player_info_label = QLabel("Right-click on a player to see available actions.")
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
    chat_title = QLabel("💬 General Chat")
    chat_title.setStyleSheet("font-size: 14px; font-weight: bold;")
    chat_header.addWidget(chat_title)
    
    # Quick action buttons for chat
    chat_header_btn_layout = QHBoxLayout()
    chat_header_btn_layout.addStretch()
    
    help_btn = QPushButton("❓ Help")
    help_btn.setMaximumWidth(60)
    from .utils import show_help
    help_btn.clicked.connect(lambda: show_help(self))
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
    # Import et utilisation de la méthode send_chat_message de main_window
    from .main_window import WerewolfClient
    self.message_input.returnPressed.connect(lambda: WerewolfClient.send_chat_message(self))
    self.message_input.setStyleSheet("background-color: #2f3542; color: #f1f2f6; border-radius: 5px; padding: 5px;")
    
    # Contextual quick action buttons
    self.vote_btn = QPushButton("☀️ Vote")
    self.vote_btn.setToolTip("Day vote (eliminate a player)")
    # Import et utilisation de la fonction show_vote_dialog de dialogs.py
    from .dialogs import show_vote_dialog
    self.vote_btn.clicked.connect(lambda: show_vote_dialog(self))
    self.vote_btn.setStyleSheet("background-color: #ffa502;")
    
    self.night_vote_btn = QPushButton("🌙 Night action")
    self.night_vote_btn.setToolTip("Night special action according to your role")
    # Import et utilisation de la fonction show_night_action_dialog de dialogs.py
    from .dialogs import show_night_action_dialog
    self.night_vote_btn.clicked.connect(lambda: show_night_action_dialog(self))
    self.night_vote_btn.setStyleSheet("background-color: #9c88ff;")
    
    send_btn = QPushButton("Send")
    # Utilisation de la même fonction que pour le message_input
    send_btn.clicked.connect(lambda: WerewolfClient.send_chat_message(self))
    send_btn.setStyleSheet("background-color: #2ed573;")
    
    # Add components to the layout
    input_layout.addWidget(self.message_input, 7)
    input_layout.addWidget(self.vote_btn, 1)
    input_layout.addWidget(self.night_vote_btn, 1)
    input_layout.addWidget(send_btn, 1)
    
    chat_layout.addLayout(input_layout)
    
    # Add the main tab
    chat_tabs.addTab(chat_widget, "Chat")
    
    # Log tab with event history
    log_widget = QWidget()
    log_layout = QVBoxLayout(log_widget)
    
    log_title = QLabel("📜 Game Log")
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