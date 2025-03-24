#!/bin/bash
# Installation script for SuperCode

echo "Installing SuperCode dependencies..."

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Install required Python packages
echo "Installing required Python packages..."
python3 -m pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating default .env file..."
    cp .env.default .env
    echo "Please edit .env to configure your speech recognition preferences."
fi

echo "Dependencies installed successfully!"
echo "To run SuperCode, use: ./run_supercode.sh"
