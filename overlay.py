#!/usr/bin/env python3
"""
Status overlay for SuperCode application.
Provides the visual interface for the overlay window.
"""

try:
    from PyQt5.QtWidgets import QApplication, QWidget
    from PyQt5.QtCore import Qt, QTimer, QRectF
    from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFont
except ImportError:
    print("\n\033[1;31mError: PyQt5 module not found.\033[0m")
    print("\033[1;33mPlease install it by running: pip install PyQt5>=5.15.6\033[0m")
    print("\033[1;33mOr rerun the install script: ./install_and_run.sh\033[0m\n")
    import sys
    sys.exit(1)

import sys
import os
import json
import argparse
import math
import traceback
from datetime import datetime

from overlay_manager import OverlayManager

class StatusOverlay(QWidget):
    """
    Status overlay that shows:
    - Status visualization
    - Current status text (Listening, Recording, Transcribing, Executing)
    """
    
    # Colors
    COLOR_BG = QColor("#efe0c2")  # Beige background
    COLOR_TEXT = QColor(70, 70, 70)  # Dark gray text
    COLOR_STATUS = QColor(76, 175, 80)  # Green
    COLOR_RECORDING = QColor(76, 175, 80)  # Green (changed from red)
    COLOR_CLOSE = QColor(150, 150, 150)  # Gray for close button
    COLOR_IDLE = QColor(33, 150, 243)  # Blue for idle state
    COLOR_BUTTON = QColor(33, 150, 243)  # Blue for buttons
    COLOR_BUTTON_TEXT = QColor(255, 255, 255)  # White text for buttons
    COLOR_INTERFACE = QColor(50, 50, 50)  # Dark gray for interface name
    COLOR_HER_GLOW = QColor(76, 175, 80, 120)  # Green for Her-inspired particles with alpha
    
    def __init__(self, size=200, status_file=None, message_file=None):
        """
        Initialize the status overlay.
        """
        super().__init__()
        
        # Configuration
        self.size_val = size
        self.opacity = 1.0
        
        # Communication files
        self.status_file = status_file
        self.message_file = message_file
        self.last_status_modified = 0
        
        # State variables
        self.current_status = OverlayManager.STATUS_INITIALIZING
        self.additional_info = ""
        self.interface_name = "SuperCode"  # Default interface name
        self.is_recording = False
        self.animation_frame = 0
        self.dragging = False
        
        # Generate particles for recording state animation
        self.her_particles = []
        self._generate_her_particles()
        
        # Application state
        self.running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        
        # Status check timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_status_file)
        
        # Initialize UI
        self.init_ui()
    
    def _generate_her_particles(self):
        """Generate particles for recording state animation"""
        import random
        
        # Clear existing particles
        self.her_particles = []
        
        # Create 20 particles with random properties
        for _ in range(20):
            particle = {
                'base_angle': random.uniform(0, 2 * math.pi),  # Random starting angle
                'distance': random.uniform(30, 80),  # Random distance from center
                'speed': random.uniform(0.01, 0.05),  # Random speed
                'size': random.uniform(2, 6),  # Random size
                'opacity': random.uniform(50, 120)  # Random opacity
            }
            self.her_particles.append(particle)
    
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Status Overlay")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(self.size_val, self.size_val)
        self.setMaximumSize(self.size_val, self.size_val)
        
        # Remove border style
        self.setStyleSheet("background-color: transparent;")
        
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
        try:
            if not self.status_file:
                return
                
            try:
                current_modified = os.path.getmtime(self.status_file)
                if current_modified > self.last_status_modified:
                    # File has been modified, read the status
                    with open(self.status_file, 'r') as f:
                        data = json.loads(f.read())
                        status = data.get("status", OverlayManager.STATUS_INITIALIZING)
                        info = data.get("info", "")
                        interface = data.get("interface", "SuperCode")
                        
                        # Update overlay status
                        self.current_status = status
                        self.additional_info = info
                        self.interface_name = interface
                        self.is_recording = status == OverlayManager.STATUS_RECORDING
                        self.update()
                        
                        print(f"Status updated: {status} - {info} - Interface: {interface}")
                    
                    # Update last modified time
                    self.last_status_modified = current_modified
            except Exception as e:
                self._log_error("Error reading status file", e)
        except Exception as outer_e:
            self._log_error("Error in check_status_file", outer_e)
    
    def update_animation(self):
        """Update animation state and redraw"""
        try:
            if not self.running:
                return
                
            self.animation_frame += 1
            self.update()
        except Exception as e:
            self._log_error("Error in update_animation", e)
    
    def _log_error(self, message, exception=None):
        """Log an error message to a file with stack trace if available"""
        try:
            error_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_error.log")
            with open(error_log_path, 'a') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
                
                # Include exception details if provided
                if exception:
                    f.write(f"Exception: {str(exception)}\n")
                    
                    # Include stack trace
                    if hasattr(exception, '__traceback__'):
                        stack_trace = ''.join(traceback.format_tb(exception.__traceback__))
                        f.write(f"Stack trace:\n{stack_trace}\n")
                    
                f.write("-" * 50 + "\n")
        except Exception as e:
            print(f"Error logging to file: {e}")
            
    def paintEvent(self, event):
        """Paint the overlay content"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate sizes for responsive layout
            padding = 15
            width = self.width() - 2 * padding
            height = 140  # Increased height to accommodate interface name
            
            # Draw rounded rectangle background with shadow
            path = QPainterPath()
            rect = QRectF(padding, padding, width, height)
            path.addRoundedRect(rect, 20, 20)  # More rounded corners
            
            # Fill background
            painter.fillPath(path, self.COLOR_BG)
            
            # Draw interface name at the top
            painter.setPen(self.COLOR_INTERFACE)
            interface_font = QFont("SF Pro Display", 12)
            interface_font.setWeight(QFont.DemiBold)
            painter.setFont(interface_font)
            
            # Leave space for the close button
            close_button_width = 30
            interface_width = width - close_button_width - 10
            
            # Truncate interface name if it's too long
            fm = painter.fontMetrics()
            truncated_interface_name = self.interface_name
            if fm.horizontalAdvance(self.interface_name) > interface_width:
                # Find the maximum characters that can fit
                available_width = interface_width - fm.horizontalAdvance("...")
                truncated_text = ""
                for char in self.interface_name:
                    if fm.horizontalAdvance(truncated_text + char) <= available_width:
                        truncated_text += char
                    else:
                        break
                truncated_interface_name = truncated_text + "..."
            
            # Draw interface name centered at the top with a slight border (leaving space for close button)
            interface_rect = QRectF(padding + 5, padding + 5, interface_width, 25)
            painter.drawText(interface_rect, Qt.AlignCenter, truncated_interface_name)
            
            # Draw a light separator line
            painter.setPen(QColor(200, 200, 200))
            painter.drawLine(padding + 20, padding + 30, padding + width - 20, padding + 30)
            
            # Draw status indicator dot with smoother animation
            # Calculate pulsing effect based on animation frame - smoother sine wave
            pulse_factor = abs(math.sin(self.animation_frame * 0.08)) * 0.4 + 0.6  # 0.6 to 1.0 range with slower frequency
            
            # Draw glowing circle effect first (subtle shadow)
            if self.current_status == "Executing command" or self.current_status == "Listening for 'activate'":
                try:
                    # Select color based on status
                    dot_color = self.COLOR_STATUS if self.current_status == "Executing command" else self.COLOR_IDLE
                    
                    # Draw outer glow
                    for i in range(3):
                        glow_size = 16 * pulse_factor + (3-i)*2
                        glow_opacity = 40 - i*10
                        
                        glow_color = QColor(dot_color)
                        glow_color.setAlpha(glow_opacity)
                        
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(glow_color)
                        
                        # Center the glow properly - moved down to accommodate interface name
                        glow_x = padding + 20 + (14 - glow_size) / 2
                        glow_y = padding + 45 + (14 - glow_size) / 2
                        painter.drawEllipse(int(glow_x), int(glow_y), int(glow_size), int(glow_size))
                    
                    # Draw the main dot
                    status_dot_size = 14 * pulse_factor
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(dot_color)
                    
                    # Center the dot properly with the pulsing effect - moved down
                    dot_x = padding + 20 + (14 - status_dot_size) / 2
                    dot_y = padding + 45 + (14 - status_dot_size) / 2
                    painter.drawEllipse(int(dot_x), int(dot_y), int(status_dot_size), int(status_dot_size))
                except Exception as e:
                    self._log_error("Error drawing status indicator dot", e)
            
            # Draw Her-inspired animation for the listening state
            if self.current_status == OverlayManager.STATUS_RECORDING:
                try:
                    # Make sure particles are initialized
                    if not hasattr(self, 'her_particles') or not self.her_particles:
                        self._generate_her_particles()
                    
                    # Draw beautiful particles radiating outward
                    # Calculate center of overlay for the particles
                    center_x = self.width() / 2
                    center_y = padding + 85
                    
                    # Draw particles
                    for particle in self.her_particles:
                        if particle['opacity'] > 5:  # Only draw visible particles
                            try:
                                # Calculate particle position based on angle and distance
                                # Smooth orbital movement around the perfect circle
                                orbit_speed = 0.008  # Slower orbit for smoother appearance
                                x = center_x + math.cos(particle['base_angle'] + (self.animation_frame * orbit_speed)) * particle['distance']
                                y = center_y + math.sin(particle['base_angle'] + (self.animation_frame * orbit_speed)) * particle['distance']
                                
                                # Create gradient colors for particles
                                particle_color = QColor(self.COLOR_HER_GLOW)
                                particle_color.setAlpha(int(particle['opacity']))
                                
                                # Draw the particle
                                painter.setPen(Qt.NoPen)
                                painter.setBrush(particle_color)
                                # Subtler size pulsing for smoother appearance
                                particle_size = particle['size'] * (0.9 + 0.1 * math.sin(self.animation_frame * 0.05))
                                painter.drawEllipse(int(x - particle_size/2), int(y - particle_size/2), 
                                                  int(particle_size), int(particle_size))
                            except Exception as e:
                                # Skip this particle if there's an error
                                self._log_error(f"Error drawing particle #{self.her_particles.index(particle)}", e)
                                continue
                except Exception as e:
                    # If anything fails in the particle animation, log it but don't crash
                    self._log_error("Error in particle animation", e)
                    # Try to regenerate particles for next frame
                    try:
                        self._generate_her_particles()
                    except Exception as regenerate_error:
                        self._log_error("Error regenerating particles", regenerate_error)
            
            # Set status text color - beautiful grey for most states, green only for executing
            status_color = self.COLOR_TEXT  # Default beautiful grey
            if self.current_status == OverlayManager.STATUS_EXECUTING or self.current_status == "Executing command":
                status_color = self.COLOR_STATUS  # Green for executing commands
            
            painter.setPen(status_color)
            status_font = QFont("SF Pro Display", 14)  # Use a more modern font
            status_font.setWeight(QFont.DemiBold)
            painter.setFont(status_font)
            
            # Draw status text
            painter.drawText(QRectF(padding, padding + 35, width, 35), Qt.AlignCenter, self.current_status)
            
            # Draw additional info (command)
            if self.additional_info:
                painter.setPen(self.COLOR_TEXT)
                info_font = QFont("SF Pro Text", 15)  # Bigger font for command text
                painter.setFont(info_font)
                
                # Truncate text if longer than 20 words
                words = self.additional_info.split()
                if len(words) > 20:
                    truncated_text = " ".join(words[:20]) + "…"
                else:
                    truncated_text = self.additional_info
                
                # Center the command text - moved down
                text_rect = QRectF(padding, padding + 70, width, 50)
                painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, truncated_text)
            
            # Draw Start Listening button when voice recognition is stopped
            if self.current_status == OverlayManager.STATUS_STOPPED:
                # Calculate button rect
                button_width = 160
                button_height = 40
                button_x = padding + (width - button_width) / 2
                button_y = padding + height - button_height - 15  # 15px from bottom
                
                # Draw button background
                button_path = QPainterPath()
                button_rect = QRectF(button_x, button_y, button_width, button_height)
                button_path.addRoundedRect(button_rect, 10, 10)
                
                painter.setPen(Qt.NoPen)
                painter.setBrush(self.COLOR_BUTTON)
                painter.fillPath(button_path, self.COLOR_BUTTON)
                
                # Draw button text
                painter.setPen(self.COLOR_BUTTON_TEXT)
                painter.setFont(QFont("SF Pro Display", 14, QFont.DemiBold))
                painter.drawText(button_rect, Qt.AlignCenter, "Resume Listening")
            
            # Draw close button
            painter.setPen(self.COLOR_CLOSE)
            close_font = QFont("SF Pro Display", 15)
            painter.setFont(close_font)
            painter.drawText(QRectF(width + padding - 25, padding + 5, 25, 25), Qt.AlignCenter, "×")
        except Exception as outer_e:
            # Log the outer exception but don't crash
            self._log_error("Fatal error in paintEvent", outer_e)
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        try:
            # Check if click is on close button
            close_size = 25
            padding = 15
            width = self.width() - 2 * padding
            
            if event.x() > width + padding - close_size and event.x() < width + padding and event.y() > padding and event.y() < padding + close_size:
                # Send a close event message via file
                self.send_close_signal()
                return
                
            # Check if the status is stopped and click is on the Start Listening button
            if self.current_status == OverlayManager.STATUS_STOPPED:
                # Calculate button rect
                button_width = 160
                button_height = 40
                height = 140
                button_x = padding + (width - button_width) / 2
                button_y = padding + height - button_height - 15  # 15px from bottom
                
                # Check if click is inside the button
                if (event.x() >= button_x and event.x() <= button_x + button_width and
                    event.y() >= button_y and event.y() <= button_y + button_height):
                    # Send a start listening event message
                    self.send_start_listening_signal()
                    return
            
            # Start dragging
            if event.button() == Qt.LeftButton:
                self.dragging = True
                self.offset = event.pos()
        except Exception as e:
            self._log_error("Error in mousePressEvent", e)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging"""
        try:
            if self.dragging and event.buttons() & Qt.LeftButton:
                # Move the window
                self.move(self.mapToGlobal(event.pos() - self.offset))
        except Exception as e:
            self._log_error("Error in mouseMoveEvent", e)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        try:
            if event.button() == Qt.LeftButton:
                self.dragging = False
        except Exception as e:
            self._log_error("Error in mouseReleaseEvent", e)
            
    def send_close_signal(self):
        """Send a signal that the close button was clicked"""
        try:
            print("Close button clicked")
            
            # Write close message to file if we have one
            if self.message_file:
                try:
                    with open(self.message_file, 'w') as f:
                        f.write(json.dumps({"message": "CLOSE"}))
                    print("Wrote CLOSE message to file")
                except Exception as e:
                    self._log_error("Error writing close message to file", e)
            
            # Exit this process
            QApplication.quit()
        except Exception as e:
            self._log_error("Error in send_close_signal", e)
        
    def send_start_listening_signal(self):
        """Send a signal that the Start Listening button was clicked"""
        try:
            print("Start Listening button clicked")
            
            # Write start message to file if we have one
            if self.message_file:
                try:
                    with open(self.message_file, 'w') as f:
                        f.write(json.dumps({"message": "START_LISTENING"}))
                    print("Wrote START_LISTENING message to file")
                except Exception as e:
                    self._log_error("Error writing start message to file", e)
        except Exception as e:
            self._log_error("Error in send_start_listening_signal", e)
    
    def update_status(self, status, additional_info=""):
        """
        Update the current status displayed in the overlay.
        """
        self.current_status = status
        self.additional_info = additional_info
        
        # Update recording state based on status
        self.is_recording = status == OverlayManager.STATUS_RECORDING
        
        # Trigger update if window is visible
        if self.isVisible():
            self.update()

def main():
    """Run the overlay"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Status overlay")
    parser.add_argument("--status-file", help="Path to status file for communication")
    parser.add_argument("--message-file", help="Path to message file for sending messages back")
    parser.add_argument("--size", type=int, default=250, help="Size of the overlay window")
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