from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from common.protocol import MessageType


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
        # Importer et utiliser la fonction vote_for_player du module actions
        from .actions import vote_for_player
        vote_for_player(self, target)

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
    elif self.player_role == "seer":
        self.show_seer_dialog()
    elif self.player_role == "witch":
        self.show_witch_dialog()
    elif self.player_role == "hunter":
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
            print(f"DEBUG - Player find: '{player_name}'")
            
            # Vérifier si c'est un joueur vivant qui n'est pas le joueur actuel
            if not "(mort)" in player_name and player_name != self.username:
                clean_name = player_name.split(" (")[0]  # Ne garder que le nom sans les annotations
                players.append(clean_name)
                print(f"DEBUG - Add list: '{clean_name}'")
            else:
                print(f"DEBUG - Exclude from list: '{player_name}'")
    
    # Check that the list is not empty
    if not players:
        print("DEBUG - List of player not able to vote!")
        QMessageBox.warning(self, "Unable to vote", "No players available for voting.")
        
        # Display all players for debugging
        all_players = [self.players_list_widget.item(i).text() for i in range(self.players_list_widget.count())]
        print(f"DEBUG - All player: {all_players}")
        return
    
    print(f"DEBUG - Final list of player: {players}")
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
        if item and not "(dead)" in item.text():
            players.append(item.text().split(" (")[0])  # Keep only the name without the role
    
    # Check that the list is not empty
    if not players:
        QMessageBox.warning(self, "Impossible action", "No player available to poison.")
        return
        
    target, ok = QInputDialog.getItem(self, "Poison",
                                    "Choose a player to poison:",
                                    players, 0, False)
    if ok and target:
        self.witch_kill_player(target)

def show_seer_dialog(self):
    # Retrieve the list of living players
    players = []
    
    print(f"DEBUG - Building the list of players for the seer")
    print(f"DEBUG - Total number of player : {self.players_list_widget.count()}")
    
    for i in range(self.players_list_widget.count()):
        item = self.players_list_widget.item(i)
        if item:
            player_name = item.text()
            print(f"DEBUG - Joueur find: '{player_name}'")
            
            # Vérifier si c'est un joueur vivant qui n'est pas le joueur actuel
            if not "(dead)" in player_name and player_name != self.username:
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
        if item and not "(dead)" in item.text():
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