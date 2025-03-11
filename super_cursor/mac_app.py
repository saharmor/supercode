import rumps
import threading
import time
import os
import sys
from dotenv import load_dotenv

# Add root directory to path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import SuperSurf modules
try:
    from super_surf.transcription import VoiceTranscriber
    from super_surf.surf_controller import SurfController
    from super_surf.utils import focus_surf_app
    from super_surf.help_commands import show_commands_help
except ImportError as e:
    print(f"Error in absolute import: {str(e)}")
    
    # Try relative import as fallback
    try:
        from .transcription import VoiceTranscriber
        from .surf_controller import SurfController
        from .utils import focus_surf_app
        from .help_commands import show_commands_help
    except ImportError as e:
        raise ImportError(f"Failed to import essential modules: {str(e)}")

# Load environment variables
load_dotenv()

class SuperSurfApp(rumps.App):
    def __init__(self):
        """Initialize the Super Surf app"""
        # Use only text name, no icon, no additional text
        super(SuperSurfApp, self).__init__("SuperSurf", 
                                           icon=None,  # Explicitly set icon to None
                                           title=None,  # Don't use a template title
                                           quit_button=rumps.MenuItem("Quit", key="q"))
        
        # Initialize state
        self.is_listening = False
        self.is_first_run = not os.path.exists(os.path.expanduser("~/.SuperSurf/has_run"))
        self.listen_thread = None
        
        # Create menu items with simple structure
        self.menu = [
            rumps.MenuItem("Start Listening", callback=self.toggle_listening, key="l"),
            None,  # Separator
            rumps.MenuItem("Basic Commands", callback=self.show_basic_commands),
            rumps.MenuItem("Navigation Commands", callback=self.show_navigation_commands),
            rumps.MenuItem("Editing Commands", callback=self.show_editing_commands),
            rumps.MenuItem("IDE Commands", callback=self.show_ide_commands),
            None,  # Separator
            rumps.MenuItem("Settings", callback=self.open_settings),
            None,  # Separator
            rumps.MenuItem("Help", callback=self.show_how_to_use),
            rumps.MenuItem("About", callback=self.show_about)
        ]
        
        # Initialize the transcriber
        try:
            # Use environment variables for configuration
            model_name = os.getenv("WHISPER_MODEL_SIZE", "base")
            use_ensemble = os.getenv("USE_ENSEMBLE", "True").lower() == "true"
            
            # Get device index from environment
            device_index = None
            if os.getenv("AUDIO_DEVICE_INDEX"):
                try:
                    device_index = int(os.getenv("AUDIO_DEVICE_INDEX"))
                except ValueError:
                    print(f"Invalid AUDIO_DEVICE_INDEX: {os.getenv('AUDIO_DEVICE_INDEX')}")
            
            # Initialize the transcriber with local Whisper model
            self.transcriber = VoiceTranscriber(
                model_name=model_name,
                use_ensemble=use_ensemble,
                device_index=device_index
            )
            
            print(f"Initialized transcriber with model: {model_name}")
        except Exception as e:
            print(f"Error initializing transcriber: {e}")
            self.transcriber = None
            
        self.controller = SurfController()
        
        # Show first-run tutorial if needed
        if self.is_first_run:
            # Schedule the tutorial to appear after the app has fully loaded
            # Use a threading.Timer instead of rumps.timer.schedule which has compatibility issues
            timer = threading.Timer(1.0, self.show_first_run_tutorial)
            timer.daemon = True
            timer.start()
            
            # Create a directory to store app data if it doesn't exist
            os.makedirs(os.path.expanduser("~/.SuperSurf"), exist_ok=True)
            
            # Mark as run
            with open(os.path.expanduser("~/.SuperSurf/has_run"), "w") as f:
                f.write("1")

    def show_first_run_tutorial(self, _=None):
        """Show a welcome and tutorial for first-time users"""
        welcome_response = rumps.alert(
            title="Welcome to SuperSurf!",
            message="SuperSurf allows you to control Windsurf IDE with voice commands.\n\nWould you like to take a quick tour of the features?",
            ok="Yes, show me around",
            cancel="Maybe later"
        )
        
        if welcome_response == 1:  # User clicked "Yes"
            self.show_tutorial()
        else:
            rumps.notification(
                "SuperSurf", 
                "Ready to use", 
                "Click the SuperSurf icon to start using voice commands"
            )

    def toggle_listening(self, sender):
        """Toggle the listening state with visual feedback"""
        if self.is_listening:
            self.stop_listening()
            sender.title = "Start Listening"
            # Just set the title to SuperSurf, no additional text
            self.title = "SuperSurf"
        else:
            self.start_listening()
            sender.title = "Stop Listening"
            # Use a different colored title but keep just SuperSurf
            self.title = "SuperSurf"
    
    def start_listening(self):
        """Start listening for voice commands with enhanced feedback"""
        if self.is_listening:
            return
            
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self.process_voice_commands)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        rumps.notification("SuperSurf", "Voice Control Active", "Say commands starting with 'Surf'")
        
        # Keep title clean - just SuperSurf
        self.title = "SuperSurf"
    
    def stop_listening(self):
        """Stop listening for voice commands with enhanced feedback"""
        if not self.is_listening:
            return
            
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=1.0)
            
        rumps.notification("SuperSurf", "Voice Control Paused", "Click 'Start Listening' to resume")
        
        # Keep title clean - just SuperSurf
        self.title = "SuperSurf"

    def process_voice_commands(self):
        """Process voice commands in a loop"""
        while self.is_listening:
            try:
                print("\n--- New recording session ---")
                self.title = "SuperSurf"  # Keep title clean
                
                # Record audio
                try:
                    self.transcriber.start_recording()
                    time.sleep(3)
                    self.transcriber.stop_recording()
                except Exception as e:
                    print(f"Error during recording: {e}")
                    time.sleep(1)
                    continue
                
                self.title = "SuperSurf"  # Keep title clean
                try:
                    transcription = self.transcriber.transcribe_audio()
                except Exception as e:
                    print(f"Error during transcription: {e}")
                    time.sleep(1)
                    continue
                
                if transcription:
                    print(f"Processing transcription: '{transcription}'")
                    
                    # Check for help command
                    if "surf help" in transcription.lower():
                        try:
                            self.show_commands_help()
                        except Exception as e:
                            print(f"Error showing help: {e}")
                        continue
                    
                    # Process the command if it contains the keyword "surf"
                    words = transcription.lower().split()
                    if "surf" in words:
                        self.title = "SuperSurf"  # Keep title clean
                        
                        # Try to focus the Windsurf IDE window
                        try:
                            focus_surf_app()
                        except Exception as e:
                            print(f"Error focusing Windsurf app: {e}")
                        
                        # Process the command
                        try:
                            success = self.controller.process_command(transcription)
                        except Exception as e:
                            print(f"Error processing command: {e}")
                            success = False
                        
                        # Provide visual feedback
                        try:
                            self.provide_visual_feedback(transcription, success)
                        except Exception as e:
                            print(f"Error providing feedback: {e}")
                    else:
                        print(f"Ignoring transcription as it doesn't contain 'surf': '{transcription}'")
                        self.title = "SuperSurf"  # Reset menu bar icon
                else:
                    print("No transcription received")
                    self.title = "SuperSurf"  # Reset menu bar icon
                
                # Small delay between recording sessions
                time.sleep(1)
            except Exception as e:
                print(f"Error in process_voice_commands: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)
    
    def provide_visual_feedback(self, command, success=True):
        """Provide visual feedback for command execution"""
        if success:
            # Show success notification
            rumps.notification("Command Executed", 
                             command, 
                             "Executing command...")
            self.title = "SuperSurf"  # Keep title clean
        else:
            # Show failure notification
            rumps.notification("Command Not Recognized", 
                             command, 
                             "Please try again.")
            self.title = "SuperSurf"  # Keep title clean
            
    def test_keyboard(self, _):
        """Test keyboard functionality"""
        focus_surf_app()
        self.controller.test_keyboard()
        rumps.notification("SuperSurf", "Keyboard Test", "Sent test keyboard input")
    
    def show_commands_help(self, _=None):
        """Show all available commands"""
        show_commands_help()
    
    def show_basic_commands(self, _):
        """Show basic commands"""
        basic_commands = """
BASIC COMMANDS

- "Surf type [text]" - Type specified text
- "Surf enter" - Press Enter key
- "Surf tab" - Press Tab key
- "Surf save" - Save current file (Cmd+S)
- "Surf undo" - Undo last action (Cmd+Z)
- "Surf delete" - Delete current line
        """
        rumps.alert(title="Basic Commands", message=basic_commands, ok="Got it!")
    
    def show_navigation_commands(self, _):
        """Show navigation commands"""
        navigation_commands = """
NAVIGATION COMMANDS

- "Surf find [text]" - Search for text
- "Surf next" - Go to next result
- "Surf previous" - Go to previous result
- "Surf go to line [number]" - Go to specific line
- "Surf top" - Go to file top
- "Surf bottom" - Go to file bottom
        """
        rumps.alert(title="Navigation Commands", message=navigation_commands, ok="Got it!")
    
    def show_how_to_use(self, _):
        """Show how to use information"""
        how_to_use = """
HOW TO USE SuperSurf

1. Click "Start Listening" in the menu
2. Speak commands beginning with "Surf"
3. The app will transcribe and execute your commands
4. To stop, click "Stop Listening" in the menu

Example: Say "Surf type hello world" to type "hello world"

Tips:
- Speak clearly and at a normal pace
- Wait for the "Command Recognized" notification
- Check the status in the menu bar
        """
        rumps.alert(title="How to Use", message=how_to_use, ok="Got it!")
    
    def show_about(self, _):
        """Show about information"""
        about = """
ABOUT SuperSurf

Version: 0.1.0
A voice control application for Windsurf IDE

SuperSurf lets you control Windsurf IDE using voice commands,
making your coding experience more efficient and hands-free.

Features:
- Voice command recognition
- Intelligent command processing
- Visual feedback
- Noise reduction
- Support for non-native English speakers
        """
        rumps.alert(title="About SuperSurf", message=about, ok="Got it!")
    
    def show_editing_commands(self, _):
        """Show editing-specific commands"""
        editing_commands = """
EDITING COMMANDS

Text Selection:
• "Surf select all" - Select all text (⌘A)
• "Surf select line" - Select current line

Deletion:
• "Surf delete" - Delete current line
• "Surf backspace" - Delete previous character

Formatting:
• "Surf format" - Format current file
• "Surf indent" - Indent current line
• "Surf outdent" - Outdent current line
• "Surf comment" - Toggle comment on current line

Basic Editing:
• "Surf duplicate" - Duplicate current line
• "Surf cut" - Cut selection (⌘X)
• "Surf copy" - Copy selection (⌘C)
• "Surf paste" - Paste from clipboard (⌘V)
        """
        rumps.alert(title="Editing Commands", message=editing_commands, ok="Close")

    def show_ide_commands(self, _):
        """Show IDE-specific commands"""
        ide_commands = """
IDE COMMANDS

Panels:
• "Surf terminal" - Toggle terminal panel
• "Surf explorer" - Toggle file explorer
• "Surf problems" - Toggle problems panel

Views:
• "Surf split" - Split editor
• "Surf close" - Close current file
• "Surf new file" - Create new file

Features:
• "Surf run" - Run current file
• "Surf debug" - Debug current file
• "Surf git" - Show git commands
        """
        rumps.alert(title="IDE Commands", message=ide_commands, ok="Close")
        
    def open_settings(self, _):
        """Open simplified settings window with functional options"""
        # Create a settings window with the most important options
        response = rumps.alert(
            title="SuperSurf Settings",
            message="Select a setting to configure:",
            ok="Audio",
            cancel="Cancel",
            other=["Commands", "Test Mic"]
        )
        
        # Handle response based on button clicked
        if response == 1:  # Audio button clicked
            self.configure_audio()
        elif response == 2:  # Commands button clicked
            self.configure_commands()
        elif response == 3:  # Test Mic button clicked
            self.check_microphone()
    
    def configure_audio(self):
        """Configure audio settings"""
        # Get current mic info
        try:
            device_info = self.transcriber.get_device_info() if hasattr(self.transcriber, 'get_device_info') else "Default system microphone"
        except:
            device_info = "Default system microphone" 
            
        # Create a simple audio settings dialog
        msg = f"""Current Settings:
• Microphone: {device_info}
• Sample Rate: 44.1 kHz
• Recording Duration: 3 seconds
• Noise Reduction: Enabled

To change microphone, use System Preferences."""
        
        rumps.alert(title="Audio Settings", message=msg, ok="Close")
    
    def configure_commands(self):
        """Configure command settings"""
        # Create a simple command settings dialog
        msg = """Current Settings:
• Voice Command Prefix: "Surf"
• Recognition: Optimized with enhanced accuracy
• Fuzzy Matching: Enabled

Available Command Categories:
• Basic Commands
• Navigation Commands
• Editing Commands
• IDE Commands"""
        
        response = rumps.alert(
            title="Command Settings",
            message=msg,
            ok="View All Commands",
            cancel="Close"
        )
        
        if response == 1:  # View All Commands clicked
            self.show_commands_help()
    
    def check_microphone(self, _=None):
        """Check microphone status and provide feedback"""
        # Display checking notification
        rumps.notification("SuperSurf", "Testing Microphone", "Recording test audio...")
        
        try:
            # Use the transcriber to test the microphone
            self.transcriber.start_recording()
            time.sleep(1)  # Record for 1 second to test
            self.transcriber.stop_recording()
            
            # Get the device info
            device_info = self.transcriber.get_device_info() if hasattr(self.transcriber, 'get_device_info') else "Default system microphone"
            
            mic_status = f"""MICROPHONE STATUS: OK

Active Device: {device_info}

The microphone is working properly.

For best recognition results:
• Speak clearly with a pause after "Surf"
• Reduce background noise
• Use simple, direct command phrases"""
            
            rumps.alert(title="Microphone Check", message=mic_status, ok="Got it")
            
        except Exception as e:
            error_msg = f"""MICROPHONE ERROR

Unable to access microphone: {str(e)}

Please check:
• System Preferences → Security & Privacy → Microphone
• Other apps using the microphone
• Hardware connections
• Try restarting SuperSurf"""
            
            rumps.alert(title="Microphone Check", message=error_msg, ok="Got it")
            
    def show_tutorial(self, _=None):
        """Show a tutorial for users"""
        tutorial_steps = [
            "Welcome to SuperSurf! This tutorial will help you get started.",
            "SuperSurf lets you control Windsurf IDE with your voice commands.",
            "To start, click on the SuperSurf icon in the menu bar and select 'Start Listening'.",
            "Try saying 'Surf type hello world' to type text.",
            "For code editing, try commands like 'Surf select all' or 'Surf format'.",
            "For navigation, use commands like 'Surf find text' or 'Surf go to line 42'.",
            "You can find all available commands in the command menus.",
            "For help at any time, say 'Surf help' or use the Help menu.",
            "Let's get started!"
        ]
        
        for i, step in enumerate(tutorial_steps):
            response = rumps.alert(title=f"Tutorial ({i+1}/{len(tutorial_steps)})", 
                                 message=step, 
                                 ok="Next" if i < len(tutorial_steps)-1 else "Finish",
                                 cancel="Skip Tutorial" if i == 0 else None)
            
            # If user clicked cancel, break out of the loop
            if response != 1:  # 1 is the OK button
                break

    def configure_api_key(self):
        """Show information about the local Whisper model"""
        # Create a window to inform the user that API key is no longer needed
        api_key_window = rumps.Window(
            title="Local Whisper Information",
            message="SuperSurf uses the local Whisper model for transcription.\n\nNo API key or internet connection needed for voice recognition.",
            ok="Great!",
            cancel=None
        )
        api_key_window.run()