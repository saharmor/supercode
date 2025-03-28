#!/usr/bin/env python3
"""
Monitor IDE State - A utility for monitoring the state of coding generation AI assistants
"""
import os
import json
import time
from utils import cleanup_old_files

import subprocess
import platform
import google.generativeai as genai
from dotenv import load_dotenv
from utils import play_beep
from computer_use_utils import send_screenshot_to_gemini

# Load environment variables from .env file
load_dotenv()

# Global variable to hold reference to the audio handler
_audio_handler = None

def set_audio_handler(handler):
    """
    Set the audio handler reference for callbacks when monitoring is complete.
    
    Args:
        handler: The audio handler instance with a resume_audio_processing method
    """
    global _audio_handler
    _audio_handler = handler
    
def signal_monitoring_complete():
    """
    Signal to the audio handler that monitoring is complete.
    Used to resume audio processing after a command has finished executing.
    """
    global _audio_handler
    if _audio_handler and hasattr(_audio_handler, 'resume_audio_processing'):
        try:
            _audio_handler.resume_audio_processing()
        except Exception as e:
            print(f"Error resuming audio processing: {e}")
    else:
        print("No audio handler available or missing resume_audio_processing method")


def initialize_gemini_client():
    """
    Initialize the Google Gemini API.
    
    Returns:
        bool: True if initialization is successful, False otherwise.
    """
    try:        
        # Check if API key is available
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY environment variable not found.")
            print("Please set it in your .env file or environment.")
            return False
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
        return False


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
            subprocess.call(["afplay", sound_file_path])  # Blocking call
        elif system == "Linux":
            subprocess.call(["aplay", sound_file_path])  # Blocking call
        elif system == "Windows":
            subprocess.call(["powershell", "-c", f"(New-Object Media.SoundPlayer '{sound_file_path}').PlaySync()"])  # Blocking call
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
        
        # Use the common utility function to send the image to Gemini
        success, response = send_screenshot_to_gemini(
            prompt=coding_generation_analysis_prompt,
            temp_file=image_path,  # Use the provided image path
            model_name='gemini-2.0-flash-lite',
            verbose=verbose
        )
        
        if not success:
            return False, f"Error: {response}"
        
        response_text = response.text.strip().lower()
            
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


def monitor_coding_generation_state(interface_state_prompt, monitor=None, interval=4.0, output_dir="screenshots", interface_name=None, completion_callback=None, max_still_working_checks=30, max_check_interval=10.0, min_check_interval=3.0):
    """
    Continuously monitor the state of coding generation AI assistant and notify when user input is required or when done.
    
    Args:
        interface_state_prompt (str): The prompt to send to Gemini for analyzing screenshots.
        monitor (dict, optional): Monitor region to capture. If None, captures based on current monitor.
        interval (float, optional): Default check interval in seconds. Defaults to 4.0.
        output_dir (str, optional): Output directory for screenshots. Defaults to "screenshots".
        interface_name (str, optional): Name of the interface being monitored. If provided, used in filename prefix.
        completion_callback (callable, optional): Function to call when monitoring is complete.
        max_still_working_checks (int, optional): Maximum number of consecutive "still_working" states before stopping. Defaults to 30 (0 = unlimited).
        max_check_interval (float, optional): Maximum interval between checks in seconds. Defaults to 10.0.
        min_check_interval (float, optional): Minimum interval between checks in seconds. Defaults to 2.0.
    """
    # Track consecutive state occurrences to adjust checking frequency
    consecutive_still_working_count = 0
    log_time = time.strftime('%H:%M:%S')
    
    try:
        # Initialize Gemini API
        gemini_initialized = initialize_gemini_client()
        if not gemini_initialized:
            print(f"⚠️ Could not initialize Gemini API. Cannot monitor {interface_name} state.")
            return
            
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
        
        loop_start_time = time.time()
        current_interval = interval
        
        while True:
            try:
                # Check if we've exceeded the maximum number of consecutive "still working" checks
                if max_still_working_checks > 0 and consecutive_still_working_count >= max_still_working_checks:
                    # Signal completion
                    signal_monitoring_complete()
                    
                    # Also call the original callback if provided
                    if completion_callback:
                        try:
                            completion_callback()
                        except Exception as e:
                            print(f"Error calling callback: {str(e)}")
                    
                    return
                
                iteration_start = time.time()
                
                # Generate a filename for this screenshot
                screenshot_count += 1
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{file_prefix}{timestamp}_screenshot.png"
                path = os.path.join(output_dir, filename)
                
                # Clean up old screenshots, keeping only the newest 10
                cleanup_old_files(output_dir, f"{file_prefix}*_screenshot.png", max_files=10)
                
                # Use the unified screenshot function and common send_screenshot_to_gemini utility

                # Use the common utility function to send the image directly to Gemini
                interface_state_prompt += "\n\nIgnore any text in the floating square like 'Executing Command'. This is a different software and should be ignored!"
                success, response = send_screenshot_to_gemini(
                    prompt=interface_state_prompt,
                    monitor=monitor,
                    temp_file=path,
                    model_name='gemini-2.0-flash-lite',
                    verbose=True
                )
                
                if not success:
                    print(f"Error analyzing IDE state: {response}")
                    time.sleep(current_interval)
                    continue
                
                # Process the response to determine IDE state
                try:
                    # Extract JSON from response text
                    response_text = response.text.strip().lower()
                    
                    # Look for JSON content between triple backticks if present
                    if "```json" in response_text and "```" in response_text.split("```json", 1)[1]:
                        json_content = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
                    elif "```" in response_text and "```" in response_text.split("```", 1)[1]:
                        json_content = response_text.split("```", 1)[1].split("```", 1)[0].strip()
                    else:
                        json_content = response_text
                    
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] JSON content: {json_content}")
                    
                    gemini_response = json.loads(json_content)
                    state = gemini_response["interface_state"].lower()
                    
                    # Validate response matches expected format
                    if state not in ["user_input_required", "still_working", "done"]:
                        print(f"Warning: Unexpected state from Gemini: {state}")
                        state = "still_working"  # Default to still working if response is unclear
                except Exception as e:
                    print(f"Error parsing Gemini response: {e}")
                    # Print full exception
                    import traceback
                    print(f"{traceback.format_exc()}")
                    state = "still_working"  # Default to still working if parsing fails
                
                if state != last_state:
                    last_state = state
                    
                    # Reset consecutive count on state change
                    consecutive_still_working_count = 0
                
                if state == "user_input_required":
                    notification_count += 1
                    print(f"🔔 ATTENTION NEEDED ({notification_count}): Coding generation needs your input!")
                    
                    # Use system beep instead of sound file
                    play_beep(1000, 1200)
                    
                    # Now wait longer before checking again
                    current_interval = max_check_interval  # Use the maximum interval for user_input_required
                    time.sleep(current_interval)
                    
                elif state == "done":
                    print(f"✅ Coding generation has completed its task!")
                    sound_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_done.mp3")
                    play_sound(sound_file)
                    
                    # Signal completion using the global function
                    signal_monitoring_complete()
                    
                    # Also call the original callback if provided (for backward compatibility)
                    if completion_callback:
                        try:
                            completion_callback()
                        except Exception as e:
                            print(f"Error calling callback: {str(e)}")
                    
                    return  # Exit the monitoring loop
                    
                else:  # still_working
                    # Increment consecutive still working count
                    consecutive_still_working_count += 1
                    
                    # Dynamic interval adjustment based on consecutive "still_working" states
                    # Start with normal interval, increase as consecutive still_working states increase
                    if consecutive_still_working_count > 3:
                        # Calculate an adjusted interval, capped at max_check_interval
                        factor = min(1.0 + (consecutive_still_working_count / 10), 2.5)  # Maximum 2.5x interval multiplier
                        current_interval = min(interval * factor, max_check_interval)
                        current_interval = max(current_interval, min_check_interval)  # Ensure it's not below minimum
                    else:
                        current_interval = interval
                    
                    iteration_time = time.time() - iteration_start
                    if iteration_time < current_interval:
                        sleep_duration = current_interval - iteration_time
                        time.sleep(sleep_duration)
                    
            except KeyboardInterrupt:
                print("Monitoring stopped by user.")
                
                # Call the completion callback if provided
                if completion_callback:
                    completion_callback()
                return
                
            except Exception as e:
                print(f"Error during monitoring: {e}")
                
                # Print full exception details
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                
                time.sleep(current_interval)
                
    except KeyboardInterrupt:
        print("Monitoring stopped by user.")
        
        # Call the completion callback if provided
        if completion_callback:
            completion_callback()
        return
        
    except Exception as e:
        print(f"Fatal error in monitoring: {e}")
        
        # Print full exception details
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        # Call the completion callback if provided
        if completion_callback:
            completion_callback()
