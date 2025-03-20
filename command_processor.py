#!/usr/bin/env python3
"""
Command processor for SuperSurf application.
Handles the execution of commands from transcribed speech.
"""

import os
import pyautogui
import threading
from dotenv import load_dotenv

from pydantic import BaseModel
from typing import Literal

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
    SUPPORTED_INTERFACES = ["windsurf", "lovable"]
    
    INTERFACE_CONFIG = {
    "windsurf": {
        "commands": {
            "type": {
                "llm_selector": "Input box for the Cascade agent which starts with 'Ask anything'. Usually, it's in the right pane of the screen",
                "description": "Text input field for sending commands to Cascade"
            },
        },
        "interface_state_prompt": 
            "You are analyzing a screenshot of the Cascade AI coding assistant interface. You only care about the right panel that says 'Cascade | Write Mode'. IGNORE ALL THE REST OF THE SCREENSHOT. " 
                "Determine the Cascade's current state based on visual cues in the right pane of the image. "
                    "Return the following state for the following scenarios: "
                    "'user_input_required' if there is an accept and reject button or 'waiting on response' text in the right handside pane"
                    "'done' if there is a thumbs-up or thumbs-down icon in the right handside pane"
                    "'still_working' for all other cases"
                    "IMPORTANT: Respond with a JSON object containing exactly these two keys: "
                "- 'interface_state': must be EXACTLY ONE of these values: 'user_input_required', 'still_working', or 'done' "
                    "- 'reasoning': a brief explanation for your decision "
                    "Example response format: "
                    "```json "
                    "{ "
                "  \"interface_state\": \"done\", "
                    "  \"reasoning\": \"I can see a thumbs-up/thumbs-down icons in the right panel\" "
                    "} "
                    "``` "
                    "Only analyze the right panel and provide nothing but valid JSON in your response."
        
    },
    "lovable": {
        "commands": {
            "type": {
                "llm_selector": "The main text input field at the bottom left of the lovable interface which says 'Ask lovable...'",
                "description": "Text input field for sending messages to lovable"
            },
        },
        "interface_state_prompt":
            "You are analyzing a screenshot of the Lovable coding assistant interface. You only care about the left panel chat panel for sending messages to Lovable. IGNORE ALL THE REST OF THE SCREENSHOT. " 
                "Determine the Lovable's current state based on visual cues in the left pane of the image. "
                    "Return the following state for the following scenarios: "
                    # "'user_input_required' if there is an accept and reject button or 'waiting on response' text in the left handside pane"
                    "'still_working' if you see a small white circle above the chat input or a stop button at the bottom left of the input box"
                    "'done' for all other cases"
                    "IMPORTANT: Respond with a JSON object containing exactly these two keys: "
                "- 'interface_state': must be EXACTLY ONE of these values: 'user_input_required', 'still_working', or 'done' "
                    "- 'reasoning': a brief explanation for your decision "
                    "Example response format: "
                    "```json "
                    "{ "
                "  \"interface_state\": \"still_working\", "
                    "  \"reasoning\": \"I can see a stop button or spinner in the left panel\" "
                    "} "
                    "``` "
                    "Only analyze the left panel and provide nothing but valid JSON in your response."
    }
}


    def __init__(self):
        self.current_interface = CommandProcessor.DEFAULT_IDE
        self.interface_config = CommandProcessor.INTERFACE_CONFIG
        
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

        
    def start_cascade_monitoring(self):
        """
        Start a background thread that monitors the Cascade state until it's done.
        Uses the monitor_cascade_state function from bg_screenshot_test.py.
        """
        try:
            # Import the function here to avoid circular imports
            sys_path = os.path.dirname(os.path.abspath(__file__))
            if sys_path not in os.sys.path:
                os.sys.path.append(sys_path)
                
            from bg_screenshot_test import monitor_coding_generation_state
            
            # Start monitoring in a background thread
            # Create the monitoring thread with correct arguments
            interface_state_prompt = self.interface_config[self.current_interface]['interface_state_prompt']
            self.interface_monitor_thread = threading.Thread(
                target=monitor_coding_generation_state,
                args=(interface_state_prompt, 3.0, "screenshots", self.current_interface)
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
        
        # Add command to history
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
                pyautogui.press("enter")
            else:
                print(f"Error: No coordinates found for {command_type} in {self.current_interface} interface")
                play_beep(1200, 1000)
                return False
            
            print("Starting Cascade monitoring since a 'type' command was detected")
            self.start_cascade_monitoring()
        elif command_type == "click":
            command_params = command_params.split(" ")[0]
            pyautogui.moveTo(self.buttons[command_params][0], self.buttons[command_params][1])
            pyautogui.click(button="left")
        elif command_type == "learn": # only buttons for now
            btn_name = command_params.split(" ")[0]
            btn_selector = " ".join(command_params.split(" ")[1:])
            self.buttons[btn_name] = get_coordinates_for_prompt(btn_selector)
        elif command_type == "change":
            # Command to change the current interface
            interface_name = command_params.lower().strip()
            if interface_name in CommandProcessor.SUPPORTED_INTERFACES:
                success = self.initialize_interface(interface_name)
                if success:
                    print(f"\n==== INTERFACE CHANGED TO: '{interface_name.upper()}' ====\n")
                else:
                    print(f"Failed to change interface to {interface_name}")
                    play_beep(1200, 1000)  # Error beep
            else:
                print(f"Unknown interface: '{interface_name}'. Valid options are 'windsurf' or 'lovable'")
                play_beep(1200, 1000)  # Error beep
                return False
            
            self.current_interface = interface_name
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
        if self.activation_word in text:
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
