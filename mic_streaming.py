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
from command_processor import CommandQueue

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
        self.openai_transcription_model = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")
        
        # Configure OpenAI API if enabled
        if self.use_openai_api:
            if not self.openai_api_key or self.openai_api_key.strip() == "":
                print("Warning: USE_OPENAI_API is set to true but OPENAI_API_KEY is not set.")
                print("Falling back to Google speech recognition.")
                self.use_openai_api = False
            else:
                # Basic validation of API key format
                if not self.openai_api_key.startswith('sk-') or len(self.openai_api_key) < 20:
                    print("Warning: OPENAI_API_KEY doesn't look valid (should start with 'sk-' and be longer).")
                    print("Will try to use it anyway, but may fail.")
                
                try:
                    self.openai_client = openai.Client(api_key=self.openai_api_key)
                except Exception as e:
                    print(f"Error initializing OpenAI client: {e}")
                    print("Falling back to Google speech recognition.")
                    self.use_openai_api = False
        else:
            print("Using Google speech recognition (OpenAI API not enabled).")
        
        # State variables
        self.listening_for_commands = False
        self.should_stop = False
        self.transcription_queue = queue.Queue()
        self.current_command = ""
        
        # Audio processing variables
        self.audio_buffer = []
        self.energy_threshold = 1000  # Higher threshold to reduce sensitivity to random noise
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
        self._before_audio_capture()
        
        try:
            # Open audio stream
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            # Calibration step: gather ambient noise for 2 seconds to set the energy threshold
            calibration_duration = 4  # seconds
            calibration_samples = []
            calibration_start = time.time()
            print("Calibrating ambient noise level...")
            while time.time() - calibration_start < calibration_duration:
                chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                calibration_samples.append(np.frombuffer(chunk, dtype=np.int16))

            # Compute the average energy of the ambient noise and set the threshold to 150% of that level
            background_energy = np.mean([
                np.sqrt(np.mean(np.square(chunk.astype(np.float32))))
                for chunk in calibration_samples
            ])
            self.energy_threshold = max(background_energy * 1.5, self.energy_threshold)  # Set minimum threshold to avoid ultra-quiet environments

            
            # Let subclasses do initialization 
            self._after_stream_open()
            
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
                            self._on_recording_start()
                        
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
                                self._on_recording_end()
        
                                # Save audio to temp file for transcription
                                self._save_and_transcribe()
                    
                    # Small sleep to prevent high CPU usage
                    time.sleep(0.001)
            
            except Exception as e:
                print(f"Error in audio capture loop: {str(e)}")
                import traceback
                print(traceback.format_exc())
                self._on_capture_error(e)
            finally:
                # Clean up
                try:
                    stream.stop_stream()
                    stream.close()
                except:
                    pass  # Stream might already be closed
                self._after_stream_close()
        
        except Exception as e:
            print(f"Error initializing audio capture: {str(e)}")
            import traceback
            print(traceback.format_exc())
            self._on_initialization_error(e)
    
    # Hook methods for subclasses to override
    def _before_audio_capture(self):
        """Hook called before audio capture starts"""
        print(f"Listening for activation word: '{self.activation_word}'\n")
        
    def _after_stream_open(self):
        """Hook called after audio stream is opened"""
        pass
        
    def _on_recording_start(self):
        """Hook called when recording starts"""
        pass
        
    def _on_recording_end(self):
        """Hook called when recording ends"""
        pass
        
    def _on_capture_error(self, error):
        """Hook called when an error occurs in the capture loop"""
        pass
        
    def _after_stream_close(self):
        """Hook called after the audio stream is closed"""
        pass
        
    def _on_initialization_error(self, error):
        """Hook called when an error occurs during initialization"""
        pass
    
    def _save_and_transcribe(self):
        """
        Save audio buffer to a temporary file and queue for transcription.
        """
        if not self.audio_buffer:
            return
        
        # Create a temporary WAV file - OpenAI requires specific formats
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        try:
            # Ensure we're using a compatible format for OpenAI (16kHz, mono)
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)  # Mono
                wf.setsampwidth(self.audio.get_sample_size(self.format))  # 16-bit
                wf.setframerate(self.rate)  # 16kHz
                wf.writeframes(b''.join(self.audio_buffer))
            
            # Check file size - OpenAI has limits
            file_size = os.path.getsize(temp_file.name)
            
            # Only send if file is not too small (likely noise) or too large
            if 10 * 1024 <= file_size <= 25 * 1024 * 1024:  # 10KB to 25MB
                # Queue for transcription - this happens very quickly
                self.transcription_queue.put(temp_file.name)
            else:
                if file_size < 10 * 1024:
                    print("Audio file too small, likely just noise. Skipping transcription.")
                else:
                    print("Audio file too large for API. Skipping transcription.")
                # Clean up temp file
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        
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
                
                # Check if audio is just random noise
                with wave.open(audio_file, 'rb') as wf:
                    # Read audio data
                    audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                    # Calculate RMS energy
                    rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
                    # Check if below noise threshold
                    if rms < self.energy_threshold * 0.8:  # Use slightly lower threshold
                        print("Audio appears to be random noise, skipping transcription")
                        if os.path.exists(audio_file):
                            os.unlink(audio_file)
                        self.transcription_queue.task_done()
                        continue
                
                print("Transcribing audio...")
                start_time = time.time()
                # Use speech_recognition library to transcribe
                with sr.AudioFile(audio_file) as source:
                    audio_data = self.recognizer.record(source)
                    try:
                        if self.use_openai_api:
                            try:
                                audio_file_obj = open(audio_file, 'rb')        
                                result = self.openai_client.audio.transcriptions.create(
                                    model=self.openai_transcription_model,
                                    file=audio_file_obj,
                                    language="en",
                                    # prompt=""
                                )
                                
                                text = result.text
                            except Exception as api_call_error:
                                print(f"API call error: {str(api_call_error)}")
                                print("Falling back to Google speech recognition...")
                                text = self.recognizer.recognize_google(audio_data)
                                print(f"Google fallback succeeded: '{text}'")
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
                        # Add more detailed error logging
                        import traceback
                        print(f"Detailed transcription error: {traceback.format_exc()}")
                    finally:
                        # Always close file
                        audio_file_obj.close()
                        
                        
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
        Also handles displaying ignored transcriptions when no activation word is found.
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
