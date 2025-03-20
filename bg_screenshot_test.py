#!/usr/bin/env python3
"""
Screenshot Utility for macOS

This script allows taking screenshots of specific windows based on their title,
saves them to disk with the current timestamp, and can analyze images using Google Gemini
to detect specific content like the word "Done".
"""
import os
import sys
import json
import time
import datetime
import argparse
import tty
import termios
import platform
from PIL import Image
import subprocess
import google.generativeai as genai
from dotenv import load_dotenv
from utils import play_beep

def get_window_list():
    """
    Get a list of all open windows using osascript.
    
    Returns:
        list: A list of dictionaries containing window information.
    """
    try:
        # Simplified AppleScript to get windows - this avoids complex parsing issues
        script = '''
        set output to ""
        tell application "System Events"
            set allProcesses to processes whose background only is false
            repeat with theProcess in allProcesses
                set processName to name of theProcess
                set pid to unix id of theProcess
                if exists (windows of theProcess) then
                    repeat with theWindow in windows of theProcess
                        set windowName to name of theWindow
                        if windowName is not "" then
                            set output to output & processName & "###" & windowName & "###" & pid & "\n"
                        end if
                    end repeat
                end if
            end repeat
        end tell
        return output
        '''
        
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error getting window list: {result.stderr}")
            return []
        
        # Parse the output
        windows = []
        for line in result.stdout.strip().split("\n"):
            if line.strip() == "":
                continue
                
            parts = line.split("###")
            if len(parts) >= 3:
                window = {
                    'app_name': parts[0],
                    'window_title': parts[1],
                    'pid': int(parts[2]) if parts[2].isdigit() else 0
                }
                windows.append(window)
        
        return windows
        
    except Exception as e:
        print(f"Error getting window list: {e}")
        return []
        
    except Exception as e:
        print(f"Error getting window list: {e}")
        return []


def getch():
    """
    Read a single character from the terminal without requiring Enter to be pressed.
    
    Returns:
        str: The character read.
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def get_arrow_key():
    """
    Get arrow key presses from the terminal.
    
    Returns:
        str: One of 'up', 'down', 'left', 'right', 'enter', or the character pressed.
    """
    first_ch = getch()
    if first_ch == '\x1b':
        second_ch = getch()
        if second_ch == '[':
            third_ch = getch()
            if third_ch == 'A':
                return 'up'
            elif third_ch == 'B':
                return 'down'
            elif third_ch == 'C':
                return 'right'
            elif third_ch == 'D':
                return 'left'
    elif first_ch == '\r' or first_ch == '\n':
        return 'enter'
    return first_ch


def interactive_window_select(matching_windows):
    """
    Present an interactive menu to select a window using arrow keys.
    
    Args:
        matching_windows (list): List of window dictionaries to choose from.
        
    Returns:
        dict: The selected window information or None if canceled.
    """
    if not matching_windows:
        return None
    
    # If only one window matches, return it directly
    if len(matching_windows) == 1:
        return matching_windows[0]
    
    selected_index = 0
    
    print(f"\nFound {len(matching_windows)} matching windows.")
    print("Use Up/Down arrow keys to navigate and Enter to select:\n")
    
    # Initial display
    for i, win in enumerate(matching_windows):
        prefix = "→ " if i == selected_index else "  "
        print(f"{prefix}{win['app_name']} - {win['window_title']}")
    
    # Move cursor up to the start of the list
    print(f"\033[{len(matching_windows)}A", end="")
    
    while True:
        key = get_arrow_key()
        
        if key == 'up' and selected_index > 0:
            selected_index -= 1
        elif key == 'down' and selected_index < len(matching_windows) - 1:
            selected_index += 1
        elif key == 'enter':
            break
        elif key == 'q' or key == '\x03':  # 'q' or Ctrl+C to cancel
            print(f"\033[{len(matching_windows)}B")  # Move cursor down below the list
            return None
        
        # Redraw the list with the new selection
        for i, win in enumerate(matching_windows):
            prefix = "→ " if i == selected_index else "  "
            print(f"{prefix}{win['app_name']} - {win['window_title']}\033[K")
            
            # Move back up after printing each line except the last
            if i < len(matching_windows) - 1:
                print("\033[A", end="")
        
        # Move back to the top of the list
        if len(matching_windows) > 1:
            print(f"\033[{len(matching_windows)-1}A", end="")
    
    # Move cursor down below the list before returning
    print(f"\033[{len(matching_windows)}B")
    selected = matching_windows[selected_index]
    print(f"Selected: {selected['app_name']} - {selected['window_title']}")
    return selected


def find_window_by_title(title_substring, app_name=None, interactive=True):
    """
    Find a window by its title (substring match) and optionally filter by app name.
    
    Args:
        title_substring (str): A substring of the window title to match.
        app_name (str, optional): Application name to filter by. Defaults to None.
        interactive (bool, optional): Whether to use interactive selection when multiple matches are found. Defaults to True.
        
    Returns:
        dict: Window information if found, None otherwise.
    """
    windows = get_window_list()
    matching_windows = []
    
    for window in windows:
        title_match = 'window_title' in window and title_substring.lower() in window['window_title'].lower()
        app_match = app_name is None or ('app_name' in window and app_name.lower() in window['app_name'].lower())
        
        if title_match and app_match:
            matching_windows.append(window)
    
    if not matching_windows:
        return None
        
    # If multiple windows match and interactive mode is enabled, use interactive selection
    if len(matching_windows) > 1 and interactive:
        return interactive_window_select(matching_windows)
    elif len(matching_windows) > 1:
        print(f"Found {len(matching_windows)} matching windows:")
        for i, win in enumerate(matching_windows, 1):
            print(f"{i}. {win['app_name']} - {win['window_title']} (PID: {win['pid']})")
        print("Using first match. Use --interactive to select or --app to filter by application name.")
    
    return matching_windows[0]


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


def capture_window_by_title(title_substring, app_name=None, interactive=True):
    """
    Capture a window by its title (substring match).
    
    Args:
        title_substring (str): A substring of the window title to match.
        
    Returns:
        tuple: (PIL.Image, window_info) if successful, (None, None) otherwise.
    """
    try:
        window = find_window_by_title(title_substring, app_name, interactive)
        if not window:
            print(f"Window with title containing '{title_substring}' not found")
            return None, None
        
        print(f"Found window: {window['app_name']} - {window['window_title']} (PID: {window['pid']})")
        
        # Use screencapture command to capture the window
        timestamp = int(time.time())
        temp_file = f"/tmp/screenshot_{timestamp}.png"
        
        # First try capturing by window ID
        try:
            # Instead of trying to capture the specific window directly, which has issues,
            # we'll use a different approach: capture the full screen and then
            # use AppleScript to get the window bounds and crop the image
            
            # First, capture the entire screen
            subprocess.run(["screencapture", "-x", temp_file], check=True)
            img_full = Image.open(temp_file)
            
            # Get window bounds using AppleScript with improved method for getting entire window
            # No window activation to avoid disturbing user workflow
            bounds_script = f'''
            tell application "System Events"
                set appProc to first process whose name is "{window['app_name']}"
                set appWin to missing value
                repeat with w in (windows of appProc)
                    if name of w contains "{window['window_title']}" then
                        set appWin to w
                        exit repeat
                    end if
                end repeat
                if appWin is not missing value then
                    set b to bounds of appWin
                    return (item 1 of b) & "," & (item 2 of b) & "," & (item 3 of b) & "," & (item 4 of b)
                end if
            end tell
            '''
            
            try:
                bounds_result = subprocess.run(["osascript", "-e", bounds_script], capture_output=True, text=True, check=True)
                bounds_text = bounds_result.stdout.strip()
                
                if bounds_text:
                    # Parse bounds and crop the full screenshot
                    bounds = [int(x) for x in bounds_text.replace(",", " ").split()]
                    if len(bounds) == 4:
                        # With AppleScript bounds, we get [left, top, right, bottom]
                        # We need to crop with: (left, top, right, bottom)
                        left, top, right, bottom = bounds
                        img = img_full.crop((left, top, right, bottom))
                        img.save(temp_file)
                    else:
                        # Use full screenshot if bounds parsing failed
                        print("Could not parse window bounds, using full screenshot")
                        img = img_full
                else:
                    # Use full screenshot if no bounds were returned
                    print("No window bounds returned, using full screenshot")
                    img = img_full
            except Exception as e:
                print(f"Error getting window bounds: {e}, using full screenshot")
                img = img_full
                
            # Open the image with PIL
            img = Image.open(temp_file)
            
            # Remove the temporary file
            os.remove(temp_file)
            
            return img, window
        except Exception as e:
            print(f"Warning: Could not capture by window ID: {e}")
            # Fall back to full screen capture
            return img_full, window
            
    except Exception as e:
        print(f"Error capturing window: {e}")
        return None, None


def save_screenshot(image, window_info=None, output_dir="screenshots"):
    """
    Save a screenshot to disk with the current timestamp.
    
    Args:
        image (PIL.Image): The image to save.
        window_info (dict, optional): Window information. Defaults to None.
        output_dir (str, optional): Output directory. Defaults to "screenshots".
        
    Returns:
        str: Path to the saved image if successful, None otherwise.
    """
    if image is None:
        print("No image to save")
        return None
    
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate a timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add window title if available
        if window_info and 'window_title' in window_info:
            # Sanitize the window title for use in a filename
            title = window_info['window_title'].replace('/', '_').replace('\\', '_')
            title = ''.join(c for c in title if c.isalnum() or c in '_ -')
            filename = f"{timestamp}_{title}.png"
        else:
            filename = f"{timestamp}_screenshot.png"
        
        # Save the image
        output_path = os.path.join(output_dir, filename)
        image.save(output_path)
        
        # Only print the full path for individual screenshots, not for continuous mode
        # to avoid flooding the console
        if "continuous_screenshot" not in sys._getframe().f_back.f_code.co_name:
            print(f"Screenshot saved to {output_path}")
        
        return output_path
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return None


def take_screenshot_of_window(title_substring, output_dir="screenshots", app_name=None, interactive=True):
    """
    Take a screenshot of a window by its title and save it to disk.
    
    Args:
        title_substring (str): A substring of the window title to match.
        output_dir (str, optional): Output directory. Defaults to "screenshots".
        app_name (str, optional): Application name to filter by. Defaults to None.
        
    Returns:
        str: Path to the saved image if successful, None otherwise.
    """
    img, window_info = capture_window_by_title(title_substring, app_name, interactive)
    if img:
        return save_screenshot(img, window_info, output_dir)
    else:
        print(f"Failed to capture screenshot of window with title '{title_substring}'")
        return None


def take_full_screenshot(output_dir="screenshots"):
    """
    Take a screenshot of the entire screen and save it to disk.
    
    Args:
        output_dir (str, optional): Output directory. Defaults to "screenshots".
        
    Returns:
        str: Path to the saved image if successful, None otherwise.
    """
    img = capture_screen()
    if img:
        return save_screenshot(img, None, output_dir)
    else:
        print("Failed to capture full screenshot")
        return None


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


def analyze_image_for_text(image_path, object_description=None, initialize_if_needed=True):
    """
    Analyze an image using Google Gemini to find a specific object.
    
    Args:
        image_path (str): Path to the image file.
        object_description (str, optional): Description of the object to find (e.g., "Zoom icon", "thumbs up button").
            If None, defaults to looking for "Done" text.
        initialize_if_needed (bool, optional): Whether to initialize Gemini if needed. Defaults to True.
        
    Returns:
        tuple: (bool, str) - (Whether the object was detected, Full analysis response)
    """
    
    # Special case for Cascade monitoring
    if object_description == "cascade_state":
        return analyze_cascade_state(image_path, initialize_if_needed)
        
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
            
            # Build the standardized prompt
            if object_description is None:
                object_description = "the word 'Done'"
                
            standardized_prompt = (
                f"Analyze this screenshot and tell me if {object_description} is visible. "
                f"Look carefully at the entire image. "
                f"IMPORTANT: Reply with ONLY 'Yes' if you find it or 'No' if you don't find it. "
                f"No other text in your response."
            )
            
            # Get response from Gemini with timing
            start_time = time.time()
            response = model.generate_content([standardized_prompt, img])
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Gemini analysis took {elapsed_time:.2f} seconds")
            
            response_text = response.text.strip()
            
            # Exact matching for Yes/No
            found = response_text.lower() == "yes"
            
            return found, response_text
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return False, f"Error: {str(e)}"


def analyze_cascade_state(image_path, initialize_if_needed=True, verbose=False):
    """
    Specialized function to analyze the state of Cascade AI assistant in a screenshot.
    
    Args:
        image_path (str): Path to the image file.
        initialize_if_needed (bool, optional): Whether to initialize Gemini if needed. Defaults to True.
        
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
            
            # Build the specialized Cascade monitoring prompt
            cascade_prompt = (
                "You are analyzing a screenshot of the Cascade AI coding assistant interface. You only care about the right panel that says 'Cascade | Write Mode'. IGNORE ALL THE REST OF THE SCREENSHOT. " 
                "Determine the Cascade's current state based on visual cues in the right pane of the image. "
                "Return the following state for the following scenarios: "
                "'user_input_required' if there is an accept and reject button or 'waiting on response' text in the right handside pane"
                "'done' if there is a thumbs-up or thumbs-down icon in the right handside pane"
                "'still_working' for all other cases"
                "IMPORTANT: Respond with a JSON object containing exactly these two keys: "
                "- 'cascade_state': must be EXACTLY ONE of these values: 'user_input_required', 'still_working', or 'done' "
                "- 'reasoning': a brief explanation for your decision "
                "Example response format: "
                "```json "
                "{ "
                "  \"cascade_state\": \"done\", "
                "  \"reasoning\": \"I can see a thumbs-up/thumbs-down icons in the right panel\" "
                "} "
                "``` "
                "Only analyze the right panel and provide nothing but valid JSON in your response."
            )
            
            # Get response from Gemini with timing
            start_time = time.time()
            response = model.generate_content([cascade_prompt, img])
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
                
                # Parse the JSON
                gemini_response = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                # Create a default response
                gemini_response = {"cascade_state": "still_working", "reasoning": "Failed to parse response"}
            # Extract the cascade state from JSON response
            state = gemini_response["cascade_state"].lower()
            
            # Determine actions based on state
            user_action_needed = state == "user_input_required"
            done = state == "done"
            
            # Validate response matches expected format
            if state not in ["user_input_required", "still_working", "done"]:
                print(f"Warning: Unexpected state from Gemini: {state}")
                state = "still_working"  # Default to still working if response is unclear
                
            return user_action_needed or done, state
            
    except Exception as e:
        print(f"Error analyzing Cascade state: {e}")
        return False, f"Error: {str(e)}"


def monitor_cascade_state(interval=4.0, output_dir="screenshots", prefix="cascade_"):
    """
    Continuously monitor the state of Cascade AI assistant and notify when user input is required or when done.
    
    Args:
        interval (float, optional): Default check interval in seconds. Defaults to 4.0.
        output_dir (str, optional): Output directory for screenshots. Defaults to "screenshots".
        prefix (str, optional): Prefix for screenshot filenames. Defaults to "cascade_".
    """
    try:
        # Initialize Gemini API
        gemini_initialized = initialize_gemini_client()
        if not gemini_initialized:
            print("⚠️ Could not initialize Gemini API. Cannot monitor Cascade state.")
            return
            
        print("🔍 Starting Cascade state monitoring...")
        print("   - Will notify when Cascade needs your input or is done")
        print("   - Press Ctrl+C to stop monitoring")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        screenshot_count = 0
        notification_count = 0
        last_state = None
        
        while True:
            try:
                # Take a screenshot
                screenshot_count += 1
                image = capture_screen()
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{prefix}{timestamp}_screenshot.png"
                path = os.path.join(output_dir, filename)
                
                # Save the screenshot
                image.save(path)
                print(f"\rChecking Cascade state ({screenshot_count})...", end="")
                
                # Analyze the screenshot to determine Cascade state
                _, state = analyze_cascade_state(path, False)  # No need to reinitialize
                
                if state != last_state:
                    print(f"\nCascade state: {state}")
                    last_state = state
                
                if state == "user_input_required":
                    # User input is required - play sound and wait longer
                    notification_count += 1
                    print(f"\n🔔 ATTENTION NEEDED ({notification_count}): Cascade needs your input!")
                    # Use system beep instead of sound file
                    play_beep(1000, 500)
                    # Now wait longer before checking again
                    time.sleep(20)
                    
                elif state == "done":
                    # Task is complete
                    print("\n✅ Cascade has completed its task!")
                    sound_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_done.mp3")
                    play_sound(sound_file)
                    return  # Exit the monitoring loop
                    
                else:  # still_working
                    # Cascade is still working, continue regular monitoring
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


def continuous_screenshot(title_substring=None, interval=1.0, output_dir="screenshots", prefix="", app_name=None, interactive=True, analyze=False, object_description=None):
    """
    Take continuous screenshots at regular intervals and optionally analyze them.
    
    Args:
        title_substring (str, optional): Window title to capture. If None, captures full screen.
        interval (float, optional): Interval between screenshots in seconds. Defaults to 1.0.
        output_dir (str, optional): Output directory. Defaults to "screenshots".
        prefix (str, optional): Prefix for the filename. Defaults to "".
        app_name (str, optional): Application name to filter by. Defaults to None.
        interactive (bool, optional): Whether to use interactive selection. Defaults to True.
        analyze (bool, optional): Whether to analyze images with Gemini. Defaults to False.
        prompt (str, optional): Custom prompt to send to Gemini. Defaults to None.
    """
    try:
        # Initialize Gemini API if analysis is requested
        if analyze:
            gemini_initialized = initialize_gemini_client()
            if not gemini_initialized:
                print("Warning: Could not initialize Gemini API. Continuing without analysis.")
                analyze = False
            else:
                print("Image analysis enabled with Gemini API")
        
        print(f"Taking continuous screenshots {'of window "' + title_substring + '"' if title_substring else 'of full screen'}")
        print(f"Saving to {output_dir} with prefix {prefix if prefix else '(none)'}")
        print(f"Interval: {interval} seconds")
        print("Press Ctrl+C to stop")
        
        # Create a directory with the prefix if provided
        if prefix:
            output_dir = os.path.join(output_dir, prefix)
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        screenshot_count = 0
        saved_count = 0
        found_count = 0
        
        while True:
            try:
                screenshot_count += 1
                path = None
                
                if title_substring:
                    # Only use interactive mode for the first screenshot in continuous mode
                    if screenshot_count == 1:
                        path = take_screenshot_of_window(title_substring, output_dir, app_name, interactive)
                    else:
                        path = take_screenshot_of_window(title_substring, output_dir, app_name, False)
                else:
                    path = take_full_screenshot(output_dir)
                    
                if path:
                    saved_count += 1
                    
                    # Analyze the screenshot with Gemini if requested
                    if analyze and path:
                        print(f"\rAnalyzing screenshot {screenshot_count}...", end="")
                        found, analysis = analyze_image_for_text(path, args.object, False)  # No need to reinitialize
                        if found:
                            found_count += 1
                            print(f"\r✅ Detection successful in screenshot {screenshot_count}!{' '*20}")
                            print(f"Analysis: {analysis[:150]}..." if len(analysis) > 150 else f"Analysis: {analysis}")
                            # Play the hardcoded sound file when detection is successful
                            sound_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "warcraft_peon.mp3")
                            play_sound(sound_file)
                        else:
                            print(f"\r❌ No detection in screenshot {screenshot_count}{' '*20}")
                    else:
                        print(f"\rScreenshots taken: {screenshot_count}, Saved: {saved_count}", end="")
                        
                time.sleep(interval)
            except Exception as e:
                print(f"\nError taking screenshot: {e}")
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"\n\nScreenshot capture stopped.")
        print(f"Total screenshots taken: {screenshot_count}, Saved: {saved_count}")
        if analyze:
            print(f"Times '{text_to_find}' was found: {found_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Take screenshots of windows by title")
    parser.add_argument("--title", help="Title substring of the window to capture")
    parser.add_argument("--app", help="Application name to filter windows with the same title")
    parser.add_argument("--list", action="store_true", help="List all windows")
    parser.add_argument("--output-dir", default="screenshots", help="Output directory")
    parser.add_argument("--continuous", action="store_true", help="Take continuous screenshots every second")
    parser.add_argument("--once", action="store_true", help="Take a single screenshot, analyze it, and exit")
    parser.add_argument("--monitor-cascade", action="store_true", help="Monitor Cascade AI assistant state and notify when input is needed")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval between screenshots in seconds (for continuous mode)")
    parser.add_argument("--prefix", default="", help="Prefix for the filename (for continuous mode)")
    parser.add_argument("--interactive", action="store_true", help="Interactively select window when multiple matches are found")
    parser.add_argument("--non-interactive", action="store_true", help="Never use interactive selection, always use first match")
    parser.add_argument("--analyze", action="store_true", help="Analyze screenshots using Google Gemini")
    parser.add_argument("--object", help="Description of the object to find in screenshots (e.g., 'Zoom icon', 'thumbs up button')")
    parser.add_argument("--sound-file", help="Path to sound file to play when detection is successful")
    parser.add_argument("--test-gemini", action="store_true", help="Test connection to Google Gemini API")
    
    args = parser.parse_args()
    
    if args.monitor_cascade:
        monitor_cascade_state(args.interval, args.output_dir, args.prefix)
    elif args.list:
        windows = get_window_list()
        print("Available windows:")
        for i, window in enumerate(windows):
            if 'app_name' in window and 'window_title' in window:
                print(f"{i+1}. {window['app_name']} - {window['window_title']}")
    elif args.test_gemini:
        initialized = initialize_gemini_client()
        if initialized:
            print("✅ Successfully connected to Google Gemini API")
            # Test with a simple request
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Hello, what version of Gemini are you?")
                print(f"\nTest response: {response.text[:200]}" + ("..." if len(response.text) > 200 else ""))
            except Exception as e:
                print(f"Error in test request: {e}")
        else:
            print("❌ Failed to connect to Google Gemini API")
            print("Please make sure you have set the GOOGLE_API_KEY environment variable.")
            print("You can create a .env file with the line: GOOGLE_API_KEY=your_api_key_here")
    elif args.once:
        interactive = not args.non_interactive
        if args.title:
            path = take_screenshot_of_window(args.title, args.output_dir, args.app, interactive)
        else:
            path = take_full_screenshot(args.output_dir)
            
        if path and args.analyze:
            print(f"Analyzing screenshot...")
            found, analysis = analyze_image_for_text(path, args.object)
            if found:
                print(f"✅ Detection successful!")
                print(f"Analysis: {analysis[:150]}..." if len(analysis) > 150 else f"Analysis: {analysis}")
                # Play the hardcoded sound file when detection is successful
                sound_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "warcraft_peon.mp3")
                play_sound(sound_file)
            else:
                print(f"❌ No detection in screenshot")
                
    elif args.continuous:
        interactive = not args.non_interactive
        continuous_screenshot(
            args.title, 
            args.interval, 
            args.output_dir, 
            args.prefix, 
            args.app, 
            interactive,
            args.analyze, 
            args.object
        )
    elif args.title:
        interactive = args.interactive or not args.non_interactive
        take_screenshot_of_window(args.title, args.output_dir, args.app, interactive)
    else:
        take_full_screenshot(args.output_dir)
