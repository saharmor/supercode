from pynput.keyboard import Key, Controller
import time
import re

class SurfController:
    def __init__(self):
        """Initialize the surf controller"""
        self.keyboard = Controller()
        
        # Define command patterns
        self.command_patterns = {
            # Priority 1 - Essential Code Editing
            r'(?i)surf\s+select\s+all': self.select_all,
            r'(?i)surf\s+find\s+(.+)': self.find_text,
            r'(?i)surf\s+save\s+all': self.save_all,
            r'(?i)surf\s+comment': self.toggle_comment,
            r'(?i)surf\s+format': self.format_code,
            
            # Priority 2 - Navigation
            r'(?i)surf\s+top': self.goto_top,
            r'(?i)surf\s+bottom': self.goto_bottom,
            r'(?i)surf\s+next': self.find_next,
            r'(?i)surf\s+previous': self.find_previous,
            r'(?i)surf\s+goto\s+line\s+(\d+)': self.goto_line,
            
            # Priority 3 - IDE Features
            r'(?i)surf\s+terminal': self.toggle_terminal,
            r'(?i)surf\s+explorer': self.toggle_explorer,
            r'(?i)surf\s+problems': self.toggle_problems,
            r'(?i)surf\s+split': self.split_editor,
            
            # Priority 4 - Additional Editing
            r'(?i)surf\s+duplicate': self.duplicate_line,
            r'(?i)surf\s+indent': self.indent_line,
            r'(?i)surf\s+outdent': self.outdent_line,
            r'(?i)surf\s+select\s+line': self.select_line,
            
            # Priority 5 - File Management
            r'(?i)surf\s+new\s+file': self.new_file,
            r'(?i)surf\s+close': self.close_file,
            
            # Existing commands
            r'(?i)surf\s+type\s+(.+)': self.type_text,
            r'(?i)surf\s+enter': self.press_enter,
            r'(?i)surf\s+accept': self.accept_suggestion,
            r'(?i)surf\s+reject': self.reject_suggestion,
            r'(?i)surf\s+tab': self.press_tab,
            r'(?i)surf\s+delete': self.delete_line,
            r'(?i)surf\s+undo': self.undo_action,
            r'(?i)surf\s+save': self.save_file,
            r'(?i)surf\s+hello': self.test_keyboard
        }
    
    def process_command(self, text):
        """
        Process a voice command
        
        Args:
            text (str): Transcribed text command
            
        Returns:
            bool: True if a command was processed, False otherwise
        """
        print(f"Processing command: '{text}'")
        
        for pattern, handler in self.command_patterns.items():
            match = re.match(pattern, text)
            if match:
                print(f"Command matched pattern: {pattern}")
                groups = match.groups()
                if groups:
                    handler(groups[0])
                else:
                    handler()
                return True
                
        print(f"No matching command pattern found for: '{text}'")
        return False
    
    def type_text(self, text):
        """Type the given text"""
        print(f"Typing: '{text}'")
        # Add a small delay to ensure focus
        time.sleep(0.2)
        self.keyboard.type(text)
    
    def press_enter(self):
        """Press the Enter key"""
        print("Pressing Enter")
        time.sleep(0.2)
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
    
    def accept_suggestion(self):
        """Accept suggestion in Windsurf (Tab key)"""
        print("Accepting suggestion")
        time.sleep(0.2)
        self.keyboard.press(Key.tab)
        self.keyboard.release(Key.tab)
    
    def reject_suggestion(self):
        """Reject suggestion in Windsurf (Esc key)"""
        print("Rejecting suggestion")
        time.sleep(0.2)
        self.keyboard.press(Key.esc)
        self.keyboard.release(Key.esc)
    
    def press_tab(self):
        """Press the Tab key"""
        print("Pressing Tab")
        time.sleep(0.2)
        self.keyboard.press(Key.tab)
        self.keyboard.release(Key.tab)
    
    def delete_line(self):
        """Delete the current line (Cmd+Shift+K in Windsurf)"""
        print("Deleting line")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press(Key.shift)
        self.keyboard.press('k')
        self.keyboard.release('k')
        self.keyboard.release(Key.shift)
        self.keyboard.release(Key.cmd)
    
    def undo_action(self):
        """Undo the last action (Cmd+Z in Windsurf)"""
        print("Undoing action")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('z')
        self.keyboard.release('z')
        self.keyboard.release(Key.cmd)
    
    def save_file(self):
        """Save the current file (Cmd+S in Windsurf)"""
        print("Saving file")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('s')
        self.keyboard.release('s')
        self.keyboard.release(Key.cmd)
        
    def test_keyboard(self):
        """Test keyboard functionality with a simple command"""
        print("Running keyboard test")
        time.sleep(0.2)
        self.keyboard.type("Hello from SuperSurf!")
    
    # Priority 1 - Essential Code Editing
    def select_all(self):
        """Select all text (Cmd+A)"""
        print("Selecting all text")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('a')
        self.keyboard.release('a')
        self.keyboard.release(Key.cmd)
    
    def find_text(self, text):
        """Find text (Cmd+F)"""
        print(f"Finding text: '{text}'")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('f')
        self.keyboard.release('f')
        self.keyboard.release(Key.cmd)
        time.sleep(0.2)
        self.keyboard.type(text)
    
    def save_all(self):
        """Save all files (Cmd+Alt+S)"""
        print("Saving all files")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press(Key.alt)
        self.keyboard.press('s')
        self.keyboard.release('s')
        self.keyboard.release(Key.alt)
        self.keyboard.release(Key.cmd)
    
    def toggle_comment(self):
        """Toggle line comment (Cmd+/)"""
        print("Toggling comment")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('/')
        self.keyboard.release('/')
        self.keyboard.release(Key.cmd)
    
    def format_code(self):
        """Format code (Alt+Shift+F)"""
        print("Formatting code")
        time.sleep(0.2)
        self.keyboard.press(Key.alt)
        self.keyboard.press(Key.shift)
        self.keyboard.press('f')
        self.keyboard.release('f')
        self.keyboard.release(Key.shift)
        self.keyboard.release(Key.alt)
    
    # Priority 2 - Navigation
    def goto_top(self):
        """Go to top of file (Cmd+Up)"""
        print("Going to top")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press(Key.up)
        self.keyboard.release(Key.up)
        self.keyboard.release(Key.cmd)
    
    def goto_bottom(self):
        """Go to bottom of file (Cmd+Down)"""
        print("Going to bottom")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press(Key.down)
        self.keyboard.release(Key.down)
        self.keyboard.release(Key.cmd)
    
    def find_next(self):
        """Find next occurrence (Cmd+G)"""
        print("Finding next")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('g')
        self.keyboard.release('g')
        self.keyboard.release(Key.cmd)
    
    def find_previous(self):
        """Find previous occurrence (Cmd+Shift+G)"""
        print("Finding previous")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press(Key.shift)
        self.keyboard.press('g')
        self.keyboard.release('g')
        self.keyboard.release(Key.shift)
        self.keyboard.release(Key.cmd)
    
    def goto_line(self, line_number):
        """Go to specific line (Ctrl+G)"""
        print(f"Going to line {line_number}")
        time.sleep(0.2)
        self.keyboard.press(Key.ctrl)
        self.keyboard.press('g')
        self.keyboard.release('g')
        self.keyboard.release(Key.ctrl)
        time.sleep(0.2)
        self.keyboard.type(line_number)
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
    
    # Priority 3 - IDE Features
    def toggle_terminal(self):
        """Toggle terminal (Ctrl+`)"""
        print("Toggling terminal")
        time.sleep(0.2)
        self.keyboard.press(Key.ctrl)
        self.keyboard.press('`')
        self.keyboard.release('`')
        self.keyboard.release(Key.ctrl)
    
    def toggle_explorer(self):
        """Toggle explorer (Cmd+Shift+E)"""
        print("Toggling explorer")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press(Key.shift)
        self.keyboard.press('e')
        self.keyboard.release('e')
        self.keyboard.release(Key.shift)
        self.keyboard.release(Key.cmd)
    
    def toggle_problems(self):
        """Toggle problems panel (Cmd+Shift+M)"""
        print("Toggling problems panel")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press(Key.shift)
        self.keyboard.press('m')
        self.keyboard.release('m')
        self.keyboard.release(Key.shift)
        self.keyboard.release(Key.cmd)
    
    def split_editor(self):
        """Split editor (Cmd+\\)"""
        print("Splitting editor")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('\\')
        self.keyboard.release('\\')
        self.keyboard.release(Key.cmd)
    
    # Priority 4 - Additional Editing
    def duplicate_line(self):
        """Duplicate line (Shift+Alt+Down)"""
        print("Duplicating line")
        time.sleep(0.2)
        self.keyboard.press(Key.shift)
        self.keyboard.press(Key.alt)
        self.keyboard.press(Key.down)
        self.keyboard.release(Key.down)
        self.keyboard.release(Key.alt)
        self.keyboard.release(Key.shift)
    
    def indent_line(self):
        """Indent line (Tab)"""
        print("Indenting line")
        time.sleep(0.2)
        self.keyboard.press(Key.tab)
        self.keyboard.release(Key.tab)
    
    def outdent_line(self):
        """Outdent line (Shift+Tab)"""
        print("Outdenting line")
        time.sleep(0.2)
        self.keyboard.press(Key.shift)
        self.keyboard.press(Key.tab)
        self.keyboard.release(Key.tab)
        self.keyboard.release(Key.shift)
    
    def select_line(self):
        """Select current line (Cmd+L)"""
        print("Selecting line")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('l')
        self.keyboard.release('l')
        self.keyboard.release(Key.cmd)
    
    # Priority 5 - File Management
    def new_file(self):
        """Create new file (Cmd+N)"""
        print("Creating new file")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('n')
        self.keyboard.release('n')
        self.keyboard.release(Key.cmd)
    
    def close_file(self):
        """Close current file (Cmd+W)"""
        print("Closing file")
        time.sleep(0.2)
        self.keyboard.press(Key.cmd)
        self.keyboard.press('w')
        self.keyboard.release('w')
        self.keyboard.release(Key.cmd)