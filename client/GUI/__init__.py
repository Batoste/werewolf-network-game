"""
Werewolf Game Client GUI Package

This package contains the modular components of the Werewolf Game client GUI.
"""

# Import main components to make them accessible from GUI package
from .main_window import WerewolfClient
from .network_worker import NetworkWorker
from .panels import create_connection_panel, create_game_info_panel, create_chat_panel
from .dialogs import (show_vote_dialog, show_night_vote_dialog, show_night_action_dialog,
                     show_witch_dialog, witch_action, witch_select_target, 
                     show_seer_dialog, show_hunter_dialog)
from .actions import (vote_for_player, night_vote_for_player, seer_examine_player,
                     witch_kill_player, hunter_shoot_player, whisper_to_player,
                     show_player_context_menu)
from .utils import (add_chat_message, add_to_log, add_to_command_history,
                   filter_log, show_help, execute_quick_command)

# Make the main class available at package level
__all__ = ['WerewolfClient']
