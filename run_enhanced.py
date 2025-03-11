#!/usr/bin/env python3
"""
Enhanced runner script for SuperCursor with GUI.
This uses the enhanced version with all improvements and the GUI interface.
"""

import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from super_cursor.enhanced_mac_app import main

if __name__ == "__main__":
    main() 