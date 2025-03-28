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


def monitor_coding_generation_state(interface_state_prompt, monitor=None, interval=4.0, output_dir="screenshots", interface_name=None, completion_callback=None):
    # Debug: Print whether we have a callback
    log_time = time.strftime('%H:%M:%S')    # Track consecutive state occurrences to adjust checking frequency
    consecutive_still_working_count = 0
    
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
        log_time = time.strftime('%H:%M:%S')
        print(f"[{log_time}] Initializing Gemini API")
        gemini_initialized = initialize_gemini_client()
        if not gemini_initialized:
            log_time = time.strftime('%H:%M:%S')
            print(f"[{log_time}] ⚠️ Could not initialize Gemini API. Cannot monitor {interface_name} state.")
            return
            
        log_time = time.strftime('%H:%M:%S')
        print(f"[{log_time}] 🔍 Starting {interface_name} state monitoring...")
        print(f"[{log_time}] - Will notify when coding generation needs your input or is done")
        print(f"[{log_time}] - Press Ctrl+C to stop monitoring")
        
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
        log_time = time.strftime('%H:%M:%S')
        print(f"[{log_time}] Waiting 2 seconds before starting monitoring loop")
        time.sleep(2)
        
        loop_start_time = time.time()
        current_interval = interval
        
        while True:
            try:
                iteration_start = time.time()
                log_time = time.strftime('%H:%M:%S')
                
                # Generate a filename for this screenshot
                screenshot_count += 1
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{file_prefix}{timestamp}_screenshot.png"
                path = os.path.join(output_dir, filename)
                
                # Clean up old screenshots, keeping only the newest 10
                cleanup_old_files(output_dir, f"{file_prefix}*_screenshot.png", max_files=10)
                
                # Use the unified screenshot function and common send_screenshot_to_gemini utility

                # Use the common utility function to send the image directly to Gemini
                capture_start = time.time()
                interface_state_prompt += "\n\nIgnore any text in the floating square like 'Executing Command'. This is a different software and should be ignored!"
                success, response = send_screenshot_to_gemini(
                    prompt=interface_state_prompt,
                    monitor=monitor,
                    temp_file=path,
                    model_name='gemini-2.0-flash-lite',
                    verbose=True
                )
                capture_time = time.time() - capture_start
                log_time = time.strftime('%H:%M:%S')
                print(f"[{log_time}] Screenshot capture and analysis took {capture_time:.2f}s")
                
                if not success:
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Error analyzing IDE state: {response}")
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
                        log_time = time.strftime('%H:%M:%S')
                        print(f"[{log_time}] Warning: Unexpected state from Gemini: {state}")
                        state = "still_working"  # Default to still working if response is unclear
                except Exception as e:
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Error parsing Gemini response: {e}")
                    # Print full exception
                    import traceback
                    print(f"[{log_time}] {traceback.format_exc()}")
                    state = "still_working"  # Default to still working if parsing fails
                
                if state != last_state:
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Coding generation state changed: {state}")
                    last_state = state
                    
                    # Reset consecutive count on state change
                    consecutive_still_working_count = 0
                else:
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Coding generation state unchanged: {state}")
                
                if state == "user_input_required":
                    notification_count += 1
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] 🔔 ATTENTION NEEDED ({notification_count}): Coding generation needs your input!")
                    
                    # Use system beep instead of sound file
                    play_beep(1000, 1200)
                    
                    # Now wait longer before checking again
                    current_interval = 10.0  # Longer interval for user_input_required
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Waiting {current_interval} seconds before next check due to user input required")
                    time.sleep(current_interval)
                    
                elif state == "done":
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] ✅ Coding generation has completed its task!")
                    sound_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_done.mp3")
                    play_sound(sound_file)
                    
                    # Signal completion using the global function
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Signaling monitoring complete")
                    signal_monitoring_complete()
                    
                    # Also call the original callback if provided (for backward compatibility)
                    if completion_callback:
                        log_time = time.strftime('%H:%M:%S')
                        print(f"[{log_time}] Calling completion callback")
                        try:
                            completion_callback()
                        except Exception as e:
                            log_time = time.strftime('%H:%M:%S')
                            print(f"[{log_time}] Error calling callback: {str(e)}")
                    
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Exiting monitoring loop due to completion")
                    return  # Exit the monitoring loop
                    
                else:  # still_working
                    # Increment consecutive still working count
                    consecutive_still_working_count += 1
                    
                    # Dynamic interval adjustment based on consecutive "still_working" states
                    # Start with normal interval, decrease as consecutive still_working states increase
                    if consecutive_still_working_count > 3:
                        # Calculate a reduced interval, minimum 2 seconds
                        current_interval = max(2, interval / (1 + consecutive_still_working_count / 5))
                    else:
                        current_interval = interval
                        
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Still working (count: {consecutive_still_working_count}), waiting {current_interval:.1f} seconds before next check")
                    
                    iteration_time = time.time() - iteration_start
                    if iteration_time < current_interval:
                        sleep_duration = current_interval - iteration_time
                        time.sleep(sleep_duration)
                    
            except KeyboardInterrupt:
                log_time = time.strftime('%H:%M:%S')
                print(f"[{log_time}] Monitoring stopped by user.")
                
                # Call the completion callback if provided
                if completion_callback:
                    log_time = time.strftime('%H:%M:%S')
                    print(f"[{log_time}] Calling completion callback due to keyboard interrupt")
                    completion_callback()
                return
                
            except Exception as e:
                log_time = time.strftime('%H:%M:%S')
                print(f"[{log_time}] Error during monitoring: {e}")
                
                # Print full exception details
                import traceback
                print(f"[{log_time}] Traceback: {traceback.format_exc()}")
                
                log_time = time.strftime('%H:%M:%S')
                print(f"[{log_time}] Waiting {current_interval} seconds before retrying")
                time.sleep(current_interval)
                
    except KeyboardInterrupt:
        log_time = time.strftime('%H:%M:%S')
        print(f"[{log_time}] Monitoring stopped by user.")
        
        # Call the completion callback if provided
        if completion_callback:
            log_time = time.strftime('%H:%M:%S')
            print(f"[{log_time}] Calling completion callback due to keyboard interrupt (outer)")
            completion_callback()
        return
        
    except Exception as e:
        log_time = time.strftime('%H:%M:%S')
        print(f"[{log_time}] Fatal error in monitoring: {e}")
        
        # Print full exception details
        import traceback
        print(f"[{log_time}] Traceback: {traceback.format_exc()}")
        
        # Call the completion callback if provided
        if completion_callback:
            log_time = time.strftime('%H:%M:%S')
            print(f"[{log_time}] Calling completion callback due to fatal error")
            completion_callback()
