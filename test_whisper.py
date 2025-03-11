#!/usr/bin/env python3
"""
Simple test script for Whisper and audio recording.
This helps diagnose segmentation fault issues in SuperSurf.
"""

import os
import sys
import time
import logging
import traceback
import pyaudio
import wave
import tempfile
import threading
import whisper
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestWhisper")

def main():
    try:
        # Load environment variables
        load_dotenv()
        
        # Disable GPU usage
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['PYTORCH_NUM_THREADS'] = '1'
        
        # Setup audio
        logger.info("Initializing audio...")
        audio = pyaudio.PyAudio()
        
        # Print audio devices
        print("Available audio input devices:")
        device_indices = []
        for i in range(audio.get_device_count()):
            try:
                device_info = audio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels') > 0:  # Input device
                    name = device_info.get('name')
                    print(f"  Device {i}: {name}")
                    device_indices.append(i)
            except Exception as e:
                print(f"Error getting device info for index {i}: {str(e)}")
        
        # Get device index from environment or use first available
        device_index = os.getenv("AUDIO_DEVICE_INDEX")
        if device_index:
            try:
                device_index = int(device_index)
                print(f"User-specified audio device index: {device_index}")
            except:
                device_index = None
                
        # If device index is not provided or invalid, use first available
        if not device_index or device_index not in device_indices:
            if device_indices:
                device_index = device_indices[0]
                print(f"Using first available audio device: {device_index}")
            else:
                print("No audio input devices found")
                return 1
        
        # Update .env file
        with open('.env', 'r') as f:
            env_file = f.read()
            
        # Update AUDIO_DEVICE_INDEX in .env file
        if 'AUDIO_DEVICE_INDEX' in env_file:
            env_file = '\n'.join([
                line if not line.startswith('AUDIO_DEVICE_INDEX=') else f'AUDIO_DEVICE_INDEX={device_index}'
                for line in env_file.split('\n')
            ])
            
            with open('.env', 'w') as f:
                f.write(env_file)
                
            print(f"Updated .env file with AUDIO_DEVICE_INDEX={device_index}")
        
        # Load Whisper model
        model_name = os.getenv("WHISPER_MODEL_SIZE", "base")
        logger.info(f"Loading Whisper model: {model_name}")
        model = whisper.load_model(model_name, device="cpu")
        logger.info("Model loaded successfully")
        
        # Test recording function
        def test_recording():
            logger.info("Starting audio recording test...")
            
            # Setup recording
            format_code = pyaudio.paInt16
            channels = 1
            sample_rate = int(os.getenv("SAMPLE_RATE", "16000"))
            chunk = 1024
            record_seconds = 5
            
            try:
                # Open stream
                stream = audio.open(
                    format=format_code,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=chunk
                )
                
                logger.info(f"Recording {record_seconds} seconds of audio...")
                frames = []
                
                # Record audio
                for i in range(0, int(sample_rate / chunk * record_seconds)):
                    data = stream.read(chunk, exception_on_overflow=False)
                    frames.append(data)
                
                # Stop and close the stream
                stream.stop_stream()
                stream.close()
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    wav_file = tmp_file.name
                
                with wave.open(wav_file, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(audio.get_sample_size(format_code))
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(frames))
                
                logger.info(f"Audio saved to {wav_file}")
                
                # Transcribe audio
                logger.info("Transcribing audio...")
                result = model.transcribe(
                    wav_file, 
                    language="en",
                    fp16=False
                )
                
                text = result["text"].strip()
                logger.info(f"Transcription: '{text}'")
                
                # Cleanup
                try:
                    os.unlink(wav_file)
                except:
                    pass
                
                return text
                
            except Exception as e:
                logger.error(f"Error in recording: {str(e)}")
                traceback.print_exc()
                return None
        
        # Execute test
        result = test_recording()
        
        # Close audio
        audio.terminate()
        
        if result:
            logger.info("Test completed successfully!")
        else:
            logger.error("Test failed to produce transcription")
        
    except Exception as e:
        logger.error(f"Error in test script: {str(e)}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 