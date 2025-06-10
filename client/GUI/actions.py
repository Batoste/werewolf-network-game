from PyQt5.QtWidgets import QInputDialog, QMessageBox, QMenu
from common.protocol import MessageType

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
                
            elif self.player_role == "seer":
                see_action = menu.addAction(f"👁️ Inspect {player_name}")
                see_action.triggered.connect(lambda: self.seer_examine_player(player_name))
                
            elif self.player_role == "witch":
                kill_action = menu.addAction(f"☠️ Poison {player_name}")
                kill_action.triggered.connect(lambda: self.witch_kill_player(player_name))
                
            elif self.player_role == "hunter":
                shoot_action = menu.addAction(f"🔫 Shoot {player_name}")
                shoot_action.triggered.connect(lambda: self.hunter_shoot_player(player_name))
            
        # Private message action (feature to implement later)
        whisper_action = menu.addAction(f"💬 Private message to {player_name}")
        whisper_action.triggered.connect(lambda: self.whisper_to_player(player_name))
        
        # Show the menu
        menu.exec_(self.players_list_widget.mapToGlobal(position))
    
def execute_quick_command(self, cmd):
    self.command_input.setText(cmd)
    self.process_command()