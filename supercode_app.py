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
from whisper_streaming import FastSpeechHandler
from command_processor import CommandProcessor
# Import the overlay manager
from overlay_manager import OverlayManager

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
                                          quit_button=rumps.MenuItem("Quit", key="q"))
        
        self.is_listening = False
        self.listen_thread = None
        self.handler = None
        
        # Use our new overlay manager instead of direct overlay
        self.overlay_manager = OverlayManager()
        # Set the close handler
        self.overlay_manager.set_close_handler(self.stop_from_overlay)
        # Set the start handler
        self.overlay_manager.set_start_handler(self.start_from_overlay)
        
        # Create menu items
        self.menu = [
            rumps.MenuItem("Start Listening", callback=self.toggle_listening, key="l"),
            None,  # Separator
            rumps.MenuItem("About", callback=self.show_about)
        ]
    
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
        
        # Create a new thread to run the whisper streaming handler
        self.listen_thread = threading.Thread(target=self.run_whisper_handler)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        # Get transcription service info
        use_openai_api = os.getenv("USE_OPENAI_API", "false").lower() == "true"
        service_name = "OpenAI Whisper API" if use_openai_api else "Google Speech Recognition"
        
        # Update the overlay status
        self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE)
        
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
            command_processor = EnhancedCommandProcessor(self.overlay_manager)
            
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


class EnhancedCommandProcessor(CommandProcessor):
    """
    A custom command processor that shows notifications and updates the overlay status.
    """
    def __init__(self, overlay_manager=None):
        super().__init__()
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
    
    # Override the audio capture loop to update the overlay
    def _audio_capture_loop(self):
        """Continuously capture audio and update the overlay"""
        print(f"Listening for activation word: '{self.activation_word}'\n")
        
        # Update overlay status
        if self.overlay_manager:
            self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE)
        
        # Open audio stream
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        # State tracking
        is_recording = False
        
        try:
            while not self.should_stop:
                # Get audio chunk - this is non-blocking and very fast
                chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                
                # We can't update audio levels with the current implementation
                # In a future implementation with IPC, we could pass audio data
                
                # Check if chunk contains speech
                contains_speech = self._is_speech(chunk)
                
                # State machine logic
                if contains_speech:
                    # Reset silence counter
                    self.silent_chunks = 0
                    
                    # Start recording if not already
                    if not is_recording:
                        is_recording = True
                        self.audio_buffer = []  # Clear buffer
                        print("Speech detected, recording...")
                        
                        # Update overlay status
                        if self.overlay_manager:
                            self.overlay_manager.update_status(self.overlay_manager.STATUS_RECORDING)
                    
                    # Add chunk to buffer
                    self.audio_buffer.append(chunk)
                else:
                    # No speech detected
                    if is_recording:
                        # Still in recording mode, count silence
                        self.silent_chunks += 1
                        self.audio_buffer.append(chunk)  # Keep recording silence too
                        
                        # Check if we've reached silence threshold
                        if self.silent_chunks >= self.silent_chunks_threshold:
                            # End of speech detected
                            is_recording = False
                            print("Silence threshold reached, processing audio...")
                            
                            # Update overlay status
                            if self.overlay_manager:
                                self.overlay_manager.update_status(self.overlay_manager.STATUS_TRANSCRIBING)
                
                            # Save audio to temp file for transcription
                            self._save_and_transcribe()
                    
                # Small sleep to prevent high CPU usage
                time.sleep(0.001)
        
        except Exception as e:
            print(f"Error in audio capture: {str(e)}")
            import traceback
            print(traceback.format_exc())
        finally:
            # Clean up
            stream.stop_stream()
            stream.close()

    # Override process_recognized_text to update overlay
    def _process_recognized_text(self, text):
        """Process recognized text and update overlay"""
        # Convert text to lowercase for consistent command detection
        text_lower = text.lower()
        
        # Check for stop command
        if self.activation_word in text_lower:
            commands = self.command_queue.process_text(text)
            
            # Check for stop command
            for command in commands:
                command_lower = command.lower()
                
                # Handle stop command
                if command_lower == "stop":
                    print("Stopping voice recognition via command")
                    if self.overlay_manager:
                        self.overlay_manager.update_status("Voice Recognition Stopped", "Stopped via voice command")
                    
                    # Execute the stop command to play audio feedback
                    if self.command_processor:
                        self.command_processor.execute_command("stop")
                    
                    # Call the stop callback if provided
                    if self.stop_callback:
                        # Use threading to avoid blocking
                        threading.Timer(1.0, self.stop_callback).start()
                    return
        
        # Regular command processing
        # Check if the activation word is in the text
        if self.activation_word in text_lower:
            # Process text and execute any commands found
            if self.command_processor:
                commands = self.command_queue.process_text(text)
                
                # Update overlay with commands if available
                if self.overlay_manager and commands:
                    cmd_text = ", ".join(commands)
                    self.overlay_manager.update_status(self.overlay_manager.STATUS_EXECUTING, cmd_text)
                    
                    # Execute commands and track results
                    for command in commands:
                        # Get the command type (first word)
                        command_type = command.split(" ")[0] if command else ""
                        
                        # Check if it's a known command type
                        if command_type not in ["type", "click", "learn", "change", "stop"]:
                            # Unknown command type - show special message
                            print(f"Unknown command type: '{command_type}'")
                            self.overlay_manager.update_status(
                                self.overlay_manager.STATUS_IDLE, 
                                f"[Ignored, unknown command] {command}"
                            )
                            # Schedule reset of overlay status after 3 seconds
                            threading.Timer(3.0, lambda: self.overlay_manager.update_status(
                                self.overlay_manager.STATUS_IDLE)).start()
                        else:
                            # Known command type - execute it
                            try:
                                self.command_processor.execute_command(command)
                            except Exception as e:
                                print(f"Error executing command: {e}")
                
                # Reset overlay status if no commands were found
                if self.overlay_manager and not commands:
                    self.overlay_manager.update_status(self.overlay_manager.STATUS_IDLE)
        else:
            # No activation word found - display as ignored
            if self.overlay_manager:
                # Truncate text if longer than 20 words
                words = text.split()
                if len(words) > 20:
                    truncated = " ".join(words[:20]) + "..."
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
            for line in ps_output.split('\n'):
                if 'python' in line and 'supercode_app.py' in line and 'ps aux' not in line:
                    # Extract the PID (second column in ps aux output)
                    try:
                        parts = [p for p in line.split() if p]
                        if len(parts) > 1:
                            pid = int(parts[1])
                            # Don't kill our own process
                            if pid != os.getpid():
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
