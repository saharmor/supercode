#!/usr/bin/env python3
"""
SuperCode - A simple macOS menu bar app for whisper_streaming.py
This app provides a single toggle button to start/stop the whisper streaming functionality.
"""

import rumps
import threading
import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Import the whisper streaming functionality and command processing
from whisper_streaming import FastSpeechHandler
from command_processor import CommandProcessor

class SuperCodeApp(rumps.App):
    def __init__(self):
        """Initialize the Whisper Menu App"""
        super(SuperCodeApp, self).__init__("SuperCode", 
                                          icon=None,
                                          title=None,
                                          quit_button=rumps.MenuItem("Quit", key="q"))
        
        self.is_listening = False
        self.listen_thread = None
        self.handler = None
        
        # Create menu items with simple structure - just one toggle button
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
        else:
            self.start_listening()
            sender.title = "Stop Listening"
            self.title = "SuperCode"
    
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
            
        rumps.notification("SuperCode", "Voice Recognition Stopped", "Click 'Start Listening' to resume")
    
    def run_whisper_handler(self):
        """Run the whisper streaming handler in a separate thread"""
        try:
            # Create a custom command processor that shows notifications
            command_processor = MenuBarCommandProcessor()
            
            # Create and start the fast speech handler
            self.handler = FastSpeechHandler(
                activation_word="activate",
                silence_duration=3,
                command_processor=command_processor
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
    
    def show_about(self, _):
        """Show about information"""
        about = """
ABOUT SuperCode

A simple macOS menu bar app for whisper_streaming.py.
This app provides a single toggle button to start/stop 
the whisper streaming functionality.

Usage:
1. Click "Start Listening" in the menu
2. Speak commands beginning with "activate"
3. The app will transcribe and execute your commands
4. To stop, click "Stop Listening" in the menu

Example: Say "surf hello world"
        """
        rumps.alert(title="About SuperCode", message=about, ok="Got it!")


class MenuBarCommandProcessor(CommandProcessor):
    """
    A custom command processor that shows notifications in the menu bar.
    """
    def execute_command(self, command_text):
        """
        Execute a command and show a notification.
        """
        # Call the parent method to execute the command
        result = super().execute_command(command_text)
        
        # Show a notification
        rumps.notification("SuperCode", "Command Detected", f"'{command_text}'")
        
        return result


def main():
    """Initialize and start the SuperCode app"""
    try:
        # Initialize and run the app
        app = SuperCodeApp()
        app.run()
    except Exception as e:
        print(f"Error initializing SuperCode: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
