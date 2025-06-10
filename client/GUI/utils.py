from PyQt5.QtWidgets import QTextEdit, QMenu, QMessageBox, QInputDialog
from PyQt5.QtCore import QDateTime

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
    """Filter log entries by type"""
    # This feature could be implemented later
    pass

def show_help(self):
    """Show help information dialog"""
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

def execute_quick_command(self, cmd):
    """Execute a command by setting it in the command input and processing it"""
    self.command_input.setText(cmd)
    # Appel à process_command() qui est défini dans main_window.py
    from .main_window import WerewolfClient
    WerewolfClient.process_command(self)