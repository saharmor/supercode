import platform
import subprocess
from openai import OpenAI

def play_beep(frequency, duration):
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.call(["afplay", "/System/Library/Sounds/Ping.aiff"])
    elif system == "Linux":
        subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"])
    elif system == "Windows":
        import winsound
        winsound.Beep(frequency, duration)  # frequency in Hz, duration in milliseconds

def enhance_user_prompt(self, command_text):
    """
    Enhance a raw user prompt by using GPT-4o Mini to structure it for a coding model.
    
    Args:
        command_text: The raw prompt text to enhance.
        
    Returns:
        str: The enhanced, structured prompt.
    """
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