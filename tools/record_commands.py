#!/usr/bin/env python3
"""
Tool for recording command examples for fine-tuning Whisper models.
This script helps collect training data for fine-tuning Whisper to better
recognize your voice and specific command patterns.
"""

import os
import json
import argparse
import time
import pyaudio
import wave
import threading
import numpy as np
from datetime import datetime

PREDEFINED_COMMANDS = [
    "surf save",
    "surf undo",
    "surf redo",
    "surf copy",
    "surf paste",
    "surf cut",
    "surf select all",
    "surf find example",
    "surf next",
    "surf previous",
    "surf go to line 10",
    "surf top",
    "surf bottom",
    "surf type hello world"
]

class CommandRecorder:
    def __init__(self, output_dir, sample_rate=16000, format_code=pyaudio.paInt16, channels=1, chunk_size=1024):
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.format_code = format_code
        self.channels = channels
        self.chunk_size = chunk_size
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(output_dir, "data")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        
        # Dataset collection
        self.dataset = []
        self.current_command = None
        
    def list_devices(self):
        """List available audio input devices"""
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        print("\nAvailable audio input devices:")
        for i in range(0, num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  Device {i}: {device_info.get('name')}")
                
        # Print default input device
        default_input = self.audio.get_default_input_device_info()
        print(f"Default input device: {default_input.get('name')}\n")
        
    def record_command(self, command, duration=3, device_index=None):
        """Record a single command example"""
        self.current_command = command
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        command_slug = command.replace(" ", "_").lower()
        filename = f"{command_slug}_{timestamp}.wav"
        filepath = os.path.join(self.data_dir, filename)
        
        # Start recording
        print(f"\nRecording: '{command}'")
        print(f"Speak in 3...")
        time.sleep(1)
        print(f"2...")
        time.sleep(1)
        print(f"1...")
        time.sleep(1)
        print(f"GO! (recording for {duration} seconds)")
        
        frames = []
        stream = self.audio.open(
            format=self.format_code,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk_size
        )
        
        # Record for the specified duration
        for i in range(0, int(self.sample_rate / self.chunk_size * duration)):
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            frames.append(data)
            
            # Print progress
            progress = int((i / (self.sample_rate / self.chunk_size * duration)) * 20)
            print(f"\r[{'#' * progress}{' ' * (20 - progress)}] {i / (self.sample_rate / self.chunk_size * duration):.0%}", end="")
            
        print("\r[####################] 100%")
        print(f"Finished recording: {filepath}")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Save the audio to a WAV file
        waveFile = wave.open(filepath, 'wb')
        waveFile.setnchannels(self.channels)
        waveFile.setsampwidth(self.audio.get_sample_size(self.format_code))
        waveFile.setframerate(self.sample_rate)
        waveFile.writeframes(b''.join(frames))
        waveFile.close()
        
        # Add to dataset
        self.dataset.append({
            "audio_path": filepath,
            "text": command
        })
        
        return filepath
        
    def save_dataset(self):
        """Save the dataset to a JSON file"""
        # Make paths relative to the output directory
        relative_dataset = []
        for item in self.dataset:
            relative_path = os.path.relpath(item["audio_path"], start=os.path.dirname(self.output_dir))
            relative_dataset.append({
                "audio_path": relative_path,
                "text": item["text"]
            })
            
        dataset_path = os.path.join(self.output_dir, "commands.json")
        with open(dataset_path, 'w') as f:
            json.dump(relative_dataset, f, indent=2)
            
        print(f"\nDataset saved to {dataset_path}")
        print(f"Total recordings: {len(self.dataset)}")
        
    def run_interactive_session(self):
        """Run an interactive recording session"""
        print("\n=== Command Recording Tool for Whisper Fine-tuning ===")
        print("This tool will help you record examples of voice commands")
        print("for fine-tuning the Whisper model in SuperSurf.")
        
        # List available devices
        self.list_devices()
        
        # Ask for device selection
        device_index = input("Enter device index to use (leave blank for default): ")
        if device_index.strip():
            device_index = int(device_index)
        else:
            device_index = None
            
        # Ask for recording duration
        duration_str = input("Enter recording duration in seconds (default: 3): ")
        duration = int(duration_str) if duration_str.strip() else 3
        
        # Start the session
        while True:
            print("\n=== Recording Options ===")
            print("1. Record predefined commands")
            print("2. Record custom command")
            print("3. Save dataset and exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == "1":
                # Record predefined commands
                print("\n=== Predefined Commands ===")
                for i, cmd in enumerate(PREDEFINED_COMMANDS):
                    print(f"{i+1}. {cmd}")
                    
                cmd_choice = input("\nEnter command number to record (or 'all' for all): ")
                
                if cmd_choice.lower() == "all":
                    # Record all commands
                    for cmd in PREDEFINED_COMMANDS:
                        self.record_command(cmd, duration, device_index)
                        time.sleep(1)  # Pause between recordings
                else:
                    # Record selected command
                    try:
                        idx = int(cmd_choice) - 1
                        if 0 <= idx < len(PREDEFINED_COMMANDS):
                            self.record_command(PREDEFINED_COMMANDS[idx], duration, device_index)
                        else:
                            print("Invalid command number.")
                    except ValueError:
                        print("Please enter a valid number or 'all'.")
                        
            elif choice == "2":
                # Record custom command
                custom_cmd = input("\nEnter custom command to record: ")
                if custom_cmd.strip():
                    if not custom_cmd.lower().startswith("surf"):
                        print("Adding 'surf' prefix for consistency")
                        custom_cmd = "surf " + custom_cmd
                    self.record_command(custom_cmd, duration, device_index)
                else:
                    print("Command cannot be empty.")
                    
            elif choice == "3":
                # Save and exit
                self.save_dataset()
                break
                
            else:
                print("Invalid choice. Please enter 1-3.")
        
        # Clean up
        self.audio.terminate()
        print("\nThank you for recording command examples!")
        print("Use these recordings with the fine-tuning script to improve accuracy.")

def main():
    parser = argparse.ArgumentParser(description="Record command examples for fine-tuning Whisper")
    parser.add_argument("--output-dir", type=str, default="./fine_tuning", 
                       help="Directory to save recordings and dataset")
    args = parser.parse_args()
    
    recorder = CommandRecorder(args.output_dir)
    recorder.run_interactive_session()
    
if __name__ == "__main__":
    main() 