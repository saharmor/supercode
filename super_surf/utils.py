import os
import json
import subprocess
import pyaudio
import logging
import re

logger = logging.getLogger(__name__)

def get_app_config_dir():
    """
    Get the application configuration directory
    
    Returns:
        str: Path to the configuration directory
    """
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".supersurf")
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    return config_dir

def save_config(config):
    """
    Save configuration to file
    
    Args:
        config (dict): Configuration dictionary
    """
    config_dir = get_app_config_dir()
    config_file = os.path.join(config_dir, "config.json")
    
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)

def load_config():
    """
    Load configuration from file
    
    Returns:
        dict: Configuration dictionary
    """
    config_dir = get_app_config_dir()
    config_file = os.path.join(config_dir, "config.json")
    
    if not os.path.exists(config_file):
        # Default configuration
        default_config = {
            "model_size": "base",
            "activation_phrase": "surf",
            "hotkey": "cmd+shift+space"
        }
        save_config(default_config)
        return default_config
    
    with open(config_file, "r") as f:
        return json.load(f)

def is_windsurf_running():
    """
    Check if Windsurf IDE is running
    
    Returns:
        bool: True if Windsurf is running, False otherwise
    """
    try:
        # More reliable way to check if Windusrf is running
        output = subprocess.check_output(["ps", "-A"])
        return b"Windusrf" in output or b"windsurf" in output
    except subprocess.CalledProcessError:
        return False

def focus_surf_app():
    """
    Bring Windsurf IDE to focus
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        subprocess.run(["osascript", "-e", 'tell application "Surf" to activate'])
        return True
    except Exception as e:
        print(f"Error focusing Windsurf app: {e}")
        return False

def validate_audio_device(device_index):
    """
    Validate if the audio device index is valid and available
    
    Args:
        device_index: The index of the audio device to validate
        
    Returns:
        bool: True if the device is valid, False otherwise
    """
    try:
        # First convert to int if it's a string
        if device_index is not None:
            try:
                device_index = int(device_index)
            except (ValueError, TypeError):
                logger.warning(f"Invalid audio device index: {device_index}")
                return False
                
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Get available input devices
        input_devices = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                input_devices.append(i)
                
        # Clean up
        p.terminate()
        
        # Check if the device index is valid
        if device_index in input_devices:
            return True
        else:
            logger.warning(f"Audio device index {device_index} not found in available devices: {input_devices}")
            return False
            
    except Exception as e:
        logger.error(f"Error validating audio device: {e}")
        return False

def update_audio_device_env():
    """
    Update the .env file with a valid audio device index
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Get available input devices
        input_devices = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                input_devices.append((i, device_info.get('name', f"Device {i}")))
                
        # Clean up
        p.terminate()
        
        if not input_devices:
            logger.error("No audio input devices found")
            return False
            
        # Use the first available device
        device_index, device_name = input_devices[0]
        logger.info(f"Using audio device: {device_name} (index: {device_index})")
        
        # Update .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        
        if not os.path.exists(env_path):
            logger.error(f".env file not found at {env_path}")
            return False
            
        with open(env_path, 'r') as f:
            env_content = f.read()
            
        # Replace or add the AUDIO_DEVICE_INDEX line
        pattern = r'^AUDIO_DEVICE_INDEX=.*$'
        replacement = f'AUDIO_DEVICE_INDEX={device_index}'
        
        if re.search(pattern, env_content, re.MULTILINE):
            # Replace existing line
            env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
        else:
            # Add new line
            env_content += f'\n{replacement}\n'
            
        with open(env_path, 'w') as f:
            f.write(env_content)
            
        logger.info(f"Updated .env file with AUDIO_DEVICE_INDEX={device_index}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating audio device in .env: {e}")
        return False