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

load_dotenv()

# Define scaling source enum similar to computer.py
class ScalingSource(Enum):
    API = 1      # Coordinates from API (need to be scaled to real screen)
    SCREEN = 2   # Coordinates from screen (need to be scaled to API format)


def capture_screenshot(resize_width=None, return_base64=False, temp_file=None):
    """
    Unified screenshot capture function for all use cases.
    
    Args:
        resize_width (int, optional): Width to resize the image to. Height will be proportionally scaled.
        return_base64 (bool, optional): Whether to return a base64 string instead of a PIL Image.
        temp_file (str, optional): Path to save a temporary file. If None, will use in-memory processing.
        
    Returns:
        Union[Image.Image, str]: Either a PIL Image object or a base64-encoded string.
    """
    try:
        # Determine whether we should use macOS screencapture or PyAutoGUI
        use_screencapture = platform.system() == "Darwin" and temp_file is not None
        
        # Capture method 1: macOS screencapture (better quality but requires temp file)
        if use_screencapture:
            subprocess.run(["screencapture", "-x", temp_file], check=True)
            screenshot = Image.open(temp_file)
            
            # Clean up temp file if we're not returning the image directly
            if return_base64:
                os.remove(temp_file)
        
        # Capture method 2: PyAutoGUI (cross-platform)
        else:
            screenshot = pyautogui.screenshot()
        
        # Resize if needed
        if resize_width:
            # Calculate target height while maintaining aspect ratio
            ratio = screenshot.height / screenshot.width
            resize_height = int(resize_width * ratio)
            screenshot = screenshot.resize((resize_width, resize_height))
        
        # Return as requested
        if return_base64:
            # Convert to base64
            img_buffer = io.BytesIO()
            screenshot.save(img_buffer, format="PNG", optimize=True)
            img_buffer.seek(0)
            return base64.b64encode(img_buffer.read()).decode()
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
    
    def take_screenshot(self) -> str:
        """
        Take a screenshot for Claude Computer Use.
        Returns a base64-encoded string of the image resized to target dimensions.
        """
        return capture_screenshot(resize_width=self.target_width, return_base64=True)
    
    async def get_coordinates_from_claude(self, prompt: str) -> Optional[Tuple[int, int]]:
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
            base64_image = self.take_screenshot()
            
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


def get_coordinates_for_prompt(prompt: str) -> Optional[Tuple[int, int]]:
    import asyncio
    
    claude = ClaudeComputerUse()
    
    # Run the async function in a new event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        coordinates = loop.run_until_complete(claude.get_coordinates_from_claude(prompt))
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

def bring_to_front_window(possible_apps_names: list[str], app_name: str, window_title: str):
    """
    Focus the appropriate IDE window based on the current interface.
    
    Returns:
        bool: True if the window was successfully focused, False otherwise
    """
    try:
        # Generic fallback for unknown interfaces - try to use the interface name as the app name
        if app_name not in possible_apps_names:
            print(f"No explicit application mapping defined for interface: {app_name}")
            raise ValueError(f"No explicit application mapping defined for interface: {app_name}")

        if platform.system() == "Darwin":
            # If the application is Google Chrome, or if it's Lovable or Bolt,
            # then use Chrome to find the tab with the window_title.
            if app_name in ["Lovable", "Bolt"]:
                script = f'''
                tell application "Google Chrome"
                    activate
                    set tabFound to false
                    repeat with w in windows
                        set tabCount to count of tabs in w
                        repeat with i from 1 to tabCount
                            if (title of (tab i of w) contains "{window_title}") then
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
                    print(f"Focused Google Chrome tab with title containing '{window_title}' for interface '{app_name}'")
                    return True
                else:
                    print(f"Warning: Focused on Google Chrome, but could not find tab with title containing '{window_title}'")
                    return False
            elif app_name in ["Windsurf", "Cursor"]:
                if app_name == "Windsurf":
                    # For Windsurf, find window by title
                    window_name = get_windsurf_project_window_name(window_title)
                    if not window_name:
                        print(f"Warning: Could not find Windsurf window containing '{window_title}'")
                        return False
                elif app_name == "Cursor":
                    window_name = window_title

                script = f'''
                    tell application "{app_name}"
                        activate
                        end tell
                        
                        tell application "System Events"
                            tell process "{app_name}"
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
                print(f"Focused {app_name} window containing '{window_title}'")
                return True
            else:
                script = f'''
                tell application "{app_name}"
                    activate
                end tell

                tell application "System Events"
                    tell process "{app_name}"
                        set frontmost to true
                        repeat with w in windows
                            if name of w contains "{window_title}" then
                                perform action "AXRaise" of w
                                exit repeat
                            end if
                        end repeat
                    end tell
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
                print(f"Focused {app_name} window")
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
    bring_to_front_window(['Cursor', 'Lovable', 'Bolt'], 'Lovable', 'ai-syndicate')
    time.sleep(2)
    
    bring_to_front_window(['Cursor', 'Lovable', 'Bolt'], 'Lovable', 'blabla')
    time.sleep(2)

    bring_to_front_window(['Cursor', 'Windsurf', 'Lovable', 'Bolt'], 'Windsurf', 'gemini')
    time.sleep(2)
    
    bring_to_front_window(['Cursor', 'Windsurf', 'Lovable', 'Bolt'], 'Cursor', 'bug')
    time.sleep(2)