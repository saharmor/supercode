# SuperSurf

SuperSurf is a simple macOS menu bar application that provides voice command functionality using the SpeechRecognition library. It allows you to speak commands starting with the word "surf" and displays notifications for recognized commands.

## Features

- **Simple Menu Bar Interface**: Toggle between Start/Stop Listening with a single click
- **Voice Command Recognition**: Uses Google's speech recognition service
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

1. Run the application:
```bash
python supersurf_app.py
```

2. Click on the "SuperSurf" icon in the menu bar
3. Select "Start Listening" to begin voice recognition
4. Speak commands starting with "surf" (e.g., "surf hello world")
5. The app will display notifications for recognized commands
6. Select "Stop Listening" when you're done

## Requirements

- macOS (tested on macOS 10.15+)
- Python 3.7+
- Working microphone
- Internet connection (for Google's speech recognition service)

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
