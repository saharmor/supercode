#!/usr/bin/env python3
"""
Diagnostic tool for testing continuous audio recording with SuperSurf.
This tool simulates the continuous recording mode and helps identify
any issues with the audio recording or multiprocessing.
"""

import os
import sys
import time
import wave
import threading
import numpy as np
import argparse
import logging
import pyaudio
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AudioDiagnostic")

class ContinuousRecordingDiagnostic:
    """
    A diagnostic tool for continuous audio recording similar to SuperSurf's implementation.
    """
    
    def __init__(self, device_index=None, sample_rate=16000, frames_per_buffer=1024):
        """Initialize the audio diagnostic with specified parameters."""
        # Load environment variables
        load_dotenv()
        
        # Set environment variables to prevent multiprocessing issues
        os.environ['OMP_NUM_THREADS'] = os.getenv('OMP_NUM_THREADS', '1')
        os.environ['PYTORCH_NUM_THREADS'] = os.getenv('PYTORCH_NUM_THREADS', '1')
        os.environ['MKL_NUM_THREADS'] = '1'
        os.environ['OPENBLAS_NUM_THREADS'] = '1'
        
        # Audio settings
        self.device_index = device_index
        if self.device_index is None:
            self.device_index = int(os.getenv("AUDIO_DEVICE_INDEX", "-1"))
        self.sample_rate = sample_rate
        self.frames_per_buffer = frames_per_buffer
        self.format_code = pyaudio.paInt16
        self.channels = 1
        
        # Recording state
        self.recording = False
        self.frames = []
        self.recording_thread = None
        self.stop_event = threading.Event()
        
        # Audio levels for visualization
        self.audio_levels = []
        self.max_levels_to_keep = 300  # About 10 seconds at 30 fps
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        
    def list_audio_devices(self):
        """List all available audio input devices and their details."""
        num_devices = self.audio.get_device_count()
        input_devices = []
        
        print(f"Available audio input devices ({num_devices} total):")
        for i in range(num_devices):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                # Only show devices with input channels
                if device_info.get('maxInputChannels', 0) > 0:
                    input_devices.append((i, device_info))
                    print(f"  Device {i}: {device_info.get('name', 'Unknown Device')}")
            except Exception as e:
                print(f"  Error getting info for device {i}: {e}")
        
        # Print default input device
        try:
            default_device = self.audio.get_default_input_device_info()
            print(f"Default input device: {default_device.get('name', 'Unknown')}")
        except Exception:
            print("No default input device available")
            
        return input_devices
    
    def start_recording(self):
        """Start continuous recording."""
        if self.recording:
            logger.info("Already recording")
            return
        
        # Reset recording state
        self.recording = True
        self.frames = []
        self.audio_levels = []
        self.stop_event.clear()
        
        try:
            # Open the audio stream
            self.stream = self.audio.open(
                format=self.format_code,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index if self.device_index >= 0 else None,
                frames_per_buffer=self.frames_per_buffer
            )
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            logger.info(f"Started continuous recording with device index: {self.device_index}")
            
        except Exception as e:
            self.recording = False
            logger.error(f"Error starting recording: {e}")
            if hasattr(self, 'stream'):
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception:
                    pass
    
    def _record_audio(self):
        """Record audio continuously in a separate thread."""
        try:
            logger.info("Recording thread started")
            
            # Variables to detect silence
            silence_threshold = int(os.getenv("SILENCE_THRESHOLD", "500"))
            consecutive_silent_chunks = 0
            max_silent_chunks = 10
            warned_about_silence = False
            last_warning_time = time.time()
            warning_interval = 5.0
            
            # Variables for statistics
            total_level = 0
            num_samples = 0
            max_level = 0
            
            # Record until stopped
            while self.recording and not self.stop_event.is_set():
                try:
                    data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                    self.frames.append(data)
                    
                    # Calculate audio level
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    audio_level = np.abs(audio_data).mean()
                    
                    # Store audio level for visualization
                    self.audio_levels.append(audio_level)
                    if len(self.audio_levels) > self.max_levels_to_keep:
                        self.audio_levels.pop(0)
                    
                    # Update statistics
                    total_level += audio_level
                    num_samples += 1
                    max_level = max(max_level, audio_level)
                    
                    # Check for silence
                    current_time = time.time()
                    if audio_level < silence_threshold:
                        consecutive_silent_chunks += 1
                        if consecutive_silent_chunks >= max_silent_chunks:
                            if not warned_about_silence or (current_time - last_warning_time) > warning_interval:
                                logger.warning(f"Possible silence detected (level: {audio_level}). Check microphone.")
                                warned_about_silence = True
                                last_warning_time = current_time
                    else:
                        consecutive_silent_chunks = 0
                        warned_about_silence = False
                        logger.debug(f"Audio level: {audio_level}")
                    
                except Exception as e:
                    logger.error(f"Error reading audio frame: {e}")
                    time.sleep(0.01)
            
            # Recording stopped normally
            logger.info(f"Recording finished. Captured {len(self.frames)} frames")
            
            # Display statistics
            if num_samples > 0:
                avg_level = total_level / num_samples
                logger.info(f"Audio statistics: Max level: {max_level:.2f}, Average level: {avg_level:.2f}")
                
                # Suggest silence threshold adjustments
                if avg_level < 200:
                    logger.warning(f"Low audio levels detected (avg: {avg_level:.2f}). Consider adjusting your microphone volume.")
                    logger.info(f"Suggested SILENCE_THRESHOLD setting: {max(int(avg_level * 0.5), 50)}")
                elif avg_level > 2000:
                    logger.info(f"High audio levels detected (avg: {avg_level:.2f}). Your microphone is capturing audio well.")
                    logger.info(f"Suggested SILENCE_THRESHOLD setting: {int(avg_level * 0.2)}")
                else:
                    logger.info(f"Good audio levels detected (avg: {avg_level:.2f}).")
                    logger.info(f"Suggested SILENCE_THRESHOLD setting: {int(avg_level * 0.3)}")
            
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
            self.recording = False
    
    def stop_recording(self):
        """Stop recording and clean up resources."""
        if not self.recording:
            logger.info("Not currently recording")
            return
        
        try:
            logger.info("Stopping recording...")
            self.recording = False
            self.stop_event.set()
            
            # Wait for recording thread to finish
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
            
            # Close the audio stream
            if hasattr(self, 'stream'):
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    logger.error(f"Error closing audio stream: {e}")
            
            logger.info(f"Recording stopped. Captured {len(self.frames)} frames.")
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
    
    def save_recording(self, filename="continuous_recording.wav"):
        """Save the recorded audio to a WAV file."""
        if not self.frames or len(self.frames) < 5:
            logger.warning("Not enough audio data to save")
            return False
        
        try:
            # Write frames to WAV file
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format_code))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))
            
            logger.info(f"Recording saved to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving recording: {e}")
            return False
    
    def visualize_audio_levels(self):
        """Create a real-time visualization of audio levels during recording."""
        if not self.recording:
            logger.warning("Not currently recording. Start recording first.")
            return
        
        # Set up the figure for plotting
        plt.ion()  # Enable interactive mode
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_ylim(0, 5000)  # Set a reasonable y-axis limit
        ax.set_xlim(0, self.max_levels_to_keep)
        ax.set_title('Live Audio Levels')
        ax.set_xlabel('Time')
        ax.set_ylabel('Audio Level')
        
        # Add horizontal line for silence threshold
        silence_threshold = int(os.getenv("SILENCE_THRESHOLD", "500"))
        ax.axhline(y=silence_threshold, color='r', linestyle='-', alpha=0.7, label=f'Silence Threshold ({silence_threshold})')
        
        # Create an empty line plot
        line, = ax.plot([], [], lw=2)
        
        # Add legend
        ax.legend()
        
        # Function to update the plot
        def update(frame):
            # Update the line data
            line.set_data(range(len(self.audio_levels)), self.audio_levels)
            
            # Adjust y-axis if needed
            if self.audio_levels and max(self.audio_levels) > ax.get_ylim()[1]:
                ax.set_ylim(0, max(self.audio_levels) * 1.1)
            
            return line,
        
        # Create animation
        ani = FuncAnimation(fig, update, frames=None, interval=100, blit=True)
        plt.show()
        
        # Keep the plot open until recording stops
        try:
            while self.recording and not self.stop_event.is_set():
                plt.pause(0.1)
        except Exception as e:
            logger.error(f"Error in visualization: {e}")
        finally:
            plt.close()
    
    def run_continuous_test(self, duration=30, visualize=True, save=True):
        """Run a complete continuous recording test for the specified duration."""
        logger.info(f"Starting audio test for {duration} seconds...")
        
        # Start recording
        self.start_recording()
        
        # Start visualization in a separate thread if requested
        if visualize:
            vis_thread = threading.Thread(target=self.visualize_audio_levels)
            vis_thread.daemon = True
            vis_thread.start()
        
        try:
            # Record for the specified duration
            for i in range(duration):
                if not self.recording:
                    break
                time.sleep(1)
                if i % 5 == 0 and i > 0:
                    logger.info(f"Recording in progress... {i}/{duration} seconds")
        
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        finally:
            # Stop recording
            self.stop_recording()
            
            # Save the recording if requested
            if save and self.frames:
                self.save_recording()
            
            # Wait for visualization to finish
            if visualize and vis_thread.is_alive():
                vis_thread.join(timeout=1.0)
            
            # Display final message
            logger.info("Audio test completed.")
            
            # Clean up
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.recording:
                self.stop_recording()
            
            if hasattr(self, 'audio'):
                self.audio.terminate()
                
            logger.info("Audio resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")


def main():
    """Main function for the continuous audio diagnostic tool."""
    parser = argparse.ArgumentParser(description="SuperSurf Continuous Audio Diagnostic Tool")
    parser.add_argument("--list-devices", action="store_true", help="List available audio devices and exit")
    parser.add_argument("--device", type=int, default=None, help="Audio device index to use")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds (default: 30)")
    parser.add_argument("--no-visualize", action="store_true", help="Disable audio level visualization")
    parser.add_argument("--no-save", action="store_true", help="Don't save the recording")
    args = parser.parse_args()
    
    try:
        # Create diagnostic instance
        diagnostic = ContinuousRecordingDiagnostic(device_index=args.device)
        
        # List devices if requested
        if args.list_devices:
            diagnostic.list_audio_devices()
            diagnostic.cleanup()
            return
        
        # Run the continuous recording test
        diagnostic.run_continuous_test(
            duration=args.duration,
            visualize=not args.no_visualize,
            save=not args.no_save
        )
        
    except Exception as e:
        logger.error(f"Error in diagnostic tool: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 