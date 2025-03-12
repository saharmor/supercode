import speech_recognition as sr
import time
import threading
import queue

class CommandProcessor:
    def __init__(self):
        """
        Initialize the command processor.
        Override this method to implement your own command execution logic.
        """
        self.command_history = []
        
    def execute_command(self, command_text):
        """
        Execute a command based on the transcribed text.
        Override this method to implement your own command execution logic.
        """
        print(f"\n==== EXECUTING COMMAND: '{command_text}' ====\n")
        
        # Add command to history
        self.command_history.append(command_text)
        
        # Add your command execution logic here
        # For example, you could parse the command and execute different actions
        # based on what was said
        
        return True

class SpeechActivationHandler:
    def __init__(self, activation_word="activate", silence_duration=2.0, command_processor=None):
        """
        Initialize the speech activation handler.
        
        Args:
            activation_word: The word that activates command listening (default: "activate")
            silence_duration: Duration of silence in seconds to end command capture (default: 2.0)
            command_processor: An optional CommandProcessor instance to execute commands
        """
        self.activation_word = activation_word.lower()
        self.silence_duration = silence_duration
        self.command_processor = command_processor or CommandProcessor()
        
        # Initialize recognizer and microphone
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        # State variables
        self.listening_for_commands = False
        self.should_stop = False
        self.command_queue = queue.Queue()
        self.current_command = ""
        
        # Adjust the recognizer for ambient noise
        with self.mic as source:
            print("Calibrating microphone for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("Calibration complete.\n")
    
    def start(self):
        """
        Start the activation handler in a separate thread.
        """
        self.should_stop = False
        
        # Start the command execution thread
        self.command_thread = threading.Thread(target=self._process_command_queue)
        self.command_thread.daemon = True
        self.command_thread.start()
        
        # Start the main listening loop
        self.listen_thread = threading.Thread(target=self._listen_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        return self.listen_thread
    
    def stop(self):
        """
        Stop the activation handler.
        """
        self.should_stop = True
    
    def _listen_loop(self):
        """
        Main listening loop that runs in a separate thread.
        """
        print(f"Listening for activation word: '{self.activation_word}'\n")
        
        while not self.should_stop:
            try:
                # Listen for audio with a sensitivity to the activation word
                with self.mic as source:
                    self.recognizer.pause_threshold = 0.8  # More responsive detection
                    print("Listening..." if not self.listening_for_commands else "Continue speaking command...")
                    audio = self.recognizer.listen(source)
                
                # Try to recognize the speech
                try:
                    phrase = self.recognizer.recognize_google(audio)
                    print(f"Heard: '{phrase}'")
                    
                    # Process the recognized text
                    self._process_recognized_text(phrase)
                    
                except sr.UnknownValueError:
                    # If we're in command mode and got silence, check if we should process the command
                    if self.listening_for_commands and self.current_command:
                        print("Silence detected after command...")
                        # Process the current command due to silence
                        self._finalize_current_command()
                    else:
                        pass  # Just continue listening
                
            except Exception as e:
                print(f"Error in listening loop: {e}")
                time.sleep(0.5)  # Brief pause before retrying
    
    def _process_recognized_text(self, text):
        """
        Process recognized text to detect activation word and commands.
        """
        text_lower = text.lower()
        
        # Special case: Handle multiple activation words in a single phrase
        if text_lower.count(self.activation_word) > 1:
            # Split the text by the activation word
            parts = text_lower.split(self.activation_word)
            
            # The first part is before any activation word, so skip it if empty
            if parts[0].strip():
                print(f"Heard before activation: '{parts[0].strip()}'")
            
            # Process the commands between activation words
            commands = []
            for i in range(1, len(parts)):
                if parts[i].strip():
                    commands.append(parts[i].strip())
            
            # If we have multiple commands
            if len(commands) > 1:
                # Process all but the last command immediately
                for i in range(len(commands) - 1):
                    cmd = commands[i]
                    print(f"\n*** ACTIVATION WORD DETECTED! ***")
                    print(f"Command detected: '{cmd}'")
                    self.command_queue.put(cmd)
                    print(f"\n==== COMMAND CAPTURED: '{cmd}' ====\n")
                
                # Keep the last command in the buffer
                self.listening_for_commands = True
                self.current_command = commands[-1]
                print(f"\n*** ACTIVATION WORD DETECTED! ***")
                print(f"Command started: '{self.current_command}'")
            
            # If we have just one command
            elif len(commands) == 1:
                self.listening_for_commands = True
                self.current_command = commands[0]
                print(f"\n*** ACTIVATION WORD DETECTED! ***")
                print(f"Command started: '{self.current_command}'")
            
            # If no valid commands were found
            else:
                self.listening_for_commands = True
                self.current_command = ""
                print(f"\n*** ACTIVATION WORD DETECTED! ***")
                print("Waiting for command...")
            
            return
        
        # Regular case: Single activation word
        if self.activation_word in text_lower:
            # If we're already in command mode and have a partial command
            if self.listening_for_commands and self.current_command:
                # Finalize the current command first
                self._finalize_current_command()
            
            # Set command listening mode
            self.listening_for_commands = True
            print(f"\n*** ACTIVATION WORD DETECTED! ***")
            
            # Extract the command after the activation word
            parts = text_lower.split(self.activation_word, 1)
            if len(parts) > 1 and parts[1].strip():
                self.current_command = parts[1].strip()
                print(f"Command started: '{self.current_command}'")
            else:
                # Just the activation word was detected
                self.current_command = ""
                print("Waiting for command...")
            
        elif self.listening_for_commands:
            # We're already in command mode, so append this text to the current command
            if self.current_command:
                self.current_command += " " + text
            else:
                self.current_command = text
            
            print(f"Command continued: '{self.current_command}'")
    
    def _finalize_current_command(self):
        """
        Finalize and queue the current command for execution.
        """
        if not self.current_command:
            # Nothing to process
            self.listening_for_commands = False
            print(f"\nWaiting for activation word: '{self.activation_word}'...\n")
            return
            
        # Check if the current command contains the activation word
        # This handles cases like "type in the world activate enter"
        if self.activation_word in self.current_command.lower():
            # Split the command by the activation word
            parts = self.current_command.lower().split(self.activation_word)
            
            # Process the first part as a complete command
            first_command = parts[0].strip()
            if first_command:
                print(f"\n==== COMMAND CAPTURED: '{first_command}' ====\n")
                self.command_queue.put(first_command)
            
            # If there's content after the activation word, start a new command
            if len(parts) > 1 and parts[1].strip():
                self.current_command = parts[1].strip()
                self.listening_for_commands = True
                print(f"\n*** NEW ACTIVATION WORD DETECTED! ***")
                print(f"Command started: '{self.current_command}'")
                return
            else:
                # Just reset for the next activation
                self.current_command = ""
                self.listening_for_commands = False
                print(f"\nWaiting for activation word: '{self.activation_word}'...\n")
                return
        
        # Normal case - no embedded activation word
        print(f"\n==== COMMAND CAPTURED: '{self.current_command}' ====\n")
        # Add the command to the processing queue
        self.command_queue.put(self.current_command)
        # Reset for the next command
        self.current_command = ""
        self.listening_for_commands = False
        print(f"\nWaiting for activation word: '{self.activation_word}'...\n")
    
    def _process_command_queue(self):
        """
        Process commands from the queue in a separate thread.
        """
        while not self.should_stop:
            try:
                # Get command from queue with timeout
                command = self.command_queue.get(timeout=0.5)
                if command:
                    # Execute the command
                    self.command_processor.execute_command(command)
                self.command_queue.task_done()
            except queue.Empty:
                pass  # No commands in the queue
            except Exception as e:
                print(f"Error processing command: {e}")

def main():
    """
    Main function to run the speech activation handler.
    """
    try:
        # Create and start the activation handler
        handler = SpeechActivationHandler(
            activation_word="activate",
            silence_duration=2.0
        )
        
        # Start the handler in a separate thread
        listen_thread = handler.start()
        
        # Keep the main thread running
        print("Press Ctrl+C to exit...")
        while listen_thread.is_alive():
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping speech recognition...")
    finally:
        # Clean up
        if 'handler' in locals():
            handler.stop()
        print("Speech recognition stopped.")

if __name__ == "__main__":
    main()
