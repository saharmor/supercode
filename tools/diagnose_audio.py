#!/usr/bin/env python
"""
Audio Diagnostic Tool for SuperSurf
This script helps diagnose audio input issues by testing microphone access,
recording capabilities, and displaying audio levels in real-time.
"""

import os
import sys
import time
import argparse
import pyaudio
import numpy as np
import threading
import wave
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from super_surf
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AudioDiagnostic")

class AudioDiagnostic:
    """Class for diagnosing audio input issues"""
    
    def __init__(self, device_index=None, sample_rate=16000, frames_per_buffer=1024):
        """Initialize the audio diagnostic tool"""
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.frames_per_buffer = frames_per_buffer
        self.format_code = pyaudio.paInt16
        self.channels = 1
        
        # State variables
        self.recording = False
        self.frames = []
        self.audio_levels = []
        self.max_levels = 100  # Store the last 100 audio levels
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Visualization
        self.fig = None
        self.ax = None
        self.line = None
        
    def list_audio_devices(self):
        """List all available audio input devices"""
        devices = []
        print("\n=== Available Audio Input Devices ===")
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels') > 0:  # Input device
                    name = device_info.get('name')
                    print(f"Device {i}: {name}")
                    devices.append((i, name))
            except Exception as e:
                print(f"Error getting info for device {i}: {e}")
        
        return devices
    
    def start_recording(self):
        """Start recording and monitoring audio"""
        if self.recording:
            logger.info("Already recording")
            return
        
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
            
            self.recording = True
            self.frames = []
            self.audio_levels = []
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            logger.info("Started recording and monitoring audio")
            
        except Exception as e:
            logger.error(f"Error starting audio: {e}")
            if self.stream:
                try:
                    self.stream.close()
                except:
                    pass
            self.recording = False
    
    def _record_audio(self):
        """Record audio in a separate thread and monitor levels"""
        try:
            while self.recording:
                try:
                    data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                    self.frames.append(data)
                    
                    # Calculate audio level
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    audio_level = np.abs(audio_data).mean()
                    
                    # Store audio level
                    self.audio_levels.append(audio_level)
                    if len(self.audio_levels) > self.max_levels:
                        self.audio_levels.pop(0)
                    
                    # Print audio level information periodically
                    if len(self.frames) % 10 == 0:
                        logger.info(f"Audio level: {audio_level:.2f}")
                        
                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    time.sleep(0.01)
            
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
            self.recording = False
    
    def stop_recording(self):
        """Stop recording and close the audio stream"""
        if not self.recording:
            logger.info("Not recording")
            return
        
        self.recording = False
        
        # Wait for recording thread to complete
        if hasattr(self, 'recording_thread') and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=1.0)
        
        # Close the stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
        
        logger.info(f"Recording stopped. Captured {len(self.frames)} frames")
    
    def save_recording(self, filename="test_recording.wav"):
        """Save the recorded audio to a WAV file"""
        if not self.frames:
            logger.warning("No audio data to save")
            return False
        
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format_code))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))
            
            logger.info(f"Saved recording to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving recording: {e}")
            return False
    
    def visualize_audio_levels(self):
        """Visualize audio levels in real-time"""
        # Create the figure and axis
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.ax.set_ylim(0, 5000)  # Adjust based on typical audio levels
        self.ax.set_xlim(0, self.max_levels)
        self.ax.set_title('Real-time Audio Levels')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Audio Level')
        self.ax.grid(True)
        
        # Create an empty line
        self.line, = self.ax.plot([], [], lw=2)
        
        # Create horizontal lines for reference
        self.ax.axhline(y=500, color='r', linestyle='--', alpha=0.7, label='Threshold 500')
        self.ax.axhline(y=1000, color='g', linestyle='--', alpha=0.7, label='Threshold 1000')
        self.ax.legend()
        
        # Function to update the line
        def update(frame):
            # Update the line data
            x = list(range(len(self.audio_levels)))
            y = self.audio_levels
            
            self.line.set_data(x, y)
            
            # Adjust the x-axis limits if needed
            if len(x) > 0:
                self.ax.set_xlim(max(0, len(x) - self.max_levels), max(self.max_levels, len(x)))
            
            return self.line,
        
        # Create the animation
        ani = FuncAnimation(self.fig, update, blit=True, interval=100)
        
        # Show the plot
        plt.tight_layout()
        plt.show()
    
    def cleanup(self):
        """Clean up resources"""
        if self.recording:
            self.stop_recording()
        
        self.audio.terminate()
        logger.info("Audio resources cleaned up")

def main():
    """Main function to run the audio diagnostic tool"""
    # Load environment variables
    load_dotenv()
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Audio Diagnostic Tool for SuperSurf')
    parser.add_argument('--device', type=int, help='Audio input device index')
    parser.add_argument('--sample-rate', type=int, default=16000, help='Sample rate in Hz')
    parser.add_argument('--test-duration', type=int, default=10, help='Test duration in seconds')
    parser.add_argument('--list-devices', action='store_true', help='List audio devices and exit')
    parser.add_argument('--save', action='store_true', help='Save the test recording')
    parser.add_argument('--visualize', action='store_true', help='Visualize audio levels')
    args = parser.parse_args()
    
    # Try to get device index from environment if not specified
    device_index = args.device
    if device_index is None:
        env_device = os.getenv("AUDIO_DEVICE_INDEX")
        if env_device is not None:
            try:
                device_index = int(env_device)
                logger.info(f"Using device index {device_index} from environment")
            except ValueError:
                logger.warning(f"Invalid AUDIO_DEVICE_INDEX: {env_device}")
    
    # Create the diagnostic tool
    diagnostic = AudioDiagnostic(device_index=device_index, sample_rate=args.sample_rate)
    
    try:
        # List devices if requested
        if args.list_devices:
            diagnostic.list_audio_devices()
            return
        
        # Default behavior: list devices and prompt for selection if not specified
        if device_index is None:
            devices = diagnostic.list_audio_devices()
            if not devices:
                logger.error("No audio input devices found")
                return
            
            device_index = input("\nEnter device index to test (leave blank for default): ")
            if device_index:
                try:
                    device_index = int(device_index)
                    diagnostic.device_index = device_index
                    logger.info(f"Selected device index: {device_index}")
                except ValueError:
                    logger.warning("Invalid device index, using default")
                    diagnostic.device_index = None
        
        # Start recording
        logger.info(f"Starting audio test for {args.test_duration} seconds...")
        diagnostic.start_recording()
        
        # If visualizing, show the plot
        if args.visualize:
            visualization_thread = threading.Thread(target=diagnostic.visualize_audio_levels)
            visualization_thread.daemon = True
            visualization_thread.start()
        
        # Wait for the specified duration
        for i in range(args.test_duration):
            time.sleep(1)
            remaining = args.test_duration - i - 1
            if remaining > 0 and remaining % 5 == 0:
                logger.info(f"{remaining} seconds remaining...")
        
        # Stop recording
        diagnostic.stop_recording()
        
        # Save the recording if requested
        if args.save:
            if diagnostic.save_recording():
                logger.info("Test recording saved successfully")
        
        # Print diagnostics summary
        print("\n=== Audio Diagnostic Summary ===")
        if not diagnostic.frames:
            print("❌ No audio data was recorded!")
            print("- Check that your microphone is connected and working")
            print("- Check system permissions for microphone access")
            print("- Try a different microphone or device index")
        else:
            num_frames = len(diagnostic.frames)
            expected_frames = args.test_duration * diagnostic.sample_rate / diagnostic.frames_per_buffer
            frame_ratio = num_frames / expected_frames if expected_frames > 0 else 0
            
            if frame_ratio < 0.5:
                print(f"⚠️ Low frame count: {num_frames} frames (expected ~{int(expected_frames)})")
            else:
                print(f"✅ Recorded {num_frames} frames (expected ~{int(expected_frames)})")
            
            audio_levels = diagnostic.audio_levels
            if not audio_levels:
                print("❌ No audio levels recorded")
            else:
                avg_level = sum(audio_levels) / len(audio_levels)
                max_level = max(audio_levels)
                print(f"Avg audio level: {avg_level:.2f}")
                print(f"Max audio level: {max_level:.2f}")
                
                if max_level < 500:
                    print("⚠️ Low audio levels detected. Try adjusting microphone volume.")
                elif max_level > 30000:
                    print("⚠️ Very high audio levels detected. Microphone may be too close or volume too high.")
                else:
                    print("✅ Audio levels look good")
        
        # If visualizing, wait for plot to be closed
        if args.visualize and 'visualization_thread' in locals():
            visualization_thread.join()
            
    finally:
        # Clean up
        diagnostic.cleanup()

if __name__ == "__main__":
    main() 