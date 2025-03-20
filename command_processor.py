#!/usr/bin/env python3
"""
Command processor for SuperSurf application.
Handles the execution of commands from transcribed speech.
"""

import os
from openai import OpenAI
import pyautogui
import threading
from computer_use_utils import get_coordinates_for_prompt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pydantic import BaseModel
from typing import Literal

class EnhancedPrompt(BaseModel):
    prompt: str
    requiredIntelligenceLevel: Literal["low", "medium", "high"]

class CommandProcessor:
    """
    Processes commands received from transcribed speech.
    Implements various actions like typing text, clicking, and learning UI elements.
    """
    def __init__(self):
        self.default_action_selectors = [
            {"command": "type", "llm_selector": "Input box for the Cascade agent which start with 'Ask anything'. Usually, it's in the right pane of the screen"}
        ]

        self.actions_coordinates = {}
        for action in self.default_action_selectors:
            self.actions_coordinates[action["command"]] = get_coordinates_for_prompt(action["llm_selector"])
        
        self.buttons = {}
        self.command_history = []
        self.cascade_monitor_thread = None
        
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
                
            from bg_screenshot_test import monitor_cascade_state
            
            # Start monitoring in a background thread
            self.cascade_monitor_thread = threading.Thread(target=monitor_cascade_state, args=(3.0, "screenshots", "cascade_"))
            self.cascade_monitor_thread.daemon = True
            self.cascade_monitor_thread.start()
            print("Started Cascade state monitoring in background")
        except Exception as e:
            print(f"Error starting Cascade monitoring: {e}")
            
    def enhance_user_prompt(self, command_text):
        """
        Enhance a raw user prompt by using GPT-4o Mini to structure it for a coding model.
        
        Args:
            command_text: The raw prompt text to enhance.
            
        Returns:
            str: The enhanced, structured prompt.
        """
        try:
            client = OpenAI()
            
            system_prompt = """You are a prompt engineering assistant. Your task is to transform raw, unstructured prompts 
            into short prompts specifically designed for coding models and IDEs like Copilot and Windsurf.
            Analyze the complexity of the request and return the transformed prompt optimized for coding models
            along with the required intelligence level based on the complexity of the task.
            
            Use 'low' for simple formatting or basic code generation, 'medium' for standard programming tasks,
            and 'high' for complex algorithms, architecture design, or domain-specific optimizations.
            
            If the prompt doesn't make sense for a coding task, return the prompt as None."""
            
            try:
                completion = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Transform this raw user prompt: {command_text}"}
                    ],
                    temperature=0.5,
                    response_format=EnhancedPrompt,
                )
                
                enhanced_data = completion.choices[0].message.parsed
                print(f"\n==== ENHANCED PROMPT ====\n{enhanced_data.prompt}\n==== INTELLIGENCE LEVEL: {enhanced_data.requiredIntelligenceLevel} ====\n")
                return enhanced_data
            except Exception as e:
                print(f"Error parsing structured output: {e}")
                # Fallback to regular response if structured parsing fails
                return {"enhancedPrompt": command_text, "requiredIntelligenceLevel": "medium"}
            
        except Exception as e:
            print(f"Error enhancing prompt: {e}")
            # Return original prompt if enhancement fails
            return command_text
    
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
            # Regular type command
            enhanced_prompt = self.enhance_user_prompt(command_params)
            if not enhanced_prompt.prompt or enhanced_prompt.prompt == 'None':
                print("Invalid command - cannot enhance prompt")
                # play sound to notify user
                play_beep(1200, 1000)
                return False
            
            pyautogui.moveTo(self.actions_coordinates[command_type][0], self.actions_coordinates[command_type][1])
            pyautogui.click(button="left")
            pyautogui.write(enhanced_prompt.prompt)
            pyautogui.press("enter")
            
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
