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

# Verify PyQt5 installation
print_message "blue" "Verifying dependencies..."
python3 -c "import PyQt5" 2>/dev/null
if [ $? -ne 0 ]; then
    print_message "red" "Error: PyQt5 module not found."
    print_message "yellow" "Would you like to install it now? (y/n)"
    read install_pyqt
    
    if [[ $install_pyqt == "y" || $install_pyqt == "Y" ]]; then
        print_message "blue" "Installing PyQt5..."
        pip install PyQt5>=5.15.6
        
        # Verify installation
        python3 -c "import PyQt5" 2>/dev/null
        if [ $? -ne 0 ]; then
            print_message "red" "PyQt5 installation failed. Please install it manually:"
            print_message "yellow" "pip install PyQt5>=5.15.6"
            exit 1
        else
            print_message "green" "✓ PyQt5 installed successfully"
        fi
    else
        print_message "red" "SuperCode requires PyQt5 to run. Exiting."
        exit 1
    fi
else
    print_message "green" "✓ PyQt5 is properly installed"
fi

# Verify pynput installation
python3 -c "import pynput" 2>/dev/null
if [ $? -ne 0 ]; then
    print_message "red" "Error: pynput module not found."
    print_message "yellow" "Would you like to install it now? (y/n)"
    read install_pynput
    
    if [[ $install_pynput == "y" || $install_pynput == "Y" ]]; then
        print_message "blue" "Installing pynput..."
        pip install pynput>=1.7.6
        
        # Verify installation
        python3 -c "import pynput" 2>/dev/null
        if [ $? -ne 0 ]; then
            print_message "red" "pynput installation failed."
            print_message "yellow" "Global keyboard shortcuts won't work, but you can continue without them."
            print_message "yellow" "Press Enter to continue anyway or Ctrl+C to abort..."
            read
        else
            print_message "green" "✓ pynput installed successfully"
        fi
    else
        print_message "yellow" "Global keyboard shortcuts won't work, but continuing anyway..."
    fi
else
    print_message "green" "✓ pynput is properly installed"
fi

# Run SuperCode
print_message "blue" "Starting SuperCode..."
python3 supercode_app.py
