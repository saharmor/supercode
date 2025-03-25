#!/usr/bin/env python3
"""
Command processor for SuperCode application.
Handles the execution of commands from transcribed speech.
"""

import os
import pyautogui
import threading
import json
from dotenv import load_dotenv

from pydantic import BaseModel
from typing import Literal, Dict, Any

from computer_use_utils import get_coordinates_for_prompt
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
    DEFAULT_IDE = 'windsurf'
    # DEFAULT_IDE = 'lovable'
    
    def __init__(self):
        self.current_interface = os.getenv("DEFAULT_IDE", self.DEFAULT_IDE)
        
        # Load interface configuration from JSON file
        self.interface_config = self._load_interface_config()
        
        # Initialize actions_coordinates with nested structure
        # Format: {"interface_name": {"command_name": (x, y)}}
        self.actions_coordinates = {}
        
        # Custom user-defined buttons
        self.buttons = {}

        # Initialize action coordinates based on the current interface
        self.initialize_interface(self.current_interface)
        
        # Command history for tracking past commands
        self.command_history = []
        
        # Cascade monitoring thread
        self.interface_monitor_thread = None
    
    def _load_interface_config(self) -> Dict[str, Any]:
        """Load interface configuration from JSON file.
        
        Returns:
            dict: The interface configuration loaded from the JSON file
        """
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "interfaces.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading interface configuration: {e}")
            print("Using default configuration")
            # Return an empty dict as fallback
            return {}
    
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
        
        # Initialize the interface if not already in actions_coordinates
        if interface_name not in self.actions_coordinates:
            self.actions_coordinates[interface_name] = {}
            
        interface_commands = self.interface_config[interface_name]['commands']
        for cmd_name, cmd_data in interface_commands.items():
            coords = get_coordinates_for_prompt(cmd_data['llm_selector'])
            self.actions_coordinates[interface_name][cmd_name] = coords
        
        return True

        
    def start_ide_monitoring(self):
        """
        Start a background thread that monitors the IDE state until it's done.
        Uses the monitor_ide_state function from monitor_ide_state.py.
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
                args=(interface_state_prompt, 2.0, "screenshots", self.current_interface)
            )
            self.interface_monitor_thread.daemon = True
            self.interface_monitor_thread.start()
            print(f"Started {self.current_interface} state monitoring in background")
        except Exception as e:
            print(f"Error starting coding interface monitoring: {e}")
            
    
    
    def execute_command(self, command_text):
        """
        Execute a command based on the transcribed text.
        Override this method to implement your own command execution logic.
        
        Args:
            command_text: The text of the command to execute.
            
        Returns:
            bool: True if the command was executed successfully, False otherwise.
        """
        print(f"\n==== EXECUTING COMMAND: '{command_text}' ====\n")
        
        self.command_history.append(command_text)
        
        command_type = command_text.split(" ")[0]
        command_params = " ".join(command_text.split(" ")[1:])
        
        if command_type == "type":
            # enhanced_prompt = enhance_user_prompt(command_params)
            # if not enhanced_prompt.prompt or enhanced_prompt.prompt == 'None':
            #     print("Invalid coding prompt - please provide a prompt that makes sense for coding tasks :D")
            #     # play sound to notify user
            #     play_beep(1200, 1000)
            #     return False
            
            if self.current_interface in self.actions_coordinates and command_type in self.actions_coordinates[self.current_interface]:
                coords = self.actions_coordinates[self.current_interface][command_type]
                pyautogui.moveTo(coords[0], coords[1])
                pyautogui.click(button="left")
                # pyautogui.write(enhanced_prompt.prompt)
                #TODO REVERT!
                pyautogui.write(command_params)
                # pyautogui.press("enter")
            else:
                print(f"Error: No coordinates found for {command_type} in {self.current_interface} interface")
                play_beep(1200, 1000)
                return False
            
            print(f"Starting {self.current_interface} monitoring since a 'type' command was detected")
            self.start_ide_monitoring()
        elif command_type == "click":
            command_params = command_params.split(" ")[0]
            pyautogui.moveTo(self.buttons[command_params][0], self.buttons[command_params][1])
            pyautogui.click(button="left")
        elif command_type == "learn": # only buttons for now
            btn_name = command_params.split(" ")[0]
            btn_selector = " ".join(command_params.split(" ")[1:])
            self.buttons[btn_name] = get_coordinates_for_prompt(btn_selector)
        elif command_type == "change":
            target_interface = command_params.lower().strip()
            for interface_name in self.interface_config.keys():
                if target_interface in self.interface_config[interface_name].get("transcribed_similar_words", []):
                    target_interface = interface_name
                    
            success = self.initialize_interface(target_interface)
            if success:
                print(f"\n==== INTERFACE CHANGED TO: '{target_interface.upper()}' ====\n")
                os.system(f"say 'Voice changed to {target_interface}'")
                self.current_interface = target_interface
            else:
                print(f"Unknown interface: '{interface_name}'. Valid options are 'windsurf' or 'lovable'")
                play_beep(1200, 1000)  # Error beep
                return False
            
            self.current_interface = target_interface
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
        
    def execute_commands(self, commands):
        """
        Execute a list of commands.
        
        Args:
            commands: A list of command strings to execute.
        """
        for command in commands:
            if command:
                try:
                    self.command_processor.execute_command(command)
                except Exception as e:
                    print(f"Error executing command: {str(e)}")
