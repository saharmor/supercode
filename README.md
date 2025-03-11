# SuperSurf

SuperSurf is a voice control application that enables hands-free operation of the Windsurf IDE and other macOS applications, making coding more efficient and accessible. Using advanced voice recognition technology, it allows developers to execute commands, navigate code, and perform editing operations through voice commands.

## Recent Improvements

SuperSurf has undergone significant enhancements to improve reliability, user experience, and command recognition:

### Reliability Improvements
- Enhanced error handling with detailed error reporting and recovery
- Improved transcription stability with automatic retry mechanisms
- Automatic restart of audio system after consecutive errors
- Proper resource cleanup to prevent memory leaks
- Maximum restart attempt limits to prevent infinite error loops
- Graceful degradation when services are unavailable

### User Interface Enhancements
- Redesigned menu structure with intuitive categorization
- Enhanced status indicators in the menu bar
- Improved visual feedback for command execution
- Separate menus for commands, settings, tools, and help
- Real-time command success/error statistics
- Cleaner menu bar display without distracting emojis

### Command Recognition Improvements
- Support for natural language variations in commands
- Multiple command patterns for the same action
- Improved string similarity detection for the "surfer" keyword
- More flexible parameter extraction from commands
- Better handling of partial or incomplete commands
- Enhanced normalization of voice input

### Documentation and Help
- Comprehensive troubleshooting guide
- Detailed command examples with practical use cases
- Interactive tutorial for new users
- Better organized help menus with categorized commands
- How-to guides for common tasks and workflows

### Performance Optimizations
- Transcription performance monitoring and statistics
- Circular buffer for continuous listening
- Optimized audio preprocessing pipeline
- Configuration options for performance tuning
- Support for different Whisper model sizes (tiny to large)

## Features

### Voice Command Categories

#### Basic Editing Commands
- Type text (`"Surfer type [text]"` or `"Surfer write [text]"`) - Types the specified text
- Save file (`"Surfer save"`) - Saves the current file (⌘S)
- Undo action (`"Surfer undo"`) - Undoes the last action (⌘Z)
- Redo action (`"Surfer redo"`) - Redoes the last undone action (⇧⌘Z)
- Copy text (`"Surfer copy"`) - Copies selected text (⌘C)
- Paste text (`"Surfer paste"`) - Pastes from clipboard (⌘V)
- Cut text (`"Surfer cut"`) - Cuts selected text (⌘X)
- Select all (`"Surfer select all"`) - Selects all text (⌘A)

#### Navigation Commands
- Find text (`"Surfer find [text]"` or `"Surfer search [text]"`) - Finds text in document (⌘F)
- Next result (`"Surfer next"`) - Goes to next search result (⌘G)
- Previous result (`"Surfer previous"`) - Goes to previous search result (⇧⌘G)
- Go to line (`"Surfer go to line [number]"`) - Goes to specified line
- Go to top (`"Surfer top"` or `"Surfer go to top"`) - Goes to top of document (⌘↑)
- Go to bottom (`"Surfer bottom"` or `"Surfer go to bottom"`) - Goes to bottom of document (⌘↓)

### Tools and Utilities
- Microphone testing
- Keyboard functionality testing
- Speech translation
- Performance monitoring
- Audio device selection
- Model configuration

## System Requirements

- macOS 10.9 or later
- Python 3.9 or later
- Windsurf IDE or other text editor
- Working microphone
- Internet connection (for OpenAI API access)
- OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pedroarrudaa/SuperSurf.git
   cd SuperSurf
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv supersurf_env
   source supersurf_env/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your OpenAI API key:
   ```bash
   echo "OPENAI_API_KEY=your_key_here" > .env
   ```

5. Run the application:
   ```bash
   python run_enhanced.py
   ```

## Dependencies

- `openai`: OpenAI API client for Whisper transcription
- `pyaudio`: Audio capture and device management
- `pynput`: Keyboard control for command execution
- `rumps`: macOS menu bar application framework
- `python-dotenv`: Environment variable management
- `numpy`: Numerical operations for audio processing
- `pydub`: Audio processing utilities

## Usage

1. Click the SuperSurf icon in the menu bar
2. Select "Start Listening" to begin voice control
3. Speak commands prefixed with "Surf"
4. Monitor command status in the menu bar
5. Use the Help menu for command references

### Example Commands
```
"Surf type hello world"     # Types "hello world"
"Surf find example"         # Searches for "example"
"Surf save"                 # Saves current file
"Surf go to line 42"        # Goes to line 42
"Surf select all"           # Selects all text
"Surf copy"                 # Copies selected text
"Surf paste"                # Pastes from clipboard
```

## Configuration

SuperSurf offers several configuration options:

### Audio Settings
- Microphone selection
- Audio input level adjustments
- Recording parameters

### API Configuration
- OpenAI API key management
- Model selection (tiny, base, small, medium, large)
- Language settings

### Performance Settings
- Recognition timeout configuration
- Auto-restart settings
- Error handling preferences

## Troubleshooting

### Common Issues

1. **Command Not Recognized**
   - Speak clearly and at a moderate pace
   - Ensure "Surf" prefix is clearly pronounced
   - Check microphone input levels
   - Try alternative command variations

2. **Audio Input Issues**
   - Verify microphone permissions
   - Check system audio input settings
   - Ensure correct input device is selected
   - Try disconnecting and reconnecting your microphone

3. **Application Crashes**
   - Make sure your OpenAI API key is valid
   - Check for sufficient internet connectivity
   - Restart the application
   - Ensure you have the latest version

4. **Slow Response Times**
   - Consider using a smaller Whisper model
   - Check your internet connection speed
   - Close other applications using the microphone
   - Adjust the recognition timeout setting

## Contributing

Contributions are welcome! Please feel free to submit pull requests or create issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Future Development Plans

### Enhanced Command Recognition
- Machine learning-based command recognition
- Custom command creation and mapping
- Context-aware commands for different applications
- Command chaining for complex operations

### Expanded Application Support
- Specialized command sets for popular applications
- Application-specific shortcuts and functions
- Automatic detection of active application

### Accessibility Improvements
- Support for additional languages
- Voice profile training for better recognition
- Features for users with motor disabilities
- Alternative activation methods

### Performance Optimizations
- Local speech recognition for offline operation
- Buffered audio processing for faster responses
- Optimized resource usage
- Reduced latency between command and execution
