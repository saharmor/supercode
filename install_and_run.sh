#!/bin/bash

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

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

# Welcome message
clear
print_message "blue" "=============================================="
print_message "blue" "     SuperCode Installation and Setup         "
print_message "blue" "=============================================="
echo ""

# Check if Python 3.8+ is installed
if ! command_exists python3; then
  print_message "red" "Error: Python 3 is not installed."
  print_message "yellow" "Please install Python 3.8 or higher from https://www.python.org/downloads/"
  exit 1
fi

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
python_major=$(echo $python_version | cut -d'.' -f1)
python_minor=$(echo $python_version | cut -d'.' -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 8 ]); then
  print_message "red" "Error: SuperCode requires Python 3.8 or higher."
  print_message "yellow" "Current version: $python_version"
  print_message "yellow" "Please upgrade your Python installation."
  exit 1
fi

print_message "green" "✓ Python $python_version detected"

# Create virtual environment
print_message "blue" "Setting up virtual environment..."

# Check if venv module is available
VENV_DIR="supercode_env"

# Create virtual environment using venv (more reliable than virtualenv)
if [ ! -d "$VENV_DIR" ]; then
  print_message "yellow" "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
  if [ $? -ne 0 ]; then
    print_message "red" "Failed to create virtual environment with venv."
    print_message "red" "Please install venv if it's not available on your system."
    exit 1
  fi
  print_message "green" "✓ Virtual environment created successfully"
else
  print_message "green" "✓ Using existing virtual environment"
fi

# Activate the virtual environment
print_message "yellow" "Activating virtual environment..."
if [ -f "$VENV_DIR/bin/activate" ]; then
  source "$VENV_DIR/bin/activate"
  
  # Verify activation
  if [[ "$VIRTUAL_ENV" == *"$VENV_DIR"* ]]; then
    print_message "green" "✓ Virtual environment activated successfully"
  else
    print_message "red" "Failed to activate virtual environment. Path: $VENV_DIR/bin/activate"
    exit 1
  fi
else
  print_message "red" "Could not find activation script at $VENV_DIR/bin/activate"
  exit 1
fi

# Upgrade pip inside the virtual environment
print_message "blue" "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install dependencies
print_message "blue" "Installing dependencies..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
  print_message "red" "Failed to install dependencies."
  print_message "yellow" "Please check if requirements.txt exists and is valid."
  exit 1
fi
print_message "green" "✓ Dependencies installed successfully"

# Check for required API keys in .env file
ENV_FILE=".env"
EXAMPLE_ENV_FILE=".example.env"

# Create .env file if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
  print_message "blue" "Creating default .env file..."
  
  # Check if example template exists and copy it
  if [ -f "$EXAMPLE_ENV_FILE" ]; then
    cp "$EXAMPLE_ENV_FILE" "$ENV_FILE"
    print_message "green" "✓ Created .env file from example template"
  else
    touch "$ENV_FILE"
    print_message "yellow" "Warning: $EXAMPLE_ENV_FILE not found, created empty .env file"
  fi
else
  print_message "green" "✓ Using existing .env file"
fi

# Function to prompt for a key if it's missing
check_api_key() {
  local key_name=$1
  local prompt_message=$2
  local guide_url=$3
  
  # Check if key exists in .env file
  if ! grep -q "^$key_name=" "$ENV_FILE" || grep -q "^$key_name=your_.*_here" "$ENV_FILE"; then
    print_message "yellow" "API key required: $key_name"
    print_message "yellow" "$prompt_message"
    
    # Show the guide URL in the prompt if provided
    if [ -n "$guide_url" ]; then
      read -p "Enter your $key_name (guide here $guide_url): " api_key
    else
      read -p "Enter your $key_name: " api_key
    fi
    
    # Only update if a non-empty key was provided
    if [ -n "$api_key" ]; then
      # If the key exists but is a placeholder, update it
      if grep -q "^$key_name=" "$ENV_FILE"; then
        sed -i '' "s|^$key_name=.*|$key_name=$api_key|" "$ENV_FILE"
      else
        # Otherwise append it
        echo "$key_name=$api_key" >> "$ENV_FILE"
      fi
      print_message "green" "✓ $key_name saved to .env file"
    else
      print_message "yellow" "No key provided, using default placeholder"
    fi
  else
    print_message "green" "✓ $key_name already configured"
  fi
}

# Check for Anthropic API key
check_api_key "ANTHROPIC_API_KEY" "Required for Claude Computer Use to control the IDE." "https://www.youtube.com/watch?v=Vp4we-ged4w"

# Check for OpenAI API key (optional)
print_message "yellow" "Do you want to use OpenAI Whisper for higher quality transcription? (costs ~$0.1/hour)"
print_message "yellow" "If not, Google's free speech recognition will be used (y/n):"
read use_openai

if [[ $use_openai == "y" || $use_openai == "Y" ]]; then
  check_api_key "OPENAI_API_KEY" "Used for Whisper transcription (higher quality)." "https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key"
  
  # Set USE_OPENAI_API flag if not already set
  if ! grep -q "^USE_OPENAI_API=" "$ENV_FILE"; then
    echo "USE_OPENAI_API=true" >> "$ENV_FILE"
  else
    # Update existing line
    sed -i '' 's/^USE_OPENAI_API=.*/USE_OPENAI_API=true/' "$ENV_FILE"
  fi
else
  print_message "green" "Using Google's free speech recognition"
  
  # Set USE_OPENAI_API flag if not already set
  if ! grep -q "^USE_OPENAI_API=" "$ENV_FILE"; then
    echo "USE_OPENAI_API=false" >> "$ENV_FILE"
  else
    # Update existing line
    sed -i '' 's/^USE_OPENAI_API=.*/USE_OPENAI_API=false/' "$ENV_FILE"
  fi
fi

# Check for Google Gemini API key (for screenshots and image analysis)
check_api_key "GEMINI_API_KEY" "Used for screenshots and image analysis." "https://github.com/saharmor/gemini-multimodal-playground?tab=readme-ov-file#getting-your-gemini-api-key"

# Ask for permissions
print_message "yellow" "SuperCode requires accessibility permissions to control your IDE."
print_message "yellow" "You may be prompted to grant these permissions when the app runs."
print_message "yellow" "Press Enter to continue..."
read

# All set, run the application
print_message "blue" "=============================================="
print_message "blue" "     Installation Complete! Starting SuperCode...     "
print_message "blue" "=============================================="

# Make sure run_supercode.sh is executable
if [ -f "run_supercode.sh" ]; then
  chmod +x run_supercode.sh
  print_message "green" "✓ To run SuperCode again later, use: ./run_supercode.sh"
fi

# Run the app
python3 supercode_app.py 