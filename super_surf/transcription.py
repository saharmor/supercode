import os
import tempfile
import threading
import time
import wave
import pyaudio
import whisper  # Import the local Whisper model
import numpy as np
import sys
from rapidfuzz import fuzz
from typing import Dict, List, Tuple, Optional, Callable, Union
import logging
import librosa
import scipy.signal
import webrtcvad
import struct
from scipy.io import wavfile
import concurrent.futures
import collections
from dotenv import load_dotenv

try:
    from pydub import AudioSegment
except ImportError:
    # Criar uma classe alternativa simples quando pydub não estiver disponível
    class AudioSegment:
        @staticmethod
        def from_wav(wav_file):
            return wav_file
        
        @staticmethod
        def from_file(file, format=None):
            return file
    
    logging.warning("pydub não encontrado. Usando implementação de fallback limitada.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceTranscriber")

# Dictionary of common transcription errors and their corrections
CORRECTION_DICT = {
    "surf": "surf",
    "serf": "surf",
    "safe": "save",
    "fine": "find",
    "go to the line": "go to line",
    "go through line": "go to line",
    "line number": "line",
    "goto": "go to",
    "coffee": "copy",
    "based": "paste",
    "caught": "cut",
    "next one": "next",
    "previous one": "previous",
    "top of": "top",
    "bottom of": "bottom",
    "select everything": "select all",
    "select old": "select all"
}

# Key command phrases to look for
KEY_COMMAND_PHRASES = [
    "save", 
    "undo", 
    "redo", 
    "copy", 
    "paste", 
    "cut", 
    "select all",
    "find", 
    "search", 
    "next", 
    "previous", 
    "go to line", 
    "top", 
    "bottom",
    "type", 
    "write"
]

class AudioPreprocessor:
    """Handles audio preprocessing to improve transcription quality"""
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        # Initialize VAD (Voice Activity Detection)
        try:
            self.vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (0-3)
        except Exception as e:
            logger.error(f"Error initializing VAD: {str(e)}")
            self.vad = None
            
    def process_audio(self, audio_data, audio_file_path=None):
        """Apply all preprocessing steps to audio data"""
        try:
            # Convert to numpy array if needed
            if isinstance(audio_data, bytes):
                audio_data = np.frombuffer(audio_data, dtype=np.int16)
            
            # Convert to float for processing
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # 1. Apply volume normalization
            normalized_audio = self._normalize_volume(audio_float)
            
            # 2. Apply noise reduction
            denoised_audio = self._reduce_noise(normalized_audio)
            
            # 3. Apply Voice Activity Detection to trim silence
            if self.vad:
                trimmed_audio = self._apply_vad(denoised_audio)
            else:
                trimmed_audio = denoised_audio
            
            # Convert back to int16 for saving
            processed_audio = (trimmed_audio * 32768).astype(np.int16)
            
            # Save processed audio if a file path is provided
            if audio_file_path:
                wavfile.write(audio_file_path, self.sample_rate, processed_audio)
                
            return processed_audio
        except Exception as e:
            logger.error(f"Error in audio preprocessing: {str(e)}")
            # Return original data if processing fails
            if audio_file_path and isinstance(audio_data, np.ndarray):
                wavfile.write(audio_file_path, self.sample_rate, audio_data)
            return audio_data
            
    def _normalize_volume(self, audio_data):
        """Normalize the volume of the audio data"""
        # Skip if audio is empty
        if len(audio_data) == 0:
            return audio_data
            
        # Calculate current RMS
        rms = np.sqrt(np.mean(audio_data**2))
        if rms < 1e-10:  # Avoid division by zero
            return audio_data
            
        # Target RMS (empirically determined for good volume level)
        target_rms = 0.2
        
        # Calculate gain needed
        gain = target_rms / rms
        
        # Apply gain with limiting to prevent clipping
        normalized = audio_data * gain
        
        # Apply soft clipping to prevent hard clipping
        normalized = np.tanh(normalized)
        
        return normalized
        
    def _reduce_noise(self, audio_data):
        """Apply noise reduction to the audio data"""
        # Skip if audio is too short
        if len(audio_data) < 2048:
            return audio_data
            
        try:
            # Estimate noise from the first 0.5 seconds (assuming it's mostly noise)
            noise_sample = audio_data[:int(self.sample_rate * 0.5)]
            if len(noise_sample) < 1024:
                noise_sample = audio_data[:min(1024, len(audio_data))]
                
            # Compute noise profile
            noise_profile = np.mean(librosa.feature.rms(y=noise_sample))
            
            # Apply simple spectral subtraction
            stft = librosa.stft(audio_data)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # Reduce magnitude where it's close to the noise profile
            mag_denoised = np.maximum(magnitude - noise_profile, 0)
            
            # Reconstruct signal
            stft_denoised = mag_denoised * np.exp(1j * phase)
            denoised_audio = librosa.istft(stft_denoised, length=len(audio_data))
            
            return denoised_audio
        except Exception as e:
            logger.warning(f"Noise reduction failed: {str(e)}. Using original audio.")
            return audio_data
            
    def _apply_vad(self, audio_data):
        """Apply Voice Activity Detection to trim silence"""
        if self.vad is None:
            return audio_data
            
        try:
            # Convert float audio to int16 for VAD
            audio_int16 = (audio_data * 32768).astype(np.int16)
            
            # Split audio into frames (30ms is standard for VAD)
            frame_duration = 30  # ms
            frame_size = int(self.sample_rate * frame_duration / 1000)
            frames = []
            for i in range(0, len(audio_int16), frame_size):
                frame = audio_int16[i:i+frame_size]
                # Pad last frame if needed
                if len(frame) < frame_size:
                    frame = np.pad(frame, (0, frame_size - len(frame)))
                frames.append(frame)
                
            # Detect speech in each frame
            is_speech = []
            for frame in frames:
                try:
                    # Convert to bytes for VAD
                    frame_bytes = struct.pack("<" + "h" * len(frame), *frame)
                    is_speech.append(self.vad.is_speech(frame_bytes, self.sample_rate))
                except Exception:
                    # If VAD fails for this frame, assume it's speech
                    is_speech.append(True)
                    
            # Add padding around speech frames to avoid cutting words
            padding = 5  # frames
            padded_speech = is_speech.copy()
            for i in range(len(is_speech)):
                if is_speech[i]:
                    for j in range(max(0, i-padding), min(len(is_speech), i+padding+1)):
                        padded_speech[j] = True
                        
            # Keep only speech frames
            speech_audio = []
            for i, frame in enumerate(frames):
                if padded_speech[i]:
                    speech_audio.extend(frame)
                    
            # Convert back to float for further processing
            if speech_audio:
                return np.array(speech_audio).astype(np.float32) / 32768.0
            else:
                # If no speech detected, return original
                return audio_data
                
        except Exception as e:
            logger.warning(f"VAD processing failed: {str(e)}. Using original audio.")
            return audio_data

class EnsembleTranscriber:
    """
    Handles multiple transcriptions with different configurations and selects best result
    using voting and confidence scores.
    """
    
    def __init__(self, base_model):
        """Initialize with base model (already loaded Whisper model)"""
        self.base_model = base_model
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        
    def transcribe_ensemble(self, audio_file, language="en", num_variants=3) -> Dict:
        """
        Run multiple transcriptions with different parameters and return best result.
        Args:
            audio_file: Path to audio file to transcribe
            language: Language code
            num_variants: Number of different configurations to try (max 3)
        Returns:
            Dict with best transcription and metadata
        """
        # Limit number of variants to reasonable range
        num_variants = min(max(num_variants, 1), 3)
        
        # Define different parameter sets to try
        param_sets = [
            {"temperature": 0.0, "prompt": "Commands for IDE like cursor save, find, copy, undo."},
            {"temperature": 0.2, "prompt": "The following audio contains programming editor commands."},
            {"temperature": 0.1, "prompt": "Voice commands for text editor: save, find, go to line, etc."}
        ]
        
        # Use only the requested number of variants
        param_sets = param_sets[:num_variants]
        
        logger.info(f"Starting ensemble transcription with {num_variants} variants")
        start_time = time.time()
        
        try:
            # Submit all transcription tasks
            future_to_params = {}
            for i, params in enumerate(param_sets):
                future = self.executor.submit(
                    self._transcribe_with_params, 
                    audio_file, 
                    language, 
                    params["temperature"], 
                    params["prompt"]
                )
                future_to_params[future] = params
                
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    result = future.result()
                    if result:
                        results.append({
                            "text": result["text"],
                            "temperature": params["temperature"],
                            "prompt": params["prompt"]
                        })
                except Exception as e:
                    logger.warning(f"Transcription variant failed: {str(e)}")
                    
            if not results:
                logger.error("All ensemble transcription variants failed")
                return {
                    "text": "",
                    "ensemble": False,
                    "processing_time": time.time() - start_time
                }
                
            # Now select the best result using voting
            best_result = self._select_best_result(results)
            
            processing_time = time.time() - start_time
            logger.info(f"Ensemble transcription completed in {processing_time:.2f}s with {len(results)} variants")
            
            return {
                "text": best_result["text"],
                "ensemble": True,
                "variants": len(results),
                "processing_time": processing_time,
                "temperature": best_result["temperature"],
                "prompt": best_result["prompt"]
            }
            
        except Exception as e:
            logger.error(f"Ensemble transcription error: {str(e)}")
            return {
                "text": "",
                "ensemble": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
            
    def _transcribe_with_params(self, audio_file, language, temperature, initial_prompt):
        """Run transcription with specific parameters"""
        try:
            # Apply specific parameter set for this transcription
            result = self.base_model.transcribe(
                audio_file,
                language=language,
                temperature=temperature,
                initial_prompt=initial_prompt,
                fp16=False  # Use FP32 for best accuracy
            )
            return result
        except Exception as e:
            logger.warning(f"Transcription with temp={temperature}, prompt='{initial_prompt[:20]}...' failed: {str(e)}")
            return None
            
    def _select_best_result(self, results):
        """
        Select best result based on voting and heuristics.
        For command detection, we prefer results containing the word "cursor" and
        then look for consensus among different variants.
        """
        if not results:
            return {"text": "", "temperature": 0, "prompt": ""}
            
        if len(results) == 1:
            return results[0]
            
        # Extract all transcribed texts
        texts = [r["text"].lower().strip() for r in results]
        
        # First, check if we have exact matches (simple voting)
        if len(set(texts)) == 1:
            # All variants gave exactly the same result - strong confidence
            return results[0]
            
        # Look for "surf" keyword occurrences
        surf_texts = [text for text in texts if "surf" in text]
        if surf_texts:
            # Prefer texts with "surf" keyword
            text_counter = collections.Counter(surf_texts)
            most_common = text_counter.most_common(1)[0][0]
            
            # Find the original result with this text
            for result in results:
                if result["text"].lower().strip() == most_common:
                    return result
                    
        # If no surf texts or no consensus, use token-level voting
        # This is more complex - tokenize and match parts where variants agree
        text_parts = []
        for text in texts:
            text_parts.extend(text.split())
            
        part_counter = collections.Counter(text_parts)
        common_parts = [part for part, count in part_counter.items() 
                        if count > 1 and len(part) > 2]
                        
        if common_parts:
            # Find the text that contains most of the common parts
            best_score = 0
            best_result = results[0]
            
            for result in results:
                text = result["text"].lower()
                score = sum(1 for part in common_parts if part in text)
                if score > best_score:
                    best_score = score
                    best_result = result
                    
            return best_result
            
        # If all else fails, prefer the result with temperature=0.0 (most deterministic)
        for result in results:
            if result["temperature"] == 0.0:
                return result
                
        # Last resort: return the first result
        return results[0]

class VoiceTranscriber:
    """Class for transcribing voice commands using Whisper"""
    
    def __init__(self, model_name="base", use_ensemble=False, device_index=None):
        """Initialize the transcriber with the specified model

        Args:
            model_name (str): The name of the Whisper model to use
                              (tiny, base, small, medium, large)
            use_ensemble (bool): Whether to use ensemble transcription
            device_index (int): The audio device index to use for recording
        """
        # Environment variables
        load_dotenv()
        model_name = os.getenv("WHISPER_MODEL_SIZE", model_name)
        
        # Set up logging
        log_level = os.getenv("LOG_LEVEL", "INFO")
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        logging.basicConfig(level=numeric_level)
        
        # Get device index from environment or parameter
        self.device_index = self._get_device_index(device_index)
        
        # Format code for audio recording
        self.format_code = pyaudio.paInt16
        self.channels = 1
        self.sample_rate = int(os.getenv("SAMPLE_RATE", "16000"))
        self.frames_per_buffer = 1024
        
        # Voice Activity Detection
        self.vad = webrtcvad.Vad(int(os.getenv("VAD_AGGRESSIVENESS", "3")))
        
        # Recording state
        self.recording = False
        self.frames = []
        self.recording_thread = None
        self.stop_recording_event = None
        self.last_transcription_result = None
        
        # Initialize audio interface
        self.audio = pyaudio.PyAudio()
        
        # Model settings
        self.model_name = model_name
        self.fallback_model_name = "medium" if model_name != "medium" else "small"
        self.second_fallback_model_name = "small" if self.fallback_model_name != "small" else "base"
        self.third_fallback_model_name = "base" if self.second_fallback_model_name != "base" else "tiny"
        
        # Performance optimization - disable GPU for Whisper
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        
        # Transcription settings
        self.use_ensemble = use_ensemble and os.getenv("USE_ENSEMBLE", "True").lower() == "true"
        self.transcription_times = collections.deque(maxlen=10)  # Store last 10 transcription times
        
        logger.info(f"Initialized VoiceTranscriber with model: {model_name}, device: {self.device_index}")
        logger.debug(f"Audio settings: rate={self.sample_rate}, format={self.format_code}, channels={self.channels}")
        
        # Initialize audio preprocessor
        self.preprocessor = AudioPreprocessor(sample_rate=self.sample_rate)
        
        # Settings for ensemble transcription
        self.ensemble_variants = int(os.getenv("ENSEMBLE_VARIANTS", "3"))
        if self.use_ensemble and self.ensemble_variants > 2:
            logger.info(f"Limiting ensemble variants to 2 for better performance (was {self.ensemble_variants})")
            self.ensemble_variants = 2
        
        # Performance metrics
        self.total_transcriptions = 0
        self.successful_transcriptions = 0
        self.failed_transcriptions = 0
        self.total_processing_time = 0
        self.total_transcription_time = 0
        
        # Try to load the model
        self._load_model(model_name)
        
        # Initialize ensemble transcriber if enabled
        if self.use_ensemble and self.model:
            self.ensemble = EnsembleTranscriber(self.model)
        else:
            self.ensemble = None
            
        # Print available audio devices
        self._print_audio_devices()
    
    def _get_device_index(self, device_index=None):
        """Get the audio device index from environment or parameter"""
        if device_index is not None:
            return device_index
        
        # Check environment variable
        env_device = os.getenv("AUDIO_DEVICE_INDEX")
        if env_device is not None:
            try:
                return int(env_device)
            except ValueError:
                logger.warning(f"Invalid AUDIO_DEVICE_INDEX: {env_device}, using default")
        
        return None  # Use default device
    
    def list_audio_devices(self):
        """List available audio input devices"""
        info = []
        audio = pyaudio.PyAudio()
        
        logger.info("Available audio input devices:")
        for i in range(audio.get_device_count()):
            try:
                device_info = audio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels') > 0:  # Input device
                    name = device_info.get('name')
                    logger.info(f"Device {i}: {name}")
                    info.append((i, name))
            except Exception as e:
                logger.error(f"Error getting device info for index {i}: {str(e)}")
        
        audio.terminate()
        return info
    
    def _print_audio_devices(self):
        """Debug function to print all available audio input devices"""
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        print(f"Available audio input devices ({num_devices} total):")
        for i in range(0, num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  Device {i}: {device_info.get('name')}")
                
        # Print default input device
        default_input = self.audio.get_default_input_device_info()
        print(f"Default input device: {default_input.get('name')}")
    
    def start_recording(self):
        """Start recording audio for transcription"""
        if self.recording:
            logger.info("Already recording - ignoring start request")
            return
        
        # Reset state
        self.recording = True
        self.frames = []
        self.start_time = time.time()
        
        try:
            # Open the audio stream
            self.stream = self.audio.open(
                format=self.format_code,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.frames_per_buffer
            )
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            logger.info("Started recording audio")
        except Exception as e:
            self.recording = False
            logger.error(f"Error starting recording: {str(e)}")
            # Clean up partial resources
            if hasattr(self, 'stream') and self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
    
    def _record_audio(self):
        """Record audio from microphone in a separate thread"""
        try:
            logger.info("Recording thread started")
            self.frames = []
            
            # Variables to detect silence
            silence_threshold = int(os.getenv("SILENCE_THRESHOLD", "500"))
            consecutive_silent_chunks = 0
            max_silent_chunks = 10   # After this many silent chunks, log a warning
            warned_about_silence = False
            last_warning_time = time.time()
            warning_interval = 5.0  # Only warn every 5 seconds about silence
            
            # Variables to prevent multiprocessing issues
            consecutive_error_count = 0
            max_error_count = 3  # Maximum consecutive errors before aborting
            
            # Record audio in chunks until stopped
            while self.recording:
                try:
                    data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                    self.frames.append(data)
                    
                    # Check audio level to detect silence or low volume
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    audio_level = np.abs(audio_data).mean()
                    
                    current_time = time.time()
                    if audio_level < silence_threshold:
                        consecutive_silent_chunks += 1
                        if consecutive_silent_chunks >= max_silent_chunks:
                            # Only warn about silence at intervals to avoid log spam
                            if not warned_about_silence or (current_time - last_warning_time) > warning_interval:
                                logger.warning(f"Possible silence detected (level: {audio_level}). Check microphone.")
                                warned_about_silence = True
                                last_warning_time = current_time
                    else:
                        consecutive_silent_chunks = 0
                        warned_about_silence = False
                        logger.debug(f"Audio level: {audio_level}")
                    
                    # Reset error count on successful read
                    consecutive_error_count = 0
                        
                except Exception as e:
                    logger.error(f"Error reading audio frame: {str(e)}")
                    consecutive_error_count += 1
                    
                    if consecutive_error_count >= max_error_count:
                        logger.error(f"Too many consecutive errors ({max_error_count}). Stopping recording.")
                        self.recording = False
                        break
                        
                    time.sleep(0.01)  # Avoid tight loop on errors
            
            # Recording stopped normally
            logger.info(f"Recording finished. Captured {len(self.frames)} frames")
            
        except Exception as e:
            logger.error(f"Error in recording thread: {str(e)}")
            self.recording = False
    
    def stop_recording(self):
        """Stop recording and process the recorded audio"""
        if not self.recording:
            logger.info("Not currently recording - ignoring stop request")
            return None
        
        try:
            logger.info("Stopping recording...")
            self.recording = False
            
            # Wait for recording thread to complete
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
                
            # Clean up audio stream
            if hasattr(self, 'stream') and self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    logger.warning(f"Error stopping audio stream: {str(e)}")
                    
            # Process the recorded audio only if we have frames
            if not self.frames:
                logger.warning("No audio frames captured during recording")
                return None
                
            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                temp_wav_path = tmp_file.name
                
            # Write the frames to the WAV file
            try:
                with wave.open(temp_wav_path, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.format_code))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(self.frames))
            except Exception as e:
                logger.error(f"Error writing audio frames to temporary file: {str(e)}")
                os.unlink(temp_wav_path)
                return None
                
            # Preprocess the audio (minimal preprocessing for speed)
            preprocessed_file = self._fast_preprocess_audio(temp_wav_path)
            
            # Transcribe the audio
            start_time = time.time()
            transcript = self._transcribe_audio(preprocessed_file or temp_wav_path)
            
            # Clean up temp files
            if os.path.exists(temp_wav_path):
                try:
                    os.unlink(temp_wav_path)
                except:
                    pass
                    
            if preprocessed_file and os.path.exists(preprocessed_file) and preprocessed_file != temp_wav_path:
                try:
                    os.unlink(preprocessed_file)
                except:
                    pass
                    
            # Calculate and log transcription time
            transcription_time = time.time() - start_time
            self.transcription_times.append(transcription_time)
            avg_time = sum(self.transcription_times) / len(self.transcription_times)
            
            # Update performance metrics
            self.total_transcriptions += 1
            self.total_transcription_time += transcription_time
            if transcript:
                self.successful_transcriptions += 1
                logger.info(f"Transcription success ({transcription_time:.2f}s, avg: {avg_time:.2f}s): '{transcript}' → '{transcript}'")
            else:
                self.failed_transcriptions += 1
                logger.warning(f"Transcription failed ({transcription_time:.2f}s)")
                
            self.last_transcription_result = transcript
            return transcript
            
        except Exception as e:
            logger.error(f"Error in stop_recording: {str(e)}")
            return None
            
    def _fast_preprocess_audio(self, audio_file):
        """Minimal preprocessing for faster transcription"""
        # Skip preprocessing for speed and stability
        # Just return original file path directly
        return audio_file
    
    def _transcribe_audio(self, audio_file):
        """Transcribe audio file to text using Whisper model"""
        # Skip ensemble mode for stability
        try:
            # Direct transcription with minimal parameters for speed
            logger.info("Starting transcription with Whisper...")
            result = self.model.transcribe(
                audio_file,
                language="en",
                temperature=float(os.getenv("WHISPER_TEMPERATURE", "0.0")),
                initial_prompt="Voice commands for text editor. Prefix with 'cursor'.",
                fp16=False,  # Explicitly use FP32 for CPU
            )
            
            # Process and return the transcription
            if not result or not result.get("text"):
                logger.warning("Empty transcription result")
                return ""
            
            # Get the text from the result
            transcript = result["text"].strip()
            logger.info(f"Raw transcription: '{transcript}'")
            
            # Apply corrections from the correction dictionary
            transcript = self._apply_corrections(transcript)
            
            # Enhance command recognition
            transcript = self._enhance_command_recognition(transcript)
            
            return transcript
                
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return ""

    def _safe_transcribe(self, audio_file):
        """
        Run transcription in a safe way that avoids multiprocessing issues.
        
        This function handles the "forking a process while a parallel region is active" 
        warning that can occur with Whisper when using PyTorch with OpenMP.
        """
        try:
            # Directly use the model without spawning additional processes
            # This avoids the multiprocessing warning
            initial_prompt = "Voice commands for text editor. Prefix with 'cursor'."
            result = self.model.transcribe(
                audio_file,
                language="en",
                temperature=float(os.getenv("WHISPER_TEMPERATURE", "0.2")),
                initial_prompt=initial_prompt,
                fp16=False  # Explicitly use FP32 for CPU
            )
            return result
        except Exception as e:
            logger.error(f"Safe transcription failed: {str(e)}")
            return None

    def _transcribe_with_ensemble(self, audio_file):
        """Transcribe with ensemble approach for higher accuracy"""
        try:
            # If ensemble disabled in config, just use regular transcription
            if not self.use_ensemble or self.ensemble_variants <= 1:
                return self._safe_transcribe(audio_file)["text"]
                
            logger.info(f"Using ensemble transcription with {self.ensemble_variants} variants")
            logger.info("Starting ensemble transcription with %d variants", self.ensemble_variants)
            
            # Simplify to just 2 parameters for speed
            temperatures = [0.0, 0.2]
            prompts = [
                "Voice commands for text editor. Prefix with 'surf'.",
                "Commands for IDE like VSCode. Start with 'surf'."
            ]
            
            # Limit to at most 2 variants for better performance
            num_variants = min(self.ensemble_variants, 2)
            
            results = []
            start_time = time.time()
            
            # Try different temperature/prompt combinations
            for i in range(num_variants):
                temp = temperatures[i % len(temperatures)]
                prompt = prompts[i % len(prompts)]
                
                try:
                    # Use the safe transcription method with explicit parameters
                    result = self.model.transcribe(
                        audio_file,
                        language="en",
                        temperature=temp,
                        initial_prompt=prompt,
                        fp16=False  # Explicitly use FP32 for CPU
                    )
                    
                    if result and result.get("text"):
                        # Apply corrections and command enhancement
                        transcript = result["text"].strip()
                        transcript = self._apply_corrections(transcript)
                        transcript = self._enhance_command_recognition(transcript)
                        
                        # Add to results
                        results.append(transcript)
                    
                except Exception as e:
                    logger.warning(f"Transcription with temp={temp}, prompt='{prompt[:20]}...' failed: {str(e)}")
            
            # If we have any successful results, choose the best one
            if results:
                elapsed = time.time() - start_time
                logger.info(f"Ensemble transcription completed in {elapsed:.2f}s with {len(results)} variants")
                
                # Choose the best result based on frequency and similarity
                if len(results) == 1:
                    # Only one successful transcription
                    return results[0]
                    
                # Multiple results - select based on frequency and cursor presence
                best_result = self._select_best_ensemble_result(results)
                return best_result
                
            # No successful results
            return ""
                
        except Exception as e:
            logger.error(f"Ensemble transcription error: {str(e)}")
            # Fallback to regular transcription if ensemble fails
            try:
                result = self._safe_transcribe(audio_file)
                return result["text"] if result and "text" in result else ""
            except:
                return ""

    def _select_best_ensemble_result(self, results):
        """Select the best result from ensemble transcription results"""
        if not results:
            return ""
            
        # Count frequencies of transcriptions
        result_counts = {}
        for result in results:
            result_lower = result.lower()
            if result_lower in result_counts:
                result_counts[result_lower] += 1
            else:
                result_counts[result_lower] = 1
                
        # Get the most frequent result
        most_common = max(result_counts.items(), key=lambda x: x[1])
        
        # If there's a clear winner (appears more than once)
        if most_common[1] > 1:
            return most_common[0]
            
        # No clear winner by frequency, prioritize results with "cursor"
        cursor_results = [r for r in results if "cursor" in r.lower()]
        if cursor_results:
            return cursor_results[0]
            
        # Fall back to first result
        return results[0]

    def _apply_corrections(self, text):
        """Apply the correction dictionary to fix common transcription errors"""
        text_lower = text.lower()
        
        # Apply whole-word corrections
        for error, correction in CORRECTION_DICT.items():
            # Replace with word boundaries to ensure we're replacing whole words
            text_lower = text_lower.replace(f" {error} ", f" {correction} ")
            # Check for error at the beginning of text
            if text_lower.startswith(f"{error} "):
                text_lower = f"{correction} {text_lower[len(error)+1:]}"
            # Check for error at the end of text
            if text_lower.endswith(f" {error}"):
                text_lower = f"{text_lower[:-len(error)-1]} {correction}"
        
        return text_lower
    
    def _enhance_command_recognition(self, text):
        """Use fuzzy matching to improve command recognition"""
        if "surf" not in text.lower():
            # Try to find surf with fuzzy matching
            words = text.lower().split()
            if words and fuzz.ratio(words[0], "surf") > 70:
                # Replace the first word with "surf" if it's similar
                text = "surf " + " ".join(words[1:])
        
        # Look for key command phrases using fuzzy matching
        for command in KEY_COMMAND_PHRASES:
            # Skip if the exact command is already in the text
            if command in text.lower():
                continue
                
            words = text.lower().split()
            for i, word in enumerate(words):
                # If a word is similar to a command, replace it
                if fuzz.ratio(word, command) > 85:
                    words[i] = command
                    text = " ".join(words)
                    break
                # Check for multi-word commands
                if i < len(words) - 1 and " " in command:
                    potential_phrase = f"{word} {words[i+1]}"
                    if fuzz.ratio(potential_phrase, command) > 85:
                        words[i] = command.split()[0]
                        words[i+1] = command.split()[1]
                        text = " ".join(words)
                        break
        
        return text
            
    def set_model(self, model_name):
        """Set a different Whisper model"""
        if model_name == self.model_name and self.model:
            logger.info(f"Already using model: {model_name}")
            return True
            
        success = self._load_model(model_name)
        if success:
            self.model_name = model_name
            
            # Reinitialize ensemble with new model if enabled
            if self.use_ensemble:
                self.ensemble = EnsembleTranscriber(self.model)
                
            return True
        return False
        
    def toggle_ensemble(self, enabled=None, variants=None):
        """Toggle ensemble transcription on/off and set variants count"""
        if enabled is not None:
            self.use_ensemble = enabled
            
        if variants is not None:
            self.ensemble_variants = min(max(variants, 1), 3)
            
        # Re-initialize ensemble if needed
        if self.use_ensemble and self.model:
            self.ensemble = EnsembleTranscriber(self.model)
        else:
            self.ensemble = None
            
        # Update environment settings
        self._update_env_setting("USE_ENSEMBLE", str(self.use_ensemble))
        self._update_env_setting("ENSEMBLE_VARIANTS", str(self.ensemble_variants))
        
        return self.use_ensemble
        
    def _update_env_setting(self, key, value):
        """Update a setting in the .env file"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        
        if not os.path.exists(env_path):
            with open(env_path, 'w') as f:
                f.write(f"{key}={value}\n")
            return
            
        # Read existing content
        with open(env_path, 'r') as f:
            lines = f.readlines()
            
        # Check if key exists
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                key_found = True
                break
                
        # Add key if not found
        if not key_found:
            lines.append(f"{key}={value}\n")
            
        # Write back to file
        with open(env_path, 'w') as f:
            f.writelines(lines)
        
    def get_performance_metrics(self):
        """Return performance metrics as a dictionary"""
        return {
            "total_transcriptions": self.total_transcriptions,
            "successful_transcriptions": self.successful_transcriptions,
            "failed_transcriptions": self.failed_transcriptions,
            "success_rate": (self.successful_transcriptions / self.total_transcriptions * 100 
                             if self.total_transcriptions > 0 else 0),
            "average_transcription_time": (self.total_transcription_time / self.successful_transcriptions 
                                          if self.successful_transcriptions > 0 else 0),
            "average_processing_time": (self.total_processing_time / self.total_transcriptions 
                                       if self.total_transcriptions > 0 else 0),
            "model_name": self.model_name
        }
    
    def _load_model(self, model_name):
        """Load the Whisper model with error handling and fallbacks"""
        try:
            logger.info(f"Loading local Whisper model: {model_name}")
            
            # Explicitly set device to CPU and disable GPU
            os.environ['CUDA_VISIBLE_DEVICES'] = ''
            
            # Load model with device specification
            self.model = whisper.load_model(
                model_name, 
                device="cpu", 
                download_root=os.getenv("WHISPER_MODEL_DIR", None)
            )
            
            logger.info(f"Successfully loaded Whisper model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Error loading Whisper model: {str(e)}")
            
            # Define fallback sequence from large to tiny
            fallback_sequence = ["medium", "small", "base", "tiny"]
            
            # Find current model in sequence
            try:
                current_idx = fallback_sequence.index(model_name)
                
                # If not the last model in sequence, try next smaller one
                if current_idx < len(fallback_sequence) - 1:
                    next_model = fallback_sequence[current_idx + 1]
                    logger.info(f"Falling back to '{next_model}' model...")
                    return self._load_model(next_model)
            except ValueError:
                # Model not in sequence, try with "tiny"
                pass
                
            # Last resort - try tiny model
            logger.info(f"Falling back to 'tiny' model...")
            try:
                self.model = whisper.load_model("tiny", device="cpu")
                return True
            except Exception as e2:
                logger.error(f"Failed to load any Whisper model: {str(e2)}")
                return False
    
    def cleanup(self):
        """Clean up resources"""
        try:
            # Stop any ongoing recording
            self.stop_recording()
            
            # Terminate PyAudio
            if self.audio:
                self.audio.terminate()
                self.audio = None
                
            print("VoiceTranscriber resources cleaned up")
        except Exception as e:
            print(f"Error cleaning up VoiceTranscriber: {e}")

    def record_and_transcribe(self, callback=None):
        """
        Record audio and transcribe it in one go with optional callback when done
        
        Args:
            callback (callable): Optional callback function that takes the transcription as parameter
        """
        try:
            # Continuous recording mode - will be stopped by UI action
            logger.info("Starting recording in continuous mode...")
            self.start_recording()
            
            # Use a threading Event to wait for stop_recording to be called
            stop_event = threading.Event()
            self.stop_recording_event = stop_event
            
            # Create a separate thread for monitoring that doesn't directly manipulate audio data
            def monitoring_thread():
                try:
                    # Initial wait to collect some audio
                    time.sleep(1.0)
                    
                    while self.recording:
                        # Simple periodic check - don't process audio directly here
                        # Just check if we should stop based on recording time
                        max_wait_time = float(os.getenv("MAX_RECORDING_TIME", "30.0"))
                        elapsed_time = time.time() - self.start_time
                        
                        if elapsed_time >= max_wait_time:
                            logger.info(f"Max recording time reached ({max_wait_time}s). Processing...")
                            # Safely stop recording in the main thread
                            result = self.stop_recording()
                            
                            # If we have a result and callback, call it
                            if result and callback:
                                try:
                                    callback(result)
                                except Exception as e:
                                    logger.error(f"Error in transcription callback: {str(e)}")
                            
                            # Restart recording for the next command if we're still supposed to be listening
                            if not stop_event.is_set():
                                # Small pause between recordings
                                time.sleep(0.5)
                                self.start_recording()
                        
                        # Sleep before checking again
                        time.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error in monitoring thread: {str(e)}")
                    # Don't crash the thread, just log the error
            
            # Start the monitoring thread
            monitor = threading.Thread(target=monitoring_thread)
            monitor.daemon = True
            monitor.start()
            
            # Return immediately - recording and processing will happen in background
            return None
                
        except Exception as e:
            logger.error(f"Error in record_and_transcribe: {str(e)}")
            if self.recording:
                self.stop_recording()
            return None 