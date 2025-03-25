#!/usr/bin/env python3
"""
Standalone status overlay for SuperCode application.
This runs completely independently of the Rumps menu bar app.
"""

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QBrush, QFont
import threading
import time
import math
import numpy as np
import sys
import os
import json
import argparse
from typing import List, Optional, Callable

class StatusOverlay(QWidget):
    """
    Standalone status overlay that shows:
    - Status visualization
    - Current status text (Listening, Recording, Transcribing, Executing)
    """
    
    # Status constants
    STATUS_IDLE = "Listening for 'activate'"
    STATUS_RECORDING = "Recording..."
    STATUS_TRANSCRIBING = "Transcribing..."
    STATUS_EXECUTING = "Executing command"
    
    # Colors
    COLOR_BG = QColor(30, 30, 30)  # Dark background
    COLOR_TEXT = QColor(255, 255, 255)  # White text
    COLOR_STATUS = QColor(76, 175, 80)  # Green
    COLOR_RECORDING = QColor(244, 67, 54)  # Red
    COLOR_WAVE_ACTIVE = QColor(33, 150, 243)  # Blue
    COLOR_WAVE_INACTIVE = QColor(85, 85, 85)  # Dark gray
    
    def __init__(self, size=200, status_file=None, message_file=None):
        """
        Initialize the status overlay.
        """
        super().__init__()
        
        # Configuration
        self.size_val = size
        self.opacity = 0.9
        
        # Communication files
        self.status_file = status_file
        self.message_file = message_file
        self.last_status_modified = 0
        
        # State variables
        self.current_status = self.STATUS_IDLE
        self.additional_info = ""
        self.is_recording = False
        self.animation_frame = 0
        
        # Application state
        self.running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        
        # Status check timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status_file)
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Status Overlay")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(self.size_val, self.size_val)
        self.setMaximumSize(self.size_val, self.size_val)
        
        # Add red border for visibility
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: 3px solid #FF0000;
                border-radius: 10px;
            }
        """)
        
        # Set position to top-right
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.size_val - 20, 20)
        
        # Show and activate
        self.setWindowOpacity(self.opacity)
    
    def start(self):
        """Start the overlay window and status check timer"""
        if self.running:
            return
            
        self.running = True
        self.show()
        self.raise_()
        self.activateWindow()
        self.timer.start(50)  # Update every 50ms
        
        # Start status check timer if we have a status file
        if self.status_file:
            self.last_status_modified = os.path.getmtime(self.status_file)
            self.status_timer.start(500)  # Check status file every 500ms
    
    def check_status_file(self):
        """Check the status file for updates"""
        if not self.status_file:
            return
            
        try:
            current_modified = os.path.getmtime(self.status_file)
            if current_modified > self.last_status_modified:
                # File has been modified, read the status
                with open(self.status_file, 'r') as f:
                    data = json.loads(f.read())
                    status = data.get("status", self.STATUS_IDLE)
                    info = data.get("info", "")
                    
                    # Update overlay status
                    self.current_status = status
                    self.additional_info = info
                    self.is_recording = status == self.STATUS_RECORDING
                    self.update()
                    
                    print(f"Status updated: {status} - {info}")
                
                # Update last modified time
                self.last_status_modified = current_modified
        except Exception as e:
            print(f"Error checking status file: {e}")
    
    def update_animation(self):
        """Update animation state and redraw"""
        if not self.running:
            return
            
        self.animation_frame += 1
        self.update()
    
    def paintEvent(self, event):
        """Paint the overlay content"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw rounded rectangle background
        path = QPainterPath()
        rect = QRectF(0, 0, self.width(), self.height())
        path.addRoundedRect(rect, 10, 10)
        
        painter.fillPath(path, self.COLOR_BG)
        
        # Draw status text
        status_color = self.COLOR_STATUS
        if self.current_status == self.STATUS_RECORDING:
            status_color = self.COLOR_RECORDING
            
        painter.setPen(status_color)
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(0, 20, self.width(), 40), Qt.AlignCenter, self.current_status)
        
        # Draw additional info
        if self.additional_info:
            painter.setPen(self.COLOR_TEXT)
            painter.setFont(QFont("Arial", 10))
            text_rect = QRectF(10, 60, self.width() - 20, 40)
            painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self.additional_info)
        
        # Draw close button
        close_size = 20
        painter.fillRect(self.width() - close_size, 0, close_size, close_size, QColor(51, 51, 51))
        painter.setPen(self.COLOR_TEXT)
        painter.setFont(QFont("Arial", 14))
        painter.drawText(QRectF(self.width() - close_size, 0, close_size, close_size), Qt.AlignCenter, "×")
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        # Check if click is on close button
        close_size = 20
        if event.x() > self.width() - close_size and event.y() < close_size:
            # Send a close event message via file
            self.send_close_signal()
            return
        
        # Start dragging
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging"""
        if self.dragging and event.buttons() & Qt.LeftButton:
            # Move the window
            self.move(self.mapToGlobal(event.pos() - self.offset))
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            
    def send_close_signal(self):
        """Send a signal that the close button was clicked"""
        print("Close button clicked")
        
        # Write close message to file if we have one
        if self.message_file:
            try:
                with open(self.message_file, 'w') as f:
                    f.write(json.dumps({"message": "CLOSE"}))
                print("Wrote CLOSE message to file")
            except Exception as e:
                print(f"Error writing close message: {e}")
        
        # Exit this process
        QApplication.quit()
    
    def update_status(self, status, additional_info=""):
        """
        Update the current status displayed in the overlay.
        """
        self.current_status = status
        self.additional_info = additional_info
        
        # Update recording state based on status
        self.is_recording = status == self.STATUS_RECORDING
        
        # Trigger update if window is visible
        if self.isVisible():
            self.update()

def main():
    """Run the standalone overlay"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Standalone status overlay")
    parser.add_argument("--status-file", help="Path to status file for communication")
    parser.add_argument("--message-file", help="Path to message file for sending messages back")
    parser.add_argument("--size", type=int, default=180, help="Size of the overlay window")
    args = parser.parse_args()
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create overlay with status file if provided
    overlay = StatusOverlay(
        size=args.size,
        status_file=args.status_file,
        message_file=args.message_file
    )
    overlay.start()
    
    print("Overlay started. It should be visible in the top-right corner.")
    print(f"Using status file: {args.status_file}")
    print(f"Using message file: {args.message_file}")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 