import os
import base64
import io
import pyautogui
from enum import Enum
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Define scaling source enum similar to computer.py
class ScalingSource(Enum):
    API = 1      # Coordinates from API (need to be scaled to real screen)
    SCREEN = 2   # Coordinates from screen (need to be scaled to API format)


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
        # Capture screenshot using PyAutoGUI - no region parameter to capture entire screen
        screenshot = pyautogui.screenshot()
        
        # Resize to target dimensions
        screenshot = screenshot.resize((self.target_width, self.target_height))
        
        # Save to in-memory buffer
        img_buffer = io.BytesIO()
        screenshot.save(img_buffer, format="PNG", optimize=True)
        img_buffer.seek(0)
        
        # Return base64 encoded image
        return base64.b64encode(img_buffer.read()).decode()
    
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
            print(f"Claude's response: {text_response}")
            
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
