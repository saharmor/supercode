import rumps

def show_commands_help():
    """Show a help dialog with all available commands and usage information"""
    help_text = """
SuperSurf Voice Commands

Basic Commands:
- "Surf type [text]" - Types the specified text (e.g., "Surf type hello world")
- "Surf write [text]" - Alternative to type command
- "Surf save" - Saves the current file (⌘S)
- "Surf undo" - Undoes the last action (⌘Z)
- "Surf redo" - Redoes the last action (⇧⌘Z)
- "Surf copy" - Copies selected text (⌘C)
- "Surf paste" - Pastes from clipboard (⌘V)
- "Surf cut" - Cuts selected text (⌘X)
- "Surf select all" - Selects all text (⌘A)

Navigation Commands:
- "Surf find [text]" - Finds text in document (⌘F)
- "Surf search [text]" - Alternative to find command
- "Surf next" - Goes to next search result (⌘G)
- "Surf previous" - Goes to previous search result (⇧⌘G)
- "Surf go to line [number]" - Goes to specified line
- "Surf top" - Goes to top of document (⌘↑)
- "Surf bottom" - Goes to bottom of document (⌘↓)

For complete documentation, visit:
https://github.com/saharmor/supersurf
"""
    
    rumps.alert(
        title="SuperSurf Commands Help",
        message=help_text,
        ok="Got it!"
    )

def show_basic_commands():
    """Show a help dialog with basic commands"""
    basic_commands = """
SuperSurf Basic Commands

Text Input:
- "Surf type [text]" - Types the specified text
  Example: "Surf type Hello, world!"
- "Surf write [text]" - Alternative to type
  Example: "Surf write This is a test"
- "Surf insert [text]" - Another alternative
  Example: "Surf insert My message here"

Text Editing:
- "Surf save" - Saves the current file (⌘S)
- "Surf undo" - Undoes the last action (⌘Z)
- "Surf redo" - Redoes the last action (⇧⌘Z)

Clipboard Operations:
- "Surf copy" - Copies selected text (⌘C)
- "Surf paste" - Pastes from clipboard (⌘V)
- "Surf cut" - Cuts selected text (⌘X)
- "Surf select all" - Selects all text (⌘A)

Tips:
- Speak clearly and at a moderate pace
- Wait for the "Listening..." indicator before speaking
- The commands are case-insensitive
"""
    
    rumps.alert(
        title="Basic Commands",
        message=basic_commands,
        ok="Got it!"
    )

def show_navigation_commands():
    """Show a help dialog with navigation commands"""
    navigation_commands = """
SuperSurf Navigation Commands

Search:
- "Surf find [text]" - Finds text in document (⌘F)
  Example: "Surf find function"
- "Surf search [text]" - Alternative to find
  Example: "Surf search variable name"
- "Surf look for [text]" - Another alternative
  Example: "Surf look for error message"

Search Navigation:
- "Surf next" - Goes to next search result (⌘G)
- "Surf previous" - Goes to previous search result (⇧⌘G)

Line Navigation:
- "Surf go to line [number]" - Goes to specified line
  Example: "Surf go to line 42"
- "Surf jump to line [number]" - Alternative
  Example: "Surf jump to line 100"

Document Navigation:
- "Surf top" - Goes to top of document (⌘↑)
- "Surf go to top" - Alternative
- "Surf bottom" - Goes to bottom of document (⌘↓)
- "Surf go to bottom" - Alternative

Tips:
- For line numbers, speak the digits clearly
- For long search terms, speak at a moderate pace
- If the search doesn't find what you want, try using more specific terms
"""
    
    rumps.alert(
        title="Navigation Commands",
        message=navigation_commands,
        ok="Got it!"
    )

def show_troubleshooting_guide():
    """Show a troubleshooting guide for common issues"""
    troubleshooting = """
SuperSurf Troubleshooting Guide

Common Issues and Solutions:

1. Commands Not Recognized
   - Speak clearly and at a moderate pace
   - Make sure to start with the keyword "Surf"
   - Check that your microphone is working properly
   - Try using a different microphone

2. Application Crashes
   - Make sure your OpenAI API key is valid
   - Check for sufficient internet connectivity
   - Restart the application
   - Make sure you have the latest version

3. Slow Response Times
   - Consider using a smaller Whisper model (e.g., "tiny" or "base")
   - Ensure you have a stable internet connection
   - Close other applications that might be using the microphone

4. Audio Input Problems
   - Check if the correct microphone is selected
   - Try disconnecting and reconnecting your microphone
   - Make sure no other applications are using the microphone
   - Adjust your microphone settings in System Preferences

5. Command Executes Incorrectly
   - Try using alternative command phrases
   - Speak more slowly and clearly
   - Restart the application

For additional help, please visit:
https://github.com/saharmor/supersurf/issues
"""
    
    rumps.alert(
        title="Troubleshooting Guide",
        message=troubleshooting,
        ok="Got it!"
    )

def show_command_examples():
    """Show examples of common command usages"""
    examples = """
SuperSurf Command Examples

Basic Text Input:
- "Surf type Hello, how are you today?"
- "Surf write function calculateSum(a, b) { return a + b; }"
- "Surf insert const x = 42;"

Multiple Commands in Sequence:
1. "Surf type function test() {"
2. "Surf type console.log('testing');"
3. "Surf type }"

Code Navigation:
1. "Surf find class MyComponent"
2. "Surf next" (to find the next occurrence)
3. "Surf go to line 42"
4. "Surf top" (to go to the beginning of the file)

Editing Workflow:
1. "Surf select all"
2. "Surf copy"
3. "Surf type // New implementation:"
4. "Surf paste"
5. "Surf save"

Advanced Usage:
- Use "Surf find" followed by "Surf next" to navigate through search results
- Use "Surf top" followed by "Surf type" to add code at the beginning
- Combine "Surf select all", "Surf copy", and "Surf paste" for duplicating content

Remember to speak clearly and pause briefly between commands for best results.
"""
    
    rumps.alert(
        title="Command Examples",
        message=examples,
        ok="Got it!"
    )

def show_how_to_use():
    """Show a guide on how to use SuperSurf effectively"""
    how_to_use = """
How to Use SuperSurf Effectively

Getting Started:
1. Click on the SuperSurf icon in the menu bar
2. Select "Start Listening" to activate voice recognition
3. Wait for the "Listening..." indicator
4. Speak your command, starting with the keyword "Surf"
5. Wait for the command to be processed and executed

Best Practices:
- Speak clearly and at a moderate pace
- Pause briefly before and after saying the "Surf" keyword
- For text input, speak at a consistent pace
- For line numbers and specific commands, enunciate clearly
- Check the status indicator in the menu bar for feedback

Optimizing Recognition:
- Use a good quality microphone
- Minimize background noise
- Position the microphone properly
- Speak directly into the microphone
- Test different microphones to find the best one

Command Structure:
- Always begin with "Surf" (e.g., "Surf type hello")
- Follow with the command word (type, find, save, etc.)
- Provide any necessary parameters or text

Stopping Recognition:
- Click on the SuperSurf icon in the menu bar
- Select "Stop Listening" to deactivate voice recognition
- Or use the keyboard shortcut (if configured)

Additional Tips:
- Use the Tutorial for interactive guidance
- Check the Commands menu for reference
- Configure settings based on your needs
- Test your microphone before extended use
"""
    
    rumps.alert(
        title="How to Use SuperSurf",
        message=how_to_use,
        ok="Got it!"
    ) 