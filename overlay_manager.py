#!/usr/bin/env python3
"""
Overlay manager for SuperCode application.
Controls the overlay window through IPC communication.
"""

import threading
import time
import sys
import os
import signal
import subprocess
import json
import tempfile

class OverlayManager:
    """
    Manager class that creates and controls the overlay in a separate process.
    This allows the overlay to run independently from the rumps app.
    """
    
    # Status constants
    STATUS_IDLE = "Waiting for 'activate'"
    STATUS_RECORDING = "Listening"
    STATUS_TRANSCRIBING = "Transcribing"
    STATUS_EXECUTING = "Executing command"
    STATUS_STOPPED = "Voice Recognition Stopped"
    STATUS_INITIALIZING = "Initializing"
    
    def __init__(self):
        """Initialize the overlay manager"""
        self.overlay_process = None
        self.is_visible = False
        self.current_status = self.STATUS_IDLE
        self.additional_info = ""
        self.interface_name = "SuperCode"  # Default interface name
        self.close_handler = None  # Function to call when close message is received
        self.start_handler = None  # Function to call when start message is received
        
        # Create a temporary file for communication
        self.status_file = tempfile.NamedTemporaryFile(delete=False, mode='w+')
        self.status_file.write(json.dumps({
            "status": self.STATUS_IDLE, 
            "info": "",
            "interface": self.interface_name
        }))
        self.status_file.flush()
        
        # Create a temporary file for receiving messages from the overlay
        self.message_file = tempfile.NamedTemporaryFile(delete=False, mode='w+')
        self.message_file.write(json.dumps({"message": ""}))
        self.message_file.flush()
        
        # Start a thread to monitor messages
        self.should_monitor = False
        self.monitor_thread = None
    
    def set_close_handler(self, handler_func):
        """Set the function to call when overlay is closed"""
        self.close_handler = handler_func
    
    def set_start_handler(self, handler_func):
        """Set the function to call when start listening button is clicked"""
        self.start_handler = handler_func
    
    def set_interface_name(self, interface_name):
        """Set the current interface name to be displayed in the overlay"""
        self.interface_name = interface_name
        # Update the status to reflect the new interface name
        self.update_status(self.current_status, self.additional_info)
    
    def show_overlay(self):
        """
        Show the overlay by launching overlay.py as a separate process
        """
        if self.overlay_process and self.overlay_process.poll() is None:
            return
            
        
        # Create the command to run the overlay with our status file
        cmd = [
            sys.executable,
            "overlay.py",
            "--status-file", self.status_file.name,
            "--message-file", self.message_file.name
        ]
        
        # Start the subprocess
        self.overlay_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start message monitoring
        self.should_monitor = True
        self.monitor_thread = threading.Thread(target=self._monitor_messages)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # Update initial status
        self.update_status(self.current_status, self.additional_info)
        
        self.is_visible = True
    
    def hide_overlay(self):
        """Hide the overlay by terminating its process"""
        if not self.overlay_process or self.overlay_process.poll() is not None:
            print("No overlay process to hide")
            return
            
        try:
            # Stop message monitoring
            self.should_monitor = False
            if self.monitor_thread:
                self.monitor_thread.join(1)
            
            # Terminate the process
            self.overlay_process.terminate()
            self.overlay_process.wait(1)  # Wait up to 1 second
            
            # If it's still running, force kill
            if self.overlay_process.poll() is None:
                print("Process didn't terminate, killing it")
                if sys.platform == 'win32':
                    os.kill(self.overlay_process.pid, signal.CTRL_BREAK_EVENT)
                else:
                    os.kill(self.overlay_process.pid, signal.SIGKILL)
                
            self.is_visible = False
        except Exception as e:
            print(f"Error hiding overlay: {e}")
    
    def _truncate_text(self, text, max_words=10):
        """
        Truncate text to a maximum number of words
        
        Args:
            text: The text to truncate
            max_words: Maximum number of words to keep (default: 10)
            
        Returns:
            Truncated text with ellipsis if truncated
        """
        if not text:
            return ""
            
        words = text.split()
        if len(words) <= max_words:
            return text
        
        return " ".join(words[:max_words]) + "..."
    
    def update_status(self, status, additional_info=""):
        """
        Update the status displayed in the overlay by writing to the status file
        """
        self.current_status = status
        
        # Truncate additional info to 10 words
        truncated_info = self._truncate_text(additional_info, max_words=10)
        self.additional_info = truncated_info
        
        # Write status to file
        try:
            with open(self.status_file.name, 'w') as f:
                f.write(json.dumps({
                    "status": status,
                    "info": truncated_info,
                    "interface": self.interface_name
                }))
        except Exception as e:
            print(f"Error updating status file: {e}")
    
    def _monitor_messages(self):
        """Monitor the message file for signals from the overlay"""
        last_modified = os.path.getmtime(self.message_file.name)
        
        while self.should_monitor:
            try:
                current_modified = os.path.getmtime(self.message_file.name)
                if current_modified > last_modified:
                    # File has been modified, read the message
                    with open(self.message_file.name, 'r') as f:
                        data = json.loads(f.read())
                        message = data.get("message", "")
                        
                        if message == "CLOSE":
                            print("Received close signal from overlay")
                            if self.close_handler:
                                # Call in the main thread
                                self.close_handler()
                            # Reset the message
                            with open(self.message_file.name, 'w') as f:
                                f.write(json.dumps({"message": ""}))
                        elif message == "START_LISTENING":
                            print("Received start listening signal from overlay")
                            if self.start_handler:
                                # Call in the main thread
                                self.start_handler()
                            # Reset the message
                            with open(self.message_file.name, 'w') as f:
                                f.write(json.dumps({"message": ""}))
                    
                    last_modified = current_modified
            except Exception as e:
                print(f"Error monitoring messages: {e}")
            
            # Sleep to avoid high CPU usage
            time.sleep(0.5)
    
    def __del__(self):
        """Clean up resources when the manager is deleted"""
        self.hide_overlay()
        
        # Clean up temp files
        try:
            os.unlink(self.status_file.name)
            os.unlink(self.message_file.name)
        except:
            pass

# For testing
if __name__ == "__main__":
    # Test the overlay manager
    manager = OverlayManager()
    manager.show_overlay()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping overlay...")
        manager.hide_overlay()
        print("Done") 