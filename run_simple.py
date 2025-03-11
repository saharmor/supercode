#!/usr/bin/env python3
"""
Simple runner script for SuperCursor command-line version.
This avoids the issues with the rumps module and provides a simpler interface.
"""

import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from super_cursor.simple_app import main

if __name__ == "__main__":
    main() 