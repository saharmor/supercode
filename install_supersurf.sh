#!/bin/bash
# Installation script for SuperSurf

echo "Installing SuperSurf dependencies..."

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Install required Python packages
echo "Installing required Python packages..."
python3 -m pip install -r requirements.txt

echo "Dependencies installed successfully!"
echo "To run SuperSurf, use: python3 supersurf_app.py"
