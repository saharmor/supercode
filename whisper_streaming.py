import speech_recognition as sr
import time
import threading
import queue
import pyaudio
import numpy as np
import wave
import tempfile
import os
from dotenv import load_dotenv
import openai

# Import the new command processor module
from command_processor import CommandProcessor, CommandQueue

# Load environment variables
load_dotenv()

class FastSpeechHandler:
    """
    A fast, responsive speech handler that uses PyAudio directly
    with manual buffering for low-latency speech recognition.
    """
    def __init__(self, activation_word="activate", silence_duration=0.8, command_processor=None):
        """
        Initialize the fast speech handler.
        
        Args:
            activation_word: The word that activates command listening (default: "activate")
            silence_duration: Duration of silence in seconds to end command capture (default: 0.8)
            command_processor: An optional CommandProcessor instance to execute commands
        """
        self.activation_word = activation_word.lower()
        self.silence_duration = silence_duration
        self.command_processor = command_processor
        self.command_queue = CommandQueue(activation_word, command_processor)
        
        # PyAudio configuration
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # 16kHz sample rate for better speech recognition
        self.chunk_size = 1024  # Small chunks for faster response
        self.audio = pyaudio.PyAudio()
        
        # Speech recognition for processing the recorded buffers
        self.recognizer = sr.Recognizer()
        
        # Load environment variables for transcription service
        self.use_openai_api = os.getenv("USE_OPENAI_API", "false").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_whisper_model = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
        
        # Configure OpenAI API if enabled
        if self.use_openai_api:
            if not self.openai_api_key:
                print("Warning: USE_OPENAI_API is set to true but OPENAI_API_KEY is not set.")
                print("Falling back to Google speech recognition.")
                self.use_openai_api = False
            self.openai_client = openai.Client(api_key=self.openai_api_key)
        
        # State variables
        self.listening_for_commands = False
        self.should_stop = False
        self.transcription_queue = queue.Queue()
        self.current_command = ""
        
        # Audio processing variables
        self.audio_buffer = []
        self.energy_threshold = 500  # Energy level to detect speech
        self.silent_chunks_threshold = int(self.silence_duration * self.rate / self.chunk_size)
        self.silent_chunks = 0
    
    def start(self):
        """
        Start the handler threads.
        """
        self.should_stop = False
        
        # Start audio capture thread
        self.capture_thread = threading.Thread(target=self._audio_capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        # Start transcription thread
        self.transcribe_thread = threading.Thread(target=self._transcribe_loop)
        self.transcribe_thread.daemon = True
        self.transcribe_thread.start()
        
        return self.capture_thread
    
    def stop(self):
        """
        Stop all threads and clean up.
        """
        self.should_stop = True
        time.sleep(0.5)  # Give threads time to stop
        self.audio.terminate()
    
    def _is_speech(self, audio_data):
        """
        Detect if audio chunk contains speech based on energy level.
        """
        # Convert bytes to numpy array
        data = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate energy level
        energy = np.sqrt(np.mean(np.square(data.astype(np.float32))))
        
        # Return True if energy is above threshold
        return energy > self.energy_threshold
    
    def _audio_capture_loop(self):
        """
        Continuously capture audio in small chunks and process in real-time.
        This is the key to low latency.
        """
        print(f"Listening for activation word: '{self.activation_word}'\n")
        
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
    
    def _save_and_transcribe(self):
        """
        Save audio buffer to a temporary file and queue for transcription.
        """
        if not self.audio_buffer:
            return
        
        # Create a temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.audio_buffer))
            
            # Queue for transcription - this happens very quickly
            self.transcription_queue.put(temp_file.name)
        
        except Exception as e:
            print(f"Error saving audio: {str(e)}")
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def _transcribe_loop(self):
        """
        Process transcription requests from the queue.
        """
        while not self.should_stop:
            try:
                # Get next file to transcribe with short timeout
                try:
                    audio_file = self.transcription_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Transcribe the audio file
                print("Transcribing audio...")
                start_time = time.time()
                
                # Use speech_recognition library to transcribe
                with sr.AudioFile(audio_file) as source:
                    audio_data = self.recognizer.record(source)
                    try:
                        if self.use_openai_api:
                            # Open the temporary audio file for Whisper API
                            with open(audio_file, 'rb') as file:
                                result = self.openai_client.audio.transcriptions.create(
                                    model=self.openai_whisper_model,
                                    file=file,
                                    language="en",
                                    # prompt=""
                                )
                                text = result.text
                        else:
                            text = self.recognizer.recognize_google(audio_data)
                        
                        # Clean the text by removing punctuation and converting to lowercase
                        clean_text = ''.join(c for c in text if c.isalnum() or c.isspace()).lower()
                        delta = time.time() - start_time
                        print(f"Transcription took {delta:.2f}s - Heard: '{text}'")
                        
                        # Process the recognized text
                        self._process_recognized_text(clean_text)
                    except sr.UnknownValueError:
                        print("Speech not recognized")
                    except Exception as e:
                        print(f"Error in transcription: {str(e)}")
                
                # Clean up the temp file
                if os.path.exists(audio_file):
                    os.unlink(audio_file)
                
                self.transcription_queue.task_done()
            
            except Exception as e:
                print(f"Error in transcription loop: {str(e)}")
                time.sleep(0.5)
    
    def _process_recognized_text(self, text):
        """
        Process recognized text to extract commands using the CommandQueue.
        """
        # Process text and execute any commands found
        if self.command_processor:
            commands = self.command_queue.process_text(text)
            self.command_queue.execute_commands(commands)

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
        self.command_processor = command_processor
        self.command_queue = CommandQueue(activation_word, command_processor)
        
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
                    # Always set non_speaking_duration first, as pause_threshold must be >= non_speaking_duration
                    self.recognizer.non_speaking_duration = 0.2  # Set this to be very responsive
                    
                    # When in command mode, use appropriate thresholds
                    if self.listening_for_commands:
                        # Must ensure pause_threshold >= non_speaking_duration
                        self.recognizer.pause_threshold = 0.3  # Slightly larger than non_speaking_duration
                        print("Continue speaking command...")
                        audio = self.recognizer.listen(source)
                        print(f"Finished listening ({time.time() - start_time:.1f}s)")
                    else:
                        # When waiting for activation word, we can afford more patience
                        self.recognizer.pause_threshold = 0.5  # Larger than non_speaking_duration
                        print("Listening...")
                        audio = self.recognizer.listen(source)
                
                # Try to recognize the speech
                try:
                    print("Transcribing")
                    start_time = time.time()
                    phrase = self.recognizer.recognize_google(audio)
                    delta = time.time() - start_time
                    print(f"Took {delta:.2f} sec. Heard: '{phrase}'")
                    
                    # Process the recognized text
                    self._process_recognized_text(phrase)
                    
                except sr.UnknownValueError:
                    # If we're in command mode and got silence, check if we should process the command
                    if self.listening_for_commands and self.current_command:
                        print("Silence detected after command... Processing now!")
                        # Process the current command due to silence - do this immediately
                        self._finalize_current_command()
                    else:
                        # Just a normal silence while waiting for activation
                        if self.listening_for_commands:
                            print("Silence - still waiting for command to continue...")
                        # Continue listening normally
                
            except Exception as e:
                print(f"Error in listening loop: {str(e)}")
                # Print full exception details for debugging
                import traceback
                print(traceback.format_exc())
                # Reset listening state in case of error
                if self.listening_for_commands:
                    print("Error occurred during command capture - resetting")
                    self.listening_for_commands = False
                    self.current_command = ""
                time.sleep(1.0)  # Longer pause to avoid rapid error loops
    
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
