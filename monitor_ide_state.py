#!/usr/bin/env python3
"""
Monitor IDE State - A utility for monitoring the state of coding generation AI assistants
"""
import os
import sys
import json
import time
import datetime
import subprocess
import platform
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
from utils import play_beep

def initialize_gemini_client():
    """
    Initialize the Google Gemini API.
    
    Returns:
        bool: True if initialization is successful, False otherwise.
    """
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Check if API key is available
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Error: GOOGLE_API_KEY environment variable not found.")
            print("Please set it in your .env file or environment.")
            return False
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
        return False


def capture_screen():
    """
    Capture the entire screen.
    
    Returns:
        PIL.Image: The captured screenshot as a PIL Image.
    """
    try:
        # Use screencapture command to capture the screen to a temporary file
        timestamp = int(time.time())
        temp_file = f"/tmp/screenshot_{timestamp}.png"
        
        subprocess.run(["screencapture", "-x", temp_file], check=True)
        
        # Open the image with PIL
        img = Image.open(temp_file)
        
        # Remove the temporary file
        os.remove(temp_file)
        
        return img
    except Exception as e:
        print(f"Error capturing screen: {e}")
        return None


def play_sound(sound_file_path):
    """
    Play a sound file using the appropriate command for the operating system.
    
    Args:
        sound_file_path (str): Path to the sound file to play.
    """
    if not os.path.exists(sound_file_path):
        print(f"Warning: Sound file not found at {sound_file_path}")
        return
        
    try:
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.Popen(["afplay", sound_file_path])
        elif system == "Linux":
            subprocess.Popen(["aplay", sound_file_path])
        elif system == "Windows":
            subprocess.Popen(["powershell", "-c", f"(New-Object Media.SoundPlayer '{sound_file_path}').PlaySync()"])
        else:
            print(f"Sound playback not supported on {system}")
    except Exception as e:
        print(f"Error playing sound: {e}")


def analyze_coding_generation_state(coding_generation_analysis_prompt, image_path, initialize_if_needed=True, verbose=False, interface_name="Cascade"):
    """
    Specialized function to analyze the state of coding generation AI assistant in a screenshot.
    
    Args:
        image_path (str): Path to the image file.
        initialize_if_needed (bool, optional): Whether to initialize Gemini if needed. Defaults to True.
        verbose (bool, optional): Whether to print detailed logs. Defaults to False.
        interface_name (str, optional): Name of the interface being analyzed. Defaults to "Cascade".
        coding_generation_analysis_prompt (str, optional): Custom prompt for analysis. If None, uses default.
        
    Returns:
        tuple: (bool, str) - (Whether action is needed, State description: "user_input_required", "still_working", or "done")
    """
    try:
        # Initialize Gemini if needed
        if initialize_if_needed:
            success = initialize_gemini_client()
            if not success:
                return False, "Failed to initialize Gemini client"
        
        # Load and prepare the image
        with Image.open(image_path) as img:
            # Ensure image is in RGB format for compatibility
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Get Gemini model
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            
            # Get response from Gemini with timing
            start_time = time.time()
            response = model.generate_content([coding_generation_analysis_prompt, img])
            end_time = time.time()
            elapsed_time = end_time - start_time
            if verbose:
                print(f"Gemini analysis took {elapsed_time:.2f} seconds")
            
            response_text = response.text.strip().lower()
            if verbose:
                print(f"Gemini response: {response_text}")
            
            # Extract JSON from response text
            try:
                # Look for JSON content between triple backticks if present
                if "```json" in response_text and "```" in response_text.split("```json", 1)[1]:
                    json_content = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                elif "```" in response_text and "```" in response_text.split("```", 1)[1]:
                    json_content = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                else:
                    json_content = response_text
                
                gemini_response = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                # Create a default response
                gemini_response = {"interface_state": "still_working", "reasoning": "Failed to parse response"}
            
                
            state = gemini_response["interface_state"].lower()
            
            user_action_needed = state == "user_input_required"
            done = state == "done"
            
            # Validate response matches expected format
            if state not in ["user_input_required", "still_working", "done"]:
                print(f"Warning: Unexpected state from Gemini: {state}")
                state = "still_working"  # Default to still working if response is unclear
                
            return user_action_needed or done, state
            
    except Exception as e:
        print(f"Error analyzing {interface_name} state: {e}")
        return False, f"Error: {str(e)}"


def monitor_coding_generation_state(interface_state_prompt, interval=4.0, output_dir="screenshots", interface_name=None):
    """
    Continuously monitor the state of coding generation AI assistant and notify when user input is required or when done.
    
    Args:
        interface_state_prompt (str): The prompt to send to Gemini for analyzing screenshots.
        interval (float, optional): Default check interval in seconds. Defaults to 4.0.
        output_dir (str, optional): Output directory for screenshots. Defaults to "screenshots".
        interface_name (str, optional): Name of the interface being monitored. If provided, used in filename prefix.
    """
    try:
        # Initialize Gemini API
        gemini_initialized = initialize_gemini_client()
        if not gemini_initialized:
            print(f"⚠️ Could not initialize Gemini API. Cannot monitor {interface_name} state.")
            return
            
        print(f"🔍 Starting {interface_name} state monitoring...")
        print("   - Will notify when coding generation needs your input or is done")
        print("   - Press Ctrl+C to stop monitoring")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Set the filename prefix based on interface name if provided
        if interface_name:
            file_prefix = f"{interface_name}_"
        else:
            file_prefix = 'interface_'
            
        screenshot_count = 0
        notification_count = 0
        last_state = None
        
        # wait for two seconds before starting
        time.sleep(2)
        
        while True:
            try:
                # Take a screenshot
                screenshot_count += 1
                image = capture_screen()
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{file_prefix}{timestamp}_screenshot.png"
                path = os.path.join(output_dir, filename)
                
                # Save the screenshot
                image.save(path)
                print(f"\rChecking coding generation state ({screenshot_count})...", end="")
                
                # Analyze the screenshot to determine coding generation state
                _, state = analyze_coding_generation_state(interface_state_prompt, path, False, interface_name=interface_name, verbose=True)  # No need to reinitialize
                
                if state != last_state:
                    print(f"\nCoding generation state: {state}")
                    last_state = state
                
                if state == "user_input_required":
                    notification_count += 1
                    print(f"\n🔔 ATTENTION NEEDED ({notification_count}): Coding generation needs your input!")
                    # Use system beep instead of sound file
                    play_beep(1000, 1200)
                    # Now wait longer before checking again
                    time.sleep(10)
                    
                elif state == "done":
                    print("\n✅ Coding generation has completed its task!")
                    sound_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_done.mp3")
                    play_sound(sound_file)
                    return  # Exit the monitoring loop
                    
                else:  # still_working
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped by user.")
                return
                
            except Exception as e:
                print(f"\nError during monitoring: {e}")
                time.sleep(interval)
                
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
        return
