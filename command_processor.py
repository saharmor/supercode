#!/usr/bin/env python3
"""
Command processor for SuperCode application.
Handles the execution of commands from transcribed speech.
"""

import os
import pyautogui
import threading
import json
import time
from dotenv import load_dotenv

from pydantic import BaseModel
from typing import Literal, Dict, Any

from computer_use_utils import bring_to_front_window, detect_ide_with_gemini, get_active_window_monitor, get_coordinates_for_prompt, get_current_window_name
from utils import play_beep, enhance_user_prompt

load_dotenv()

class EnhancedPrompt(BaseModel):
    prompt: str
    requiredIntelligenceLevel: Literal["low", "medium", "high"]

class CommandProcessor:
    """
    Processes commands received from transcribed speech.
    Implements various actions like typing text, clicking, and learning UI elements.
    Supports multiple interfaces (Windsurf, lovable) with different command selectors.
    """
    # Default interface
    DEFAULT_IDE = 'cursor'
    # DEFAULT_IDE = 'lovable'
    
    def __init__(self, app=None):
        self.app = app  # Reference to the main app for interface name updates

        # Load interface configuration from JSON file
        self.interface_config = self._load_interface_config()
        
        self.current_interface = detect_ide_with_gemini(self.interface_config.keys())

        # Initialize actions_coordinates with nested structure
        # Format: {"interface_name": {"command_name": (x, y)}}
        self.actions_coordinates = {}
        
        # Custom user-defined buttons
        self.buttons = {}
        
        # Command tracking
        self.last_command_time = 0

        # Initialize action coordinates based on the current interface
        self.initialize_interface(self.current_interface)
        
        # Command history for tracking past commands
        self.command_history = []
        
        # Cascade monitoring thread
        self.interface_monitor_thread = None
    
    @staticmethod
    def read_interface_config():
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "interfaces.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading interface configuration: {e}")
            print("Using default configuration")
            # Return an empty dict as fallback
            return {}
    
    def _load_interface_config(self) -> Dict[str, Any]:
        """Load interface configuration from JSON file.
        
        Returns:
            dict: The interface configuration loaded from the JSON file
        """
        return self.read_interface_config()
    
    def initialize_interface(self, interface_name):
        """Initialize action coordinates for the specified interface
        
        Args:
            interface_name: The name of the interface to initialize ('windsurf', 'lovable')
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if interface_name not in self.interface_config:
            print(f"Interface {interface_name} not found in configuration")
            raise ValueError(f"Interface {interface_name} not found in configuration")
        
        self.current_project_name = get_current_window_name()
        self.interface_monitor_region = get_active_window_monitor() # TODO Fix, for now this will always return Primary screen

        # Initialize the interface if not already in actions_coordinates
        if interface_name not in self.actions_coordinates:
            self.actions_coordinates[interface_name] = {}

        # toggle the agent interface TODO check if it's open and avoid opening it again
        # if interface_name == "cursor":
        #     pyautogui.hotkey('command', 'i')
        # elif interface_name == "windsurf":
        #     pyautogui.hotkey('command', 'l')

        interface_commands = self.interface_config[interface_name]['commands']
        for cmd_name, cmd_data in interface_commands.items():
            coords = get_coordinates_for_prompt(cmd_data['llm_selector'], monitor=self.interface_monitor_region)
            if not coords:
                print(f"Error: No coordinates found for {cmd_name} in {interface_name} interface")
                os.system(f"say 'Error: No coordinates found for {interface_name} interface'. Make sure {interface_name} is open and in focus on primary screen and try again.")
                return False
            self.actions_coordinates[interface_name][cmd_name] = coords
        
        return True

    def focus_ide_window(self, project_name: str):
        return bring_to_front_window(self.interface_config.keys(), self.current_interface, project_name)
        
        
    def start_ide_monitoring(self, monitor, completion_callback=None):
        """
        Start a background thread that monitors the IDE state until it's done.
        Uses the monitor_ide_state function from monitor_ide_state.py.
        
        Args:
            monitor: Region to monitor for screenshots
            completion_callback: Optional callback function to call when monitoring completes
        """
        try:
            # Import the function here to avoid circular imports
            sys_path = os.path.dirname(os.path.abspath(__file__))
            if sys_path not in os.sys.path:
                os.sys.path.append(sys_path)
                
            from monitor_ide_state import monitor_coding_generation_state
            
            # Start monitoring in a background thread
            # Create the monitoring thread with correct arguments
            interface_state_prompt = self.interface_config[self.current_interface]['interface_state_prompt']
            self.interface_monitor_thread = threading.Thread(
                target=monitor_coding_generation_state,
                args=(interface_state_prompt, monitor, 2.0, "screenshots", self.current_interface, completion_callback)
            )
            self.interface_monitor_thread.daemon = True
            self.interface_monitor_thread.start()
            print(f"Started {self.current_interface} state monitoring in background")
        except Exception as e:
            print(f"Error starting coding interface monitoring: {e}")
            
    
    
    def change_interface(self, command_params):
        # TODO handle cases where changing to the same project name
        change_params = command_params.lower().strip().split()
        target_interface = change_params[0]
        for interface_name in self.interface_config.keys():
            if target_interface in self.interface_config[interface_name].get("transcribed_similar_words", []):
                target_interface = interface_name
        
        if target_interface not in self.interface_config.keys():
            print(f"Unknown interface: '{target_interface}'. Valid options are {self.interface_config.keys()}")
            play_beep(1200, 1000)  # Error beep
            return False
        
        project_name = " ".join(change_params[1:])
        bring_to_front_window(self.interface_config.keys(), target_interface, project_name)
        self.current_project_name = get_current_window_name()

        success = self.initialize_interface(target_interface)
        if success:
            print(f"\n==== INTERFACE CHANGED TO: '{target_interface.upper()}' ====\n")
            
            # Update the overlay manager with the new interface name (if available via app)
            if hasattr(self, 'app') and self.app:
                # Create a display name combining interface and project
                display_name = target_interface
                if self.current_project_name:
                    display_name = f"{target_interface} - {self.current_project_name}"
                
                print(f"Updating interface display name to: {display_name}")
                self.app.set_current_interface(display_name.capitalize())
            
            # Audio notification
            if project_name:
                os.system(f"say 'Development environment changed to {target_interface} project {project_name}'")
            else:
                os.system(f"say 'Development environment changed to {target_interface}'")
            self.current_interface = target_interface
        else:
            print(f"Error: Could not initialize {target_interface} interface")
            play_beep(1200, 1000)
            return False
            
        
    def execute_command(self, command_text, completion_callback=None):
        """
        Execute a command based on the transcribed text.
        Override this method to implement your own command execution logic.
        
        Args:
            command_text: The text of the command to execute.
            completion_callback: Optional callback to call when command execution is complete.
            
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        print(f"\n==== EXECUTING COMMAND: '{command_text}' ====\n")
        
        self.command_history.append(command_text)
        self.last_command_time = time.time()  # Track when the command was executed
        
        command_type = command_text.split(" ")[0]
        command_params = " ".join(command_text.split(" ")[1:])
        
        if command_type == "type":
            # First, ensure the correct window is focused
            focus_success = self.focus_ide_window(self.current_project_name)
            if not focus_success:
                print(f"Warning: Could not focus the {self.current_interface} window")
                # Continue anyway, but it might not type in the right place
            
            prompt = command_params
            if os.getenv("ENHANCE_PROMPT") == "true":
                enhanced_prompt = enhance_user_prompt(command_params)
                if not enhanced_prompt.prompt or enhanced_prompt.prompt == 'None':
                    print("Invalid coding prompt - please provide a prompt that makes sense for coding tasks :D")
                    # play sound to notify user
                    play_beep(1200, 1000)
                    return False
                
                prompt = enhanced_prompt.prompt
            
            if self.current_interface in self.actions_coordinates and command_type in self.actions_coordinates[self.current_interface]:
                coords = self.actions_coordinates[self.current_interface][command_type]
                pyautogui.moveTo(coords[0], coords[1])
                pyautogui.click(button="left")
                pyautogui.write(prompt)
                pyautogui.press("enter")
            else:
                print(f"Error: No coordinates found for {command_type} in {self.current_interface} interface")
                play_beep(1200, 1000)
                return False
            
            print(f"Starting {self.current_interface} monitoring since a 'type' command was detected")
            if completion_callback:
                self.start_ide_monitoring(monitor=self.interface_monitor_region, completion_callback=completion_callback)
            else:
                print("Warning: No completion callback provided for 'type' command")
                self.start_ide_monitoring(monitor=self.interface_monitor_region)
            return True
        elif command_type == "click":
            # First, ensure the correct window is focused
            focus_success = self.focus_ide_window(self.current_project_name)
            if not focus_success:
                print(f"Warning: Could not focus the {self.current_interface} window")
                # Continue anyway, but it might not click in the right place
            
            command_params = command_params.split(" ")[0]
            if command_params not in self.buttons:
                print(f"Error: No button named '{command_params}' has been learned")
                play_beep(1200, 1000)
                return False
                
            pyautogui.moveTo(self.buttons[command_params][0], self.buttons[command_params][1])
            pyautogui.click(button="left")
            return True
        elif command_type == "learn": # only buttons for now
            btn_name = command_params.split(" ")[0]
            btn_selector = " ".join(command_params.split(" ")[1:])
            self.buttons[btn_name] = get_coordinates_for_prompt(btn_selector, monitor=self.interface_monitor_region)
        elif command_type == "change":
            self.change_interface(command_params)
        elif command_type == "stop":
            # Stop command is handled in EnhancedSpeechHandler
            print("Stopping voice recognition")
            os.system("say 'Voice recognition stopped'")
            return True
        else:
            print(f"Unknown command type: '{command_type}'")
            return False

        return True
        

class CommandQueue:
    """
    Handles the queuing and processing of commands from transcribed speech.
    """
    def __init__(self, activation_word="activate", command_processor=None):
        """
        Initialize the command queue.
        
        Args:
            activation_word: The word that activates command listening (default: "activate")
            command_processor: An optional CommandProcessor instance to execute commands
        """
        self.activation_word = activation_word.lower()
        self.command_processor = command_processor or CommandProcessor()
        self.audio_handler = None  # Will be set by FastSpeechHandler
        
    def set_audio_handler(self, audio_handler):
        """
        Set a reference to the audio handler for callbacks.
        
        Args:
            audio_handler: The audio handler instance.
        """
        self.audio_handler = audio_handler
        
    def process_text(self, text):
        """
        Process recognized text to extract commands.
        If multiple activation words are present, split into separate commands.
        
        Args:
            text: The recognized text to process.
            
        Returns:
            list: A list of extracted commands.
        """
        commands = []
        
        # Check for activation word
        # Split text into words and check if activation word exists as a separate word
        if self.activation_word in text.lower().split():
            # Split the text by the activation word
            parts = text.split(self.activation_word)
            
            # Process each part after an activation word
            commands_found = False
            
            for i in range(1, len(parts)):  # Skip the first part (before first activation word)
                command = parts[i].strip()
                if command:  # Only process non-empty commands
                    commands_found = True
                    print(f"\n*** ACTIVATION WORD DETECTED! ***")
                    print(f"Command {i} detected: '{command}'")
                    commands.append(command)
                    print(f"\n==== COMMAND CAPTURED: '{command}' ====\n")
            
            if not commands_found:
                # Activation word(s) detected but no commands
                print(f"\n*** ACTIVATION WORD DETECTED! ***")
                print("No command found after activation word")
        
        return commands
        
    def is_empty(self):
        """
        Check if there are any pending commands.
        
        Returns:
            bool: True if there are no commands, False otherwise.
        """
        # The CommandQueue doesn't actually maintain a queue of commands
        # Instead, we'll look at the command processor's command history
        if hasattr(self.command_processor, 'command_history') and self.command_processor.command_history:
            last_command_time = getattr(self.command_processor, 'last_command_time', 0)
            if last_command_time and (time.time() - last_command_time) < 5:
                # If a command was processed in the last 5 seconds, consider queue not empty
                return False
        return True
    
    def execute_commands(self, commands, completion_callback=None):
        """
        Execute a list of commands.
        
        Args:
            commands: A list of command strings to execute.
            completion_callback: Optional callback to call when all commands have completed execution.
        """
        for command in commands:
            if command:
                try:
                    self.command_processor.execute_command(command, completion_callback)
                except Exception as e:
                    print(f"Error executing command: {str(e)}")
                    # If there's an error and we have a callback, call it
                    if completion_callback:
                        completion_callback()
