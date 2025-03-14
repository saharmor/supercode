# SuperSurf

SuperSurf is a simple macOS menu bar application that provides voice command functionality using the SpeechRecognition library. It allows you to speak commands starting with the word "surf" and displays notifications for recognized commands.

## Features

- **Simple Menu Bar Interface**: Toggle between Start/Stop Listening with a single click
- **Flexible Speech Recognition**: Choose between Google's free service or OpenAI's Whisper API
- **Notification Feedback**: Displays macOS notifications for recognized commands
- **Low Resource Usage**: Runs efficiently in the background

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/supersurf.git
cd supersurf
```

2. Install the required dependencies:
```bash
chmod +x install_supersurf.sh
./install_supersurf.sh
```

## Usage

1. Configure your preferred speech recognition service (optional):
   - Copy `.example.env` to `.env`
   - Edit `.env` to set your preferences:
     - Set `USE_OPENAI_API=true` to use OpenAI's Whisper API (more accurate)
     - Add your OpenAI API key if using Whisper API
     - Or keep `USE_OPENAI_API=false` to use Google's free service

2. Run the application:
```bash
./run_supersurf.sh
```

3. Click on the "SuperSurf" icon in the menu bar
4. Select "Start Listening" to begin voice recognition
5. Speak commands starting with "activate" (e.g., "activate hello world")
6. The app will display notifications for recognized commands
7. Select "Stop Listening" when you're done

## Requirements

- macOS (tested on macOS 10.15+)
- Python 3.7+
- Working microphone
- Internet connection (for speech recognition services)
- OpenAI API key (optional, only if using the Whisper API)

## Dependencies

- rumps: For creating the macOS menu bar application
- pyaudio: For audio capture
- SpeechRecognition: For speech-to-text conversion
- python-dotenv: For environment variable management
- numpy: For audio processing
- webrtcvad: For voice activity detection

## License

This project is licensed under the terms of the license included in the repository.

## Acknowledgments

This application is based on the whisper_streaming.py script and adapted to run as a macOS menu bar application.
