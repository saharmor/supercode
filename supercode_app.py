#!/usr/bin/env python3
"""
SuperCode - A macOS menu bar app with status overlay for voice commands
This app provides voice command recognition with visual feedback of the current status.
"""

import rumps
import threading
import time
import os
import socket
import sys
import errno
from dotenv import load_dotenv

load_dotenv()

# Import the whisper streaming functionality and command processing
from mic_streaming import FastSpeechHandler
from command_processor import CommandProcessor
# Import the overlay manager
from overlay_manager import OverlayManager

# Add pynput for global shortcuts
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    # Silently handle missing pynput - it should be installed via requirements.txt
    HAS_PYNPUT = False
    print("Failed to import pynput")

class SingleInstanceChecker:
    """
    Ensures only one instance of the application is running.
    Uses a socket bound to a specific port to detect other instances.
    """
    def __init__(self, port=47200):
        self.port = port
        self.sock = None
        
    def is_running(self):
        """Check if another instance is already running"""
        try:
            # Create a TCP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Try to bind to the port on localhost
            self.sock.bind(('127.0.0.1', self.port))
            # If we got here, no other instance is running
            return False
        except socket.error as e:
            # Address already in use error means another instance is running
            if e.errno == errno.EADDRINUSE:
                if self.sock:
                    self.sock.close()
                    self.sock = None
                return True
            # Some other error
            print(f"Socket error: {e}")
            return False
    
    def cleanup(self):
        """Close the socket when the app exits"""
        if self.sock:
            self.sock.close()


class SuperCodeApp(rumps.App):
    def __init__(self):
        """Initialize the SuperCode App with menu bar and status overlay"""
        super(SuperCodeApp, self).__init__("SuperCode", 
                                          icon=None,
                                          title=None,
                                          quit_button=rumps.MenuItem("Quit"))
        
        self.is_listening = False
        self.listen_thread = None
        self.handler = None
        self.keyboard_listener = None
        self.current_interface = "SuperCode"  # Track the current interface
        
        # Use our new overlay manager instead of direct overlay
        self.overlay_manager = OverlayManager()
        # Set the interface name in the overlay
        self.overlay_manager.set_interface_name(self.current_interface)
        # Set the close handler
        self.overlay_manager.set_close_handler(self.stop_from_overlay)
        # Set the start handler
        self.overlay_manager.set_start_handler(self.start_from_overlay)
        
        # Create menu items
        self.menu = [
            rumps.MenuItem("Start Listening", callback=self.toggle_listening),
            None,  # Separator
            rumps.MenuItem("About", callback=self.show_about)
        ]
        
        # Set up global keyboard shortcut
        self.setup_global_shortcut()
    
    def setup_global_shortcut(self):
        """Set up global keyboard shortcut (Command + Option + L)"""
        try:
            # Only set up if pynput is available
            if HAS_PYNPUT:
                # Track pressed keys
                self.pressed_keys = set()
                self.hotkey_triggered = False  # Flag to ensure one trigger per key cycle

                def on_press(key):
                    try:                        
                        # Add the key to the set of pressed keys
                        self.pressed_keys.add(key)
        
                        # Check if the Command key is pressed
                        is_cmd = (keyboard.Key.cmd in self.pressed_keys or
                                keyboard.Key.cmd_l in self.pressed_keys or
                                keyboard.Key.cmd_r in self.pressed_keys)
                        
                        # Check if the Option/Alt key is pressed
                        is_alt = (keyboard.Key.alt in self.pressed_keys or
                                keyboard.Key.alt_l in self.pressed_keys or
                                keyboard.Key.alt_r in self.pressed_keys)
                        
                        # Check if the letter "l" is pressed
                        is_l = any(getattr(k, 'char', None) and k.char == '¬' for k in self.pressed_keys)
                        
                        if is_cmd and is_alt and is_l and not self.hotkey_triggered:
                            self.hotkey_triggered = True
                            self.on_hotkey_activated()
                            
                    except Exception as e:
                        print(f"Error on key press: {e}")
                
                def on_release(key):
                    try:
                        if key in self.pressed_keys:
                            self.pressed_keys.remove(key)
                        
                        # If any part of the combination is released, reset the flag
                        if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
                                keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r) or (
                            hasattr(key, 'char') and key.char and key.char.lower() == 'l'):
                            self.hotkey_triggered = False
                    except Exception as e:
                        print(f"Error on key release: {e}")
                
                # Start the listener in a non-blocking way
                self.keyboard_listener = keyboard.Listener(
                    on_press=on_press,
                    on_release=on_release,
                    suppress=False  # Don't suppress events to avoid conflicts
                )
                self.keyboard_listener.daemon = True
                self.keyboard_listener.start()
            else:
                # Log to console but don't show error to user
                print("pynput not available, global shortcut disabled")
        except Exception as e:
            print(f"Error setting up global shortcut: {e}")
            import traceback
            traceback.print_exc()
    
    def on_hotkey_activated(self):
        """Handle global hotkey activation"""
        # Create a one-shot timer by stopping it in the callback.
        timer = rumps.Timer(self.toggle_listening_from_shortcut, 0.1)
        timer.start()

    
    def toggle_listening_from_shortcut(self, timer):
        """Toggle listening from a global shortcut (ensures running on main thread)"""
        timer.stop()
        print("Toggling listening from global shortcut")
        
        # Find the "Start Listening" menu item to pass as sender
        toggled_item = self.menu['Start Listening'] if 'Start Listening' in self.menu else self.menu['Stop Listening']
        self.toggle_listening(toggled_item)
        
    def toggle_listening(self, sender):
        """Toggle the listening state with visual feedback"""
        if self.is_listening:
            self.stop_listening()
            sender.title = "Start Listening"
            self.title = "SuperCode"
            
            # Hide the overlay when stopping
            self.hide_overlay()
        else:
            self.start_listening()
            sender.title = "Stop Listening"
            self.title = "SuperCode"
            
            # Always show the overlay when starting
            self.show_overlay()
    
    def show_overlay(self):
        """Show the status overlay"""
        try:
            # Don't pass a callback directly - overlay will communicate via messages instead
            self.overlay_manager.show_overlay()
        except Exception as e:
            print(f"Error showing overlay: {e}")
            import traceback
            traceback.print_exc()
    
    def hide_overlay(self):
        """Hide the status overlay"""
        try:
            self.overlay_manager.hide_overlay()
        except Exception as e:
            print(f"Error hiding overlay: {e}")
            import traceback
            traceback.print_exc()
            
    def start_listening(self):
        """Start listening for voice commands"""
        if self.is_listening:
            return
            
        self.is_listening = True
        
        # Always show the overlay when starting
        self.show_overlay()
        
        # Set initializing status
        self.overlay_manager.update_status(self.overlay_manager.STATUS_INITIALIZING, "Preparing microphone...")
        
        # Create a new thread to run the whisper streaming handler
        self.listen_thread = threading.Thread(target=self.run_whisper_handler)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        # Get transcription service info
        use_openai_api = os.getenv("USE_OPENAI_API", "false").lower() == "true"
        service_name = "OpenAI Whisper API" if use_openai_api else "Google Speech Recognition"
        
        # The handler will set the status to idle when fully ready
        
        rumps.notification("SuperCode", f"Voice Recognition Active ({service_name})", "Say commands starting with 'activate'")
    
    def stop_listening(self):
        """Stop listening for voice commands"""
        if not self.is_listening:
            return
            
        self.is_listening = False
        
        # Stop the handler if it exists
        if self.handler:
            self.handler.stop()
            self.handler = None
        
        # Update the overlay status
        self.overlay_manager.update_status("Voice Recognition Stopped")
            
        rumps.notification("SuperCode", "Voice Recognition Stopped", "Click 'Start Listening' to resume")
    
    def run_whisper_handler(self):
        """Run the whisper streaming handler in a separate thread"""
        try:
            # Create a custom command processor with overlay access
            command_processor = EnhancedCommandProcessor(self.overlay_manager, self)
            
            # Create an enhanced speech handler that updates the overlay
            self.handler = EnhancedSpeechHandler(
                activation_word="activate",
                silence_duration=3,
                command_processor=command_processor,
                overlay=self.overlay_manager,
                stop_callback=self.stop_from_voice_command
            )
            
            # Log which service is being used
            service_name = "OpenAI Whisper API" if self.handler.use_openai_api else "Google Speech Recognition"
            print(f"Using {service_name} for transcription")
            
            # Start the handler
            listen_thread = self.handler.start()
            
            # Keep the thread running until we stop listening
            while self.is_listening and listen_thread.is_alive():
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error in whisper handler: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Show error notification
            rumps.notification("SuperCode", "Error", f"Error: {str(e)}")
            
            # Reset state
            self.is_listening = False
            self.handler = None
            
    def stop_from_voice_command(self):
        """Stop listening when triggered from a voice command"""
        print("Stopping recording from voice command")
        # Only stop if we're actually listening
        if self.is_listening:
            # Find the "Start Listening" menu item and update it
            for item in self.menu:
                if hasattr(item, 'title') and item.title == "Stop Listening":
                    item.title = "Start Listening"
                    break
                    
            self.title = "SuperCode"
            
            # Stop listening
            self.stop_listening()
    
    def show_about(self, _):
        """Show about information"""
        about = """
ABOUT SuperCode

A macOS menu bar app with status overlay for voice commands.
This app provides voice command recognition with visual feedback
of the application's current status.

Usage:
1. Click "Start Listening" in the menu
2. Watch the overlay for status updates
3. Speak commands beginning with "activate"
4. The app will transcribe and execute your commands
5. To stop, click "Stop Listening" in the menu
6. To toggle the overlay, use the menu option

Example: Say "activate type hello world"
        """
        rumps.alert(title="About SuperCode", message=about, ok="Got it!")

    def stop_from_overlay(self):
        """Stop listening when triggered from the overlay close button"""
        print("Stopping recording from overlay close button")
        # Only stop if we're actually listening
        if self.is_listening:
            # Find the "Start Listening" menu item and update it
            for item in self.menu:
                if hasattr(item, 'title') and item.title == "Stop Listening":
                    item.title = "Start Listening"
                    break
                    
            self.title = "SuperCode"
            
            # Stop listening
            self.stop_listening()
        else:
            # Just hide the overlay if we're not listening
            self.hide_overlay()

    def start_from_overlay(self):
        """Start listening when triggered from the overlay button"""
        print("Starting recording from overlay button")
        # Only start if we're not already listening
        if not self.is_listening:
            # Find the "Start Listening" menu item and update it
            for item in self.menu:
                if hasattr(item, 'title') and item.title == "Start Listening":
                    item.title = "Stop Listening"
                    break
                    
            self.title = "SuperCode"
            
            # Start listening
            self.start_listening()

    def run(self):
        """Run the app and ensure cleanup on exit"""
        try:
            super().run()
        finally:
            # Ensure the overlay is hidden when the app exits
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources when the app exits"""
        print("Cleaning up SuperCode resources...")
        # Hide the overlay
        self.hide_overlay()
        # Stop listening if active
        if self.is_listening:
            self.stop_listening()
        # Stop keyboard listener if active
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def set_current_interface(self, interface_name):
        """Set the current interface name and update the overlay"""
        self.current_interface = interface_name
        self.overlay_manager.set_interface_name(interface_name)


class EnhancedCommandProcessor(CommandProcessor):
    """
    A custom command processor that shows notifications and updates the overlay status.
    """
    def __init__(self, overlay_manager=None, app=None):
        super().__init__(app=app)
        self.overlay_manager = overlay_manager
        
    def process_command(self, command_text):
        """Process a command and update the overlay"""
        print(f"Processing command: {command_text}")
        
        # Update overlay with executing status
        if self.overlay_manager:
            self.overlay_manager.update_status("Executing command", command_text)
        
        # Execute the command using the parent class method
        result = super().process_command(command_text)
        
        # Show a notification
        if result:
            rumps.notification("SuperCode", "Command Executed", command_text)
            
            # Reset overlay status if available
            if self.overlay_manager:
                self.overlay_manager.update_status("Listening for 'activate'")
                
        return result


# Enhanced speech handler that updates the overlay
class EnhancedSpeechHandler(FastSpeechHandler):
    def __init__(self, activation_word="activate", silence_duration=0.8, command_processor=None, overlay=None, stop_callback=None):
        super().__init__(activation_word, silence_duration, command_processor)
        self.overlay_manager = overlay  # This is the overlay_manager
        self.audio_data_buffer = []
        self.stop_callback = stop_callback  # Callback to stop listening completely
    
    # Override hook methods instead of the entire _audio_capture_loop
    def _before_audio_capture(self):
        """Hook called before audio capture starts"""
        print(f"Initializing audio capture...")
        
        # Ensure the overlay shows initializing
        if self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_INITIALIZING, "Preparing microphone...")
    
    def _after_stream_open(self):
        """Hook called after audio stream is opened"""
        # Calibration period - let the mic warm up
        print("Calibrating microphone... Please wait.")
        
        # Minimum initialization time to ensure users see the initializing status
        # This also gives time for the microphone to stabilize
        time.sleep(2.0)
        
        # Now we're ready to listen
        print(f"Ready! Listening for activation word: '{self.activation_word}'\n")
        
        # Update overlay status to idle - now we're ready
        if self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE)
    
    def _on_recording_start(self):
        """Hook called when recording starts"""
        # Update overlay status
        if self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_RECORDING)
    
    def _on_recording_end(self):
        """Hook called when recording ends"""
        # Update overlay status
        if self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_TRANSCRIBING)
    
    def _on_capture_error(self, error):
        """Hook called when an error occurs in the capture loop"""
        # Make sure we reset the overlay status in case of error
        if self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE, "Error: " + str(error))
    
    def _after_stream_close(self):
        """Hook called after the audio stream is closed"""
        # Reset overlay status if we're still running
        if not self.should_stop and self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE)
    
    def _on_initialization_error(self, error):
        """Hook called when an error occurs during initialization"""
        # Update overlay with error
        if self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE, "Error: " + str(error))

    # Override process_recognized_text to update overlay
    def _process_recognized_text(self, text):
        """Process recognized text and update overlay"""
        # Convert text to lowercase for consistent command detection
        text_lower = text.lower()
        
        # Check for stop command
        if self.activation_word in text_lower:
            # Process text and execute any commands found
            commands = self.command_queue.process_text(text)
            
            if self.command_processor and commands:
                # Update overlay with commands if available
                if self.overlay_manager:
                    cmd_text = ", ".join(commands)
                    self.overlay_manager.update_status(self.overlay_manager.STATUS_EXECUTING, cmd_text)
                
                # Execute commands and track results
                for command in commands:
                    # Get the command type (first word)
                    command_type = command.split(" ")[0] if command else ""
                    
                    # Handle stop command specially
                    if command_type == "stop":
                        print("Stopping voice recognition via command")
                        if self.overlay_manager:
                            self.overlay_manager.update_status("Voice Recognition Stopped", "Stopped via voice command")
                        
                        # Execute the stop command to play audio feedback
                        self.command_processor.execute_command("stop")
                        
                        # Call the stop callback if provided
                        if self.stop_callback:
                            # Use threading to avoid blocking
                            threading.Timer(1.0, self.stop_callback).start()
                        return
                    
                    # Handle other known command types
                    elif command_type in ["type", "click", "learn", "change"]:
                        try:
                            self.command_processor.execute_command(command)
                        except Exception as e:
                            print(f"Error executing command: {e}")
                    
                    # Unknown command type - show special message
                    else:
                        print(f"Unknown command type: '{command_type}'")
                        if self.overlay_manager:
                            self.overlay_manager.update_status(
                                self.overlay_manager.STATUS_IDLE,
                                f"[Ignored, unknown command] {command}"
                            )
                            # Schedule reset of overlay status after 3 seconds
                            threading.Timer(3.0, lambda: self.overlay_manager.update_status(
                                self.overlay_manager.STATUS_IDLE)).start()
                
                # Reset overlay status if no commands were found
                if self.overlay_manager and not commands:
                    self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE)
        else:
            # No activation word found - display as ignored
            if self.overlay_manager:
                # Truncate text if longer than 20 words
                words = text.split()
                if len(words) > 20:
                    truncated = " ".join(words[:20]) + "…"
                else:
                    truncated = text
                    
                # Show in overlay with "[Ignored]" prefix
                self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE, f"[Ignored] {truncated}")
                
                # Reset to idle status after 3 seconds
                threading.Timer(3.0, lambda: self.overlay_manager.update_status(
                    self.overlay_manager.STATUS_IDLE)).start()


def main():
    """Initialize and start the SuperCode app"""
    try:
        # Check for existing instance
        instance_checker = SingleInstanceChecker()
        if instance_checker.is_running():
            print("Another instance of SuperCode is already running. Killing existing SuperCode processes.")
            
            # Kill any existing SuperCode processes
            import subprocess
            import signal
            
            # Get all Python processes
            ps_output = subprocess.check_output(['ps', 'aux']).decode('utf-8')
            
            # Find any python processes running supercode_app.py
            current_pid = os.getpid()
            for line in ps_output.split('\n'):
                if 'python' in line and 'supercode_app.py' in line and 'ps aux' not in line:
                    # Extract the PID (second column in ps aux output)
                    try:
                        parts = [p for p in line.split() if p]
                        if len(parts) > 1:
                            pid = int(parts[1])
                            # Skip if this is our own process
                            if pid == current_pid:
                                continue
                                
                            print(f"Killing existing SuperCode process with PID {pid}")
                            # Send SIGTERM signal
                            os.kill(pid, signal.SIGTERM)
                            # Give it a moment to terminate
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"Error killing process: {e}")
            
            # Check again after killing processes
            time.sleep(1)
            instance_checker = SingleInstanceChecker()
            if instance_checker.is_running():
                print("Could not terminate existing instance. Exiting.")
                sys.exit(1)
        
        # Initialize QApplication first
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer, QCoreApplication
        
        # Create QApplication instance
        qt_app = QApplication.instance()
        if not qt_app:
            qt_app = QApplication(sys.argv)
            
        # macOS specific settings to ensure windows can show
        # This is CRITICAL for menu bar apps to show windows
        try:
            from AppKit import NSApp, NSApplication, NSApplicationActivationPolicyRegular
            NSApplication.sharedApplication()
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
        except Exception as e:
            print(f"Warning: Could not set macOS activation policy: {e}")
        
        # Create the Rumps app
        app = SuperCodeApp()
        
        # Create a timer to process Qt events
        timer = QTimer()
        timer.timeout.connect(QCoreApplication.processEvents)
        timer.start(50)  # Process Qt events every 50ms
        
        # Set the initial interface name based on default IDE
        try:
            # Import command processor to get the default IDE
            from command_processor import CommandProcessor
            default_ide = os.getenv("DEFAULT_IDE", CommandProcessor.DEFAULT_IDE)
            
            # Set a descriptive initial interface name
            initial_interface = f"{default_ide.capitalize()}"
            app.set_current_interface(initial_interface)
        except Exception as e:
            print(f"Error setting initial interface name: {e}")
        
        try:
            # Run the rumps app (this will block)
            app.run()
        finally:
            # Clean up the instance checker socket when the app exits
            instance_checker.cleanup()
        
    except Exception as e:
        print(f"Error initializing SuperCode: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
