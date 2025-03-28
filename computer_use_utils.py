import os
import base64
import io
import time
import pyautogui
import platform
import subprocess
from enum import Enum
from typing import Optional, Tuple
from dotenv import load_dotenv
from PIL import Image
from screeninfo import get_monitors

load_dotenv()

# Define scaling source enum similar to computer.py
class ScalingSource(Enum):
    API = 1      # Coordinates from API (need to be scaled to real screen)
    SCREEN = 2   # Coordinates from screen (need to be scaled to API format)


def capture_screenshot(monitor=None, resize_width=None, return_base64=False, temp_file=None):
    """
    Unified screenshot capture function for all use cases.
    
    Args:
        monitor (str, optional): The monitor to capture the screenshot from.
        resize_width (int, optional): Width to resize the image to. Height will be proportionally scaled.
        return_base64 (bool, optional): Whether to return a base64 string instead of a PIL Image.
        temp_file (str, optional): Path to save a temporary file. If None, will use in-memory processing.
    Returns:
        Union[Image.Image, str]: Either a PIL Image object or a base64-encoded string.
    """
    try:
        # Always try to use screencapture on macOS if possible
        use_screencapture = platform.system() == "Darwin"
        
        if use_screencapture:
            # Create temp file if not provided
            if temp_file is None:
                temp_file = os.path.join(os.getcwd(), f"temp_screenshot_{int(time.time())}.png")
                should_cleanup = True
            else:
                should_cleanup = False
                
            # Determine capture region
            region_args = []
            if monitor == 'current':
                m = get_active_window_monitor()
                region_args = ["-R", f"{m['left']},{m['top']},{m['width']},{m['height']}"]
            elif isinstance(monitor, dict):
                region_args = ["-R", f"{monitor['left']},{monitor['top']},{monitor['width']},{monitor['height']}"]
                
            # Capture screenshot
            subprocess.run(["screencapture", "-x"] + region_args + [temp_file], check=True)
            screenshot = Image.open(temp_file)
            
            # Clean up temp file if we created it
            if should_cleanup or return_base64:
                os.remove(temp_file)
        else:
            # Fall back to pyautogui on other platforms
            region = None
            if monitor == 'current':
                m = get_active_window_monitor()
                region = (m['left'], m['top'], m['width'], m['height'])
            elif isinstance(monitor, dict):
                region = (monitor['left'], monitor['top'], monitor['width'], monitor['height'])
            
            screenshot = pyautogui.screenshot(region=region)

        # Resize
        if resize_width:
            ratio = screenshot.height / screenshot.width
            resize_height = int(resize_width * ratio)
            screenshot = screenshot.resize((resize_width, resize_height))

        if return_base64:
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG", optimize=True)
            return base64.b64encode(buffer.getvalue()).decode()
        else:
            return screenshot
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None
    

class ClaudeComputerUse:
    """Simple class to interact with Claude Computer Use for getting coordinates"""
    
    def __init__(self):
        # Get the actual screen dimensions
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Set target dimensions (what Claude expects)
        self.target_width = 1280  # Claude's max screenshot width
        self.target_height = int(self.screen_height * (self.target_width / self.screen_width))
    
    def scale_coordinates(self, source: ScalingSource, x: int, y: int) -> Tuple[int, int]:
        """Scale coordinates between Claude's coordinate system and real screen coordinates"""
        x_scaling_factor = self.screen_width / self.target_width
        y_scaling_factor = self.screen_height / self.target_height
        
        if source == ScalingSource.API:
            # Claude's coordinates -> real screen coordinates
            return round(x * x_scaling_factor), round(y * y_scaling_factor)
        else:
            # Real screen coordinates -> Claude's coordinate system
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
    
    def take_screenshot(self, monitor=None) -> str:
        """
        Take a screenshot for Claude Computer Use.
        Returns a base64-encoded string of the image resized to target dimensions.
        """
        return capture_screenshot(monitor=monitor, resize_width=self.target_width, return_base64=True)
    
    async def get_coordinates_from_claude(self, prompt: str, monitor=None) -> Optional[Tuple[int, int]]:
        """Get coordinates from Claude based on a natural language prompt"""
        try:
            from anthropic import Anthropic
            
            # Get API key from environment
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                print("Error: ANTHROPIC_API_KEY not found in environment variables")
                return None
            
            # Initialize Anthropic client
            client = Anthropic(api_key=api_key)
            
            # Take a screenshot
            base64_image = self.take_screenshot(monitor=monitor)
            
            # Create the message with the screenshot and prompt
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                system="You are an expert at identifying UI elements in screenshots. When given a screenshot and a description of an element to find, respond ONLY with the X,Y coordinates of where to click to interact with that element. Format your response as 'X=<number>,Y=<number>' and nothing else.",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": f"Find the {prompt}. Respond ONLY with the X,Y coordinates where to click."
                            }
                        ]
                    }
                ]
            )
            
            # Extract coordinates from Claude's response
            text_response = response.content[0].text
            
            # Parse X,Y coordinates from response
            if "X=" in text_response and "Y=" in text_response:
                # Extract X and Y values
                x_part = text_response.split("X=")[1].split(",")[0]
                y_part = text_response.split("Y=")[1].split(")")[0] if ")" in text_response else text_response.split("Y=")[1]
                
                try:
                    x = int(x_part.strip())
                    y = int(y_part.strip())
                    return (x, y)
                except ValueError:
                    print(f"Error parsing coordinates from: {text_response}")
                    return None
            else:
                print(f"Could not find X,Y coordinates in response: {text_response}")
                return None
                
        except Exception as e:
            print(f"Error getting coordinates from Claude: {str(e)}")
            return None


def get_coordinates_for_prompt(prompt: str, monitor) -> Optional[Tuple[int, int]]:
    import asyncio
    
    claude = ClaudeComputerUse()
    
    # Run the async function in a new event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        coordinates = loop.run_until_complete(claude.get_coordinates_from_claude(prompt, monitor=monitor))
        loop.close()
    except Exception as e:
        print(f"Error running async function: {str(e)}")
        return None
    
    if coordinates:
        api_x, api_y = coordinates
        print(f"Claude coordinates: ({api_x}, {api_y})")
        
        # Scale the coordinates to match the actual screen dimensions
        scaled_x, scaled_y = claude.scale_coordinates(ScalingSource.API, api_x, api_y)        
        return scaled_x, scaled_y
    else:
        print("Failed to get coordinates from Claude")
        return None


def get_windsurf_project_window_name(project_contained_name: str):
    # Windsurf runs as an Electron app, so we need to check the window names
    script = '''
        tell application "System Events"
            tell process "Electron"
                set theWindowNames to name of every window
            end tell
        end tell
        return theWindowNames
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
    window_names = result.stdout.strip().split(",")
    return next((name.strip() for name in window_names if project_contained_name in name), None)


def get_ide_window_name(app_name: str, window_title: str):
    if app_name == "windsurf":
        return window_title.split(" — ")[0] if " — " in window_title else window_title
    elif app_name == "cursor":
        return window_title.split(" — ")[1] if " — " in window_title else window_title
    else:
        return window_title

def bring_to_front_window(possible_apps_names: list[str], app_name: str, window_title: str):
    """
    Focus the appropriate IDE window based on the current interface.
    
    Returns:
        bool: True if the window was successfully focused, False otherwise
    """
    try:
        app_name = app_name.lower()
        window_name = get_ide_window_name(app_name, window_title)
        
        # Generic fallback for unknown interfaces - try to use the interface name as the app name
        if app_name not in possible_apps_names:
            print(f"No explicit application mapping defined for interface: {app_name}")
            raise ValueError(f"No explicit application mapping defined for interface: {app_name}")

        if platform.system() == "Darwin":
            # If the application is Google Chrome, or if it's Lovable or Bolt,
            # then use Chrome to find the tab with the window_title.
            window_name_for_script = window_name if window_name else app_name

            if app_name in ["lovable", "bolt"]:
                script = f'''
                tell application "Google Chrome"
                    activate
                    set tabFound to false
                    repeat with w in windows
                        set tabCount to count of tabs in w
                        repeat with i from 1 to tabCount
                            if (title of (tab i of w) contains "{window_name_for_script}") then
                                set active tab index of w to i
                                -- Bring the window to the front
                                set index of w to 1
                                set tabFound to true
                                exit repeat
                            end if
                        end repeat
                        if tabFound then exit repeat
                    end repeat
                    return tabFound
                end tell
                '''
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
                tab_found = result.stdout.strip() == "true"
                if tab_found:
                    return True
                else:
                    print(f"Warning: Focused on Google Chrome, but could not find tab with title containing '{window_name}'")
                    return False
            else:
                # windsurf runs as an Electron app, so we need to check the window names
                app_name_for_script = "Electron" if app_name == "windsurf" else app_name.capitalize()
                
                script = f'''
                tell application "System Events"
                    tell process "{app_name_for_script}"
                        set frontmost to true
                        repeat with w in windows
                            if name of w contains "{window_name}" then
                                perform action "AXRaise" of w
                                exit repeat
                            end if
                        end repeat
                    end tell
                end tell
                '''

                subprocess.run(["osascript", "-e", script], check=True)
                return True

        elif platform.system() == "Windows":
            # Windows-specific focusing script would be implemented here
            print("Window focusing not implemented for Windows")
            return False
        else:
            print(f"Window focusing not implemented for {platform.system()}")
            return False
    except Exception as e:
        print(f"Error focusing window: {e}")
        return False


def test_bring_to_front_window():
    # bring_to_front_window(['Cursor', 'Lovable', 'Bolt'], 'Lovable', 'ai-syndicate')
    # time.sleep(2)
    
    # bring_to_front_window(['Cursor', 'Lovable', 'Bolt'], 'Lovable', 'blabla')
    # time.sleep(2)

    bring_to_front_window(['cursor', 'windsurf', 'lovable', 'bolt'], 'Windsurf', 'gemini-multimodal-playground — ai studio api key.png')
    time.sleep(2)
    bring_to_front_window(['cursor', 'windsurf', 'lovable', 'bolt'], 'Windsurf', 'bug_surf')
    time.sleep(2)
    bring_to_front_window(['cursor', 'windsurf', 'lovable', 'bolt'], 'Windsurf', 'gemini-multimodal-playground — ai studio api key.png')
    
    # bring_to_front_window(['cursor', 'windsurf', 'lovable', 'bolt'], 'Cursor', 'bug_hunter.py — simulatedev')
    # time.sleep(2)

    # bring_to_front_window(['cursor', 'windsurf', 'lovable', 'bolt'], 'Windsurf', 'bug_surf')
    # time.sleep(2)
    

def get_current_window_name():
    """Get the name of the currently active window, with robust error handling."""
    script = '''
    try
        tell application "System Events"
            set frontProcess to first process whose frontmost is true
            set processName to name of frontProcess
        end tell

        if processName is "Google Chrome" then
            tell application "Google Chrome"
                if (count of windows) > 0 then
                    return title of active tab of front window
                else
                    return "Google Chrome"
                end if
            end tell
        else
            tell application "System Events"
                if exists front window of frontProcess then
                    return name of front window of frontProcess
                else
                    return processName
                end if
            end tell
        end if
    on error errorMessage
        return "Unknown"
    end try
    '''
    
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"Warning: AppleScript error when getting window name: {result.stderr.strip()}")
            # Return a fallback window name instead of raising an exception
            return "Unknown Window"
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting current window name: {e}")
        return "Unknown Window"


def get_active_window_monitor():
    """
    Get the monitor where the currently active window is displayed.
    
    Returns:
        dict: The monitor's bounding box with keys 'left', 'top', 'width', 'height'.
    """
    try:
        time.sleep(3)
        center_x, center_y = pyautogui.position()

        monitors = get_monitors()
        for m in monitors:
            if (m.x <= center_x <= m.x + m.width and
                m.y <= center_y <= m.y + m.height):
                return {"left": m.x, "top": m.y, "width": m.width, "height": m.height}

        # Fallback: return the first monitor if none match
        primary = monitors[0]
        return {"left": primary.x, "top": primary.y, "width": primary.width, "height": primary.height}

    except Exception as e:
        print(f"Error getting active window monitor: {e}")
        # Default fallback dimensions
        return {"left": 0, "top": 0, "width": 1920, "height": 1080}


def send_screenshot_to_gemini(prompt, monitor=None, temp_file=None, resize_width=1024, model_name='gemini-2.0-flash-lite', verbose=False):
    """
    Take a screenshot, send it to Gemini with a prompt, and return the response.
    Common utility for both IDE detection and state analysis.
    
    Args:
        prompt (str): The prompt to send to Gemini along with the screenshot
        monitor (dict, optional): Monitor region to capture. If None, captures current window.
        temp_file (str, optional): Path to save screenshot temporarily. If None, creates a temp file.
        resize_width (int, optional): Width to resize the screenshot to.
        model_name (str, optional): Gemini model to use.
        verbose (bool, optional): Whether to print detailed logs.
        
    Returns:
        tuple: (bool, response_obj) - Success flag and response object from Gemini
               or (False, error_str) if an error occurred
    """
    try:
        # Import Google Gemini AI library
        import google.generativeai as genai
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # Check for API key
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            error_msg = "Error: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not found."
            print(error_msg)
            return False, error_msg
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create a temp file if none provided
        should_cleanup_temp = False
        if not temp_file:
            temp_file = os.path.join(os.getcwd(), f"temp_gemini_query_{int(time.time())}.png")
            should_cleanup_temp = True
        
        # Capture screenshot
        screenshot = capture_screenshot(monitor=monitor, resize_width=resize_width, temp_file=temp_file)
        if not screenshot:
            error_msg = "Error: Failed to capture screenshot"
            print(error_msg)
            return False, error_msg
        
        try:
            # Get Gemini model
            model = genai.GenerativeModel(model_name)
            
            # Send to Gemini with timing
            start_time = time.time()
            
            # Different handling depending on whether screenshot is a PIL Image or a path
            if isinstance(screenshot, str) or temp_file:  # If temp_file exists or screenshot is a path
                file_path = screenshot if isinstance(screenshot, str) else temp_file
                # Load and prepare the image
                with Image.open(file_path) as img:
                    # Ensure image is in RGB format for compatibility
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    # Generate content with image
                    response = model.generate_content([prompt, img])
            else:  # If screenshot is a PIL Image
                # Ensure image is in RGB format
                if screenshot.mode != "RGB":
                    screenshot = screenshot.convert("RGB")
                # Generate content with image directly
                response = model.generate_content([prompt, screenshot])
            
            # Log timing if verbose
            end_time = time.time()
            elapsed_time = end_time - start_time
            if verbose:
                print(f"Gemini analysis took {elapsed_time:.2f} seconds")
                print(f"Gemini response: {response.text.strip()}")
            
            # Cleanup temp file if we created it
            if should_cleanup_temp and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Warning: Could not remove temp file {temp_file}: {e}")
            
            return True, response
            
        except Exception as e:
            error_msg = f"Error communicating with Gemini: {str(e)}"
            print(error_msg)
            
            # Cleanup temp file if we created it
            if should_cleanup_temp and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Error in send_screenshot_to_gemini: {str(e)}"
        print(error_msg)
        return False, error_msg

def detect_ide_with_gemini(possible_ides: list[str]) -> str:
    """
    Use Gemini to detect which IDE is currently open and in focus.
    
    Args:
        possible_ides: List of possible IDE names to check for
        
    Returns:
        str: The detected IDE name, or None if no matching IDE is detected
    """
    # Prepare the prompt for Gemini
    detection_prompt = """
Help me know what AI IDE is being used based on the given screenshot. It can be one of three options: Cursor, Windsurf, or Lovable. I'll provide you with the visual description of those three and you will return the name. If it's none of these options, you return None.

Visual description:
Cursor Prompt: "This interface looks like VS Code. Does the right panel show an integrated AI chat/diff view with 'Agent', 'Accept all' / 'Reject all' buttons, and does the bottom status bar mention 'Cursor Tab'?"

Windsurf Prompt: "This interface looks like VS Code. Does the right panel feature an AI assistant explicitly named or titled 'Cascade' (e.g., 'Write with Cascade'), and does the bottom status bar mention 'Windsurf'?"

Lovable Prompt: "This interface is a web browser, not a standalone code editor. Does the URL contain 'lovable.dev', and is there a left-hand panel distinctly labeled 'Lovable' (often next to a heart icon) controlling a web page preview on the right?"

Return ONLY the IDE name (Cursor, Windsurf, Lovable) or "None" if no match.
"""
    
    # Use the new common function to get Gemini's response
    success, response = send_screenshot_to_gemini(
        prompt=detection_prompt,
        monitor='current',
        resize_width=1024
    )
    
    if not success:
        print(f"Error in IDE detection: {response}")
        return None
    
    # Extract the response text
    response_text = response.text.strip()
    
    # Process the response
    if response_text.lower() in ['cursor', 'windsurf', 'lovable']:
        detected_ide = response_text.lower()
        print(f"Gemini detected IDE: {detected_ide}")
        
        # Verify the detected IDE is in our list of possible IDEs
        if detected_ide in [ide.lower() for ide in possible_ides]:
            return detected_ide
        else:
            print(f"Detected IDE {detected_ide} is not in the list of possible IDEs: {possible_ides}")
            return None
    else:
        print("No matching IDE detected")
        return None
