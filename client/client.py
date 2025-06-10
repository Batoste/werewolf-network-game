#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Werewolf Game Client - Main Application Entry Point
This module serves as the main entry point for the Werewolf Game client application.
It imports the necessary components and starts the GUI.
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor

# Import the main window class from the GUI package
from GUI import WerewolfClient

def main():
    """
    Main function that initializes and starts the application.
    """
    # Create the application
    app = QApplication(sys.argv)
    
    # Set the application style to Fusion for a modern look
    app.setStyle("Fusion")
    
    # Create a custom dark color palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    # Create and show the main window
    client = WerewolfClient()
    client.show()
    
    # Start the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
