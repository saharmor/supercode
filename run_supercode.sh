#!/bin/bash
# Convenience script to run SuperCode

# Function to display a colored message
print_message() {
  local color=$1
  local message=$2
  
  case $color in
    "green") echo -e "\033[0;32m$message\033[0m" ;;
    "yellow") echo -e "\033[0;33m$message\033[0m" ;;
    "red") echo -e "\033[0;31m$message\033[0m" ;;
    "blue") echo -e "\033[0;34m$message\033[0m" ;;
    *) echo "$message" ;;
  esac
}

# Check if virtual environment exists
VENV_DIR="supercode_env"
if [ ! -d "$VENV_DIR" ]; then
    print_message "red" "Error: Virtual environment not found at $VENV_DIR"
    print_message "yellow" "Please run ./install_and_run.sh first to set up the environment"
    exit 1
fi

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    print_message "red" "Error: Activation script not found at $VENV_DIR/bin/activate"
    print_message "yellow" "Please run ./install_and_run.sh again to properly set up the environment"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_message "yellow" "Warning: .env file not found, creating from example template..."
    if [ -f ".example.env" ]; then
        cp .example.env .env
        print_message "yellow" "Please edit .env to add your API keys"
    else
        print_message "red" "Error: .example.env template not found"
        touch .env
        print_message "yellow" "Created empty .env file. You'll need to add your API keys manually."
    fi
fi

# Run SuperCode
print_message "blue" "Starting SuperCode..."
python3 supercode_app.py
