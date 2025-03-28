import platform
import subprocess
from openai import OpenAI
from pydantic import BaseModel
from typing import Literal
import os
import glob

def play_beep(frequency, duration):
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.call(["afplay", "/System/Library/Sounds/Ping.aiff"])
    elif system == "Linux":
        subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"])
    elif system == "Windows":
        import winsound
        winsound.Beep(frequency, duration)  # frequency in Hz, duration in milliseconds

def enhance_user_prompt(command_text):
    """
    Enhance a raw user prompt by using GPT-4o Mini to structure it for a coding model.
    
    Args:
        command_text: The raw prompt text to enhance.
        
    Returns:
        str: The enhanced, structured prompt.
    """
    class EnhancedPrompt(BaseModel):
        prompt: str
        requiredIntelligenceLevel: Literal["low", "medium", "high"]

    try:
        client = OpenAI()
        
        system_prompt = """You are a prompt engineering assistant. Your task is to transform raw, unstructured prompts 
        into short prompts specifically designed for coding models and IDEs like Copilot and Windsurf.
        Analyze the complexity of the request and return the transformed prompt optimized for coding models
        along with the required intelligence level based on the complexity of the task.
        
        Use 'low' for simple formatting or basic code generation, 'medium' for standard programming tasks,
        and 'high' for complex algorithms, architecture design, or domain-specific optimizations.
        
        If the prompt doesn't make sense for a coding task, return the prompt as None."""
        
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transform this raw user prompt: {command_text}"}
                ],
                temperature=0.5,
                response_format=EnhancedPrompt,
            )
            
            enhanced_data = completion.choices[0].message.parsed
            return enhanced_data
        except Exception as e:
            print(f"Error parsing structured output: {e}")
            # Fallback to regular response if structured parsing fails
            return {"enhancedPrompt": command_text, "requiredIntelligenceLevel": "medium"}
        
    except Exception as e:
        print(f"Error enhancing prompt: {e}")
        # Return original prompt if enhancement fails
        return command_text

def cleanup_old_files(directory, pattern, max_files=10):
    """
    Maintain a rolling set of files in the given directory, keeping only the newest max_files.
    
    Args:
        directory (str): Directory containing the files
        pattern (str): Glob pattern to match files (e.g., "*.wav", "*.png")
        max_files (int): Maximum number of files to keep (default: 10)
    """
    if not os.path.exists(directory):
        return
        
    # List all matching files with their full paths
    files = glob.glob(os.path.join(directory, pattern))
    
    # Sort files by modification time (newest last)
    files.sort(key=os.path.getmtime)
    
    # Remove oldest files if we have more than max_files
    if len(files) > max_files:
        files_to_remove = files[:-max_files]  # Keep the newest max_files
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing file {file_path}: {e}")

def extract_json_content(response_text):
    # Look for JSON content between triple backticks if present
    if "```json" in response_text and "```" in response_text.split("```json", 1)[1]:
        json_content = response_text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in response_text and "```" in response_text.split("```", 1)[1]:
        json_content = response_text.split("```", 1)[1].split("```", 1)[0].strip()
    else:
        json_content = response_text
    return json_content