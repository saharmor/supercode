# SuperCode Development Guide

## Build/Run Commands
- `./install_supercode.sh` - Install dependencies and create virtual environment
- `./run_supercode.sh` - Run the application
- `source supercode_venv/bin/activate` - Activate virtual environment for development
- `python supercode_app.py` - Run the app directly after activating venv

## Code Style Guidelines
- **Imports**: Group imports by standard library, third-party, and local modules
- **Docstrings**: Use triple quotes for docstrings with clear descriptions of parameters and returns
- **Error Handling**: Use specific exception types with descriptive error messages
- **Naming**: 
  - Classes: PascalCase (e.g., `FastSpeechHandler`)
  - Functions/Methods: snake_case (e.g., `execute_command`)
  - Variables: snake_case (e.g., `command_processor`)
- **Line Length**: Aim for maximum 100 characters per line
- **Environment Variables**: Load via dotenv, provide sensible defaults
- **Threading**: Always mark daemon=True for background threads

## Project Architecture
SuperCode is a macOS menu bar app for voice commands with three main components:
1. Audio capture with low-latency streaming
2. Speech recognition (Google or OpenAI Whisper)
3. Command processing when activation word is heard