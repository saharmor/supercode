#!/usr/bin/env python3
"""
Status overlay for SuperCode application.
Displays a small, always-on-top window showing the current state of the application
with visual feedback for recording, transcribing, and command execution.
"""

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF, QPropertyAnimation, QEasingCurve, QCoreApplication
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QBrush, QFont
import threading
import time
import math
import numpy as np
import sys
from typing import List, Optional, Callable

class SuperCodeOverlay(QWidget):
    """
    Always-on-top status overlay for SuperCode that shows:
    - Recording visualization (animated audio waves)
    - Current status text (Listening, Recording, Transcribing, Executing)
    - Additional information about the current action
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
    
    def __init__(self, size=200, position="top-right", opacity=0.9):
        """
        Initialize the status overlay.
        
        Args:
            size: Size of the overlay window in pixels (default: 200)
            position: Where to position the overlay ("top-right", "top-left", "bottom-right", "bottom-left")
            opacity: Window opacity from 0.0 to 1.0 (default: 0.9)
        """
        print("Initializing SuperCodeOverlay...")
        # Get existing QApplication instance
        self.app = QApplication.instance()
        if not self.app:
            print("No QApplication instance found, creating new one...")
            self.app = QApplication([])
            print("QApplication instance created")
        else:
            print("Using existing QApplication instance")
            
        # Get screen information for debugging
        screen = self.app.primaryScreen()
        geometry = screen.geometry()
        print(f"Screen dimensions: {geometry.width()}x{geometry.height()}")
        
        super().__init__()
        print("QWidget initialized")
        
        # Configuration
        self.size_val = size
        print(f"Overlay size set to: {size}x{size} pixels")
        self.position = position
        self.opacity = opacity
        
        # State variables
        self.current_status = self.STATUS_IDLE
        self.additional_info = ""
        self.is_recording = False
        self.audio_levels = [0.1] * 20  # Initialize with minimal levels
        self.animation_frame = 0
        self.wave_points = 20
        
        # Dragging state
        self.dragging = False
        self.offset = QPoint()
        
        # Application state
        self.running = False
        self.update_thread = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("SuperCode Status")
        # Use stronger window flags to ensure visibility
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus |
            Qt.SubWindow  # Add SubWindow flag to ensure it stays on top
        )
        
        # Force window level to appear in macOS menu bar apps
        # NSWindowLevel constants for macOS (will be used after window is shown)
        self.NSStatusWindowLevel = 25  # This is the level of the macOS menu bar
        
        # Don't try to set window level here - window handle not available yet
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowOpacity(self.opacity)
        self.setMinimumSize(self.size_val, self.size_val)
        self.setMaximumSize(self.size_val, self.size_val)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: 2px solid #FF0000;  /* Make border RED for easier visibility */
                border-width: 3px;
                border-radius: 10px;
            }
        """)
        
        # Position the window
        self.position_window()
    
    def position_window(self):
        """Position the overlay based on the screen size"""
        # Get screen dimensions
        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        
        # Calculate position based on setting
        x, y = 0, 0
        if self.position == "top-right":
            x = screen_width - self.size_val - 20
            y = 20
        elif self.position == "top-left":
            x = 20
            y = 20
        elif self.position == "bottom-right":
            x = screen_width - self.size_val - 20
            y = screen_height - self.size_val - 20
        elif self.position == "bottom-left":
            x = 20
            y = screen_height - self.size_val - 20
        
        # Set position
        self.move(x, y)
    
    def start(self):
        """Start the overlay window"""
        if self.running:
            print("Overlay already running, returning")
            return
            
        print("Setting running state and showing window...")
        self.running = True
        
        try:
            # MACOS SPECIFIC: Force window to appear at the right level
            # This uses PyQt's native window functionality
            window = self.windowHandle()
            if window:
                print("Got window handle, setting level...")
                # Force window level to appear above all others
                window.setProperty("_q_windowLevel", 25+1)  # Above macOS menu bar
            else:
                print("Window handle not available yet")
        except Exception as e:
            print(f"Error setting window level: {e}")
        
        # Flash effect to make the window noticeable
        self.setWindowOpacity(1.0)
        
        # Ensure window is properly shown and stays on top
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Force window to be visible and process events
        QCoreApplication.processEvents()
        
        # Try getting window handle again after showing
        try:
            window = self.windowHandle()
            if window:
                print("Setting window level after show...")
                window.setProperty("_q_windowLevel", 25+1)  # Above macOS menu bar
        except Exception as e:
            print(f"Error setting window level after show: {e}")
        
        print(f"Window shown at position: ({self.x()}, {self.y()})")
        print("Starting animation timer...")
        self.timer.start(50)  # Update every 50ms
        
        # Gradually fade to target opacity
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(1000)  # 1 second
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(self.opacity)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_anim.start()
        
        print("Animation timer started")
        
        return threading.current_thread()
    
    def stop(self):
        """Stop the overlay window"""
        self.running = False
        self.timer.stop()
        self.hide()
        
        # No need to quit the QApplication as it's managed by the main app
    
    def update_animation(self):
        """Update animation state and redraw"""
        if not self.running:
            return
            
        self.animation_frame += 1
        self.update()
    
    def paintEvent(self, event):
        """Paint the overlay content"""
        try:
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
            painter.drawText(QRectF(0, 10, self.width(), 40), Qt.AlignCenter, self.current_status)
            
            # Draw additional info
            if self.additional_info:
                painter.setPen(self.COLOR_TEXT)
                painter.setFont(QFont("Arial", 10))
                text_rect = QRectF(10, 40, self.width() - 20, 40)
                painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self.additional_info)
            
            # Draw waveform
            self.draw_waveform(painter)
            
            # Draw close button
            close_size = 20
            painter.fillRect(self.width() - close_size, 0, close_size, close_size, QColor(51, 51, 51))
            painter.setPen(self.COLOR_TEXT)
            painter.setFont(QFont("Arial", 14))
            painter.drawText(QRectF(self.width() - close_size, 0, close_size, close_size), Qt.AlignCenter, "×")
            
        except Exception as e:
            print(f"Error painting overlay: {e}")
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        # Check if click is on close button
        close_size = 20
        if event.x() > self.width() - close_size and event.y() < close_size:
            self.stop()
            return
            
        # Start dragging
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for dragging"""
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(self.mapToGlobal(event.pos() - self.offset))
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    def draw_waveform(self, painter):
        """Draw the animated audio waveform"""
        center_y = 120
        width = self.width() - 40
        height = 80
        start_x = 20
        
        # Create wave points
        upper_points = []
        lower_points = []
        
        for i in range(self.wave_points):
            x = start_x + (width / (self.wave_points - 1)) * i
            
            # Determine amplitude
            amplitude = self.audio_levels[i % len(self.audio_levels)]
            
            # Add animation
            if self.is_recording:
                # More active animation during recording
                amplitude *= 1.0 + 0.3 * math.sin((self.animation_frame + i * 2) * 0.2)
            else:
                # Gentle pulsing when not recording
                amplitude *= 0.3 + 0.15 * math.sin(self.animation_frame * 0.1)
            
            upper_y = center_y + amplitude * height / 2
            lower_y = center_y - amplitude * height / 2
            
            upper_points.append(QPoint(int(x), int(upper_y)))
            lower_points.append(QPoint(int(x), int(lower_y)))
        
        # Draw the waveforms
        if upper_points and lower_points:
            # Select color based on state
            wave_color = self.COLOR_WAVE_ACTIVE if self.is_recording else self.COLOR_WAVE_INACTIVE
            
            # Create pen for drawing
            pen = QPen(wave_color, 2, Qt.SolidLine)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            
            # Draw upper waveform
            for i in range(1, len(upper_points)):
                painter.drawLine(upper_points[i-1], upper_points[i])
            
            # Draw lower waveform
            for i in range(1, len(lower_points)):
                painter.drawLine(lower_points[i-1], lower_points[i])
    
    def update_status(self, status, additional_info=""):
        """
        Update the current status displayed in the overlay.
        
        Args:
            status: One of the STATUS_* constants or a custom status string
            additional_info: Additional information to display
        """
        self.current_status = status
        self.additional_info = additional_info
        
        # Update recording state based on status
        self.is_recording = status == self.STATUS_RECORDING
        
        # Trigger update if window is visible
        if self.isVisible():
            self.update()
    
    def update_audio_levels(self, audio_data):
        """
        Update the audio levels for visualization.
        
        Args:
            audio_data: Raw audio data bytes or numpy array
        """
        try:
            # Convert bytes to numpy array if needed
            if isinstance(audio_data, bytes):
                data = np.frombuffer(audio_data, dtype=np.int16)
            else:
                data = audio_data
                
            # Divide the data into chunks
            chunk_size = len(data) // self.wave_points
            if chunk_size < 1:
                chunk_size = 1
                
            # Calculate RMS for each chunk
            new_levels = []
            for i in range(min(self.wave_points, len(data) // chunk_size)):
                start = i * chunk_size
                end = start + chunk_size
                chunk = data[start:end]
                rms = np.sqrt(np.mean(np.square(chunk.astype(np.float32))))
                
                # Normalize to 0.0-1.0 range with some reasonable scaling
                normalized = min(1.0, rms / 10000)
                new_levels.append(normalized)
                
            # Smooth transition with existing levels
            if new_levels:
                # Update audio levels with some smoothing
                alpha = 0.3  # Smoothing factor (0-1)
                for i in range(min(len(self.audio_levels), len(new_levels))):
                    self.audio_levels[i] = alpha * new_levels[i] + (1 - alpha) * self.audio_levels[i]
                    
        except Exception as e:
            print(f"Error updating audio levels: {e}")

# For testing/demo purposes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    overlay = SuperCodeOverlay(size=180)
    overlay.start()
    
    # Demo status changes in a separate thread
    def demo_animation():
        try:
            states = [
                (SuperCodeOverlay.STATUS_IDLE, ""),
                (SuperCodeOverlay.STATUS_RECORDING, ""),
                (SuperCodeOverlay.STATUS_TRANSCRIBING, ""),
                (SuperCodeOverlay.STATUS_EXECUTING, "type hello world"),
                (SuperCodeOverlay.STATUS_IDLE, "")
            ]
            
            for status, info in states:
                overlay.update_status(status, info)
                # Generate some random audio levels for demo
                dummy_audio = np.random.normal(0, 32000, 1024).astype(np.int16)
                overlay.update_audio_levels(dummy_audio)
                time.sleep(2)
                
        except Exception as e:
            print(f"Error in demo: {e}")
    
    # Start demo in background
    threading.Thread(target=demo_animation, daemon=True).start()
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        overlay.stop()
