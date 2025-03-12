#!/bin/bash

# SuperSurf Installation Script
# This script sets up the SuperSurf voice control application

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}  SuperSurf Installation Script   ${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""

# Check if Python 3.9 is installed
echo -e "${YELLOW}Checking for Python 3.9...${NC}"
if command -v python3.9 &>/dev/null; then
    PYTHON_VERSION=$(python3.9 --version)
    echo -e "${GREEN}Found $PYTHON_VERSION${NC}"
else
    echo -e "${RED}Python 3.9 not found. Please install Python 3.9 before proceeding.${NC}"
    echo -e "${YELLOW}Visit https://www.python.org/downloads/ to download Python.${NC}"
    exit 1
fi

# Check for pip
echo -e "${YELLOW}Checking for pip...${NC}"
if command -v pip3.9 &>/dev/null || command -v pip3 &>/dev/null; then
    PIP_VERSION=$(command -v pip3.9 >/dev/null && pip3.9 --version || pip3 --version)
    echo -e "${GREEN}Found pip: ${PIP_VERSION}${NC}"
else
    echo -e "${RED}pip not found. Please install pip before proceeding.${NC}"
    exit 1
fi

# Check if FFmpeg is installed (required for Whisper)
echo -e "${YELLOW}Checking for FFmpeg (required for Whisper)...${NC}"
if command -v ffmpeg &>/dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
    echo -e "${GREEN}Found FFmpeg: ${FFMPEG_VERSION}${NC}"
else
    echo -e "${RED}FFmpeg not found. Installing FFmpeg...${NC}"
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use homebrew if available
        if command -v brew &>/dev/null; then
            echo -e "${YELLOW}Installing FFmpeg via Homebrew...${NC}"
            brew install ffmpeg
        else
            echo -e "${RED}Homebrew not found. Please install FFmpeg manually:${NC}"
            echo -e "${YELLOW}1. Install Homebrew from https://brew.sh/${NC}"
            echo -e "${YELLOW}2. Run: brew install ffmpeg${NC}"
            echo -e "${RED}After installing FFmpeg, please run this script again.${NC}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - try apt-get
        if command -v apt-get &>/dev/null; then
            echo -e "${YELLOW}Installing FFmpeg via apt-get...${NC}"
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        else
            echo -e "${RED}Package manager not found. Please install FFmpeg manually for your Linux distribution.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Unsupported OS. Please install FFmpeg manually for your operating system.${NC}"
        exit 1
    fi
    
    # Verify FFmpeg installation
    if command -v ffmpeg &>/dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
        echo -e "${GREEN}FFmpeg installed successfully: ${FFMPEG_VERSION}${NC}"
    else
        echo -e "${RED}FFmpeg installation failed. Please install FFmpeg manually and try again.${NC}"
        exit 1
    fi
fi

# Create and activate virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
python3.9 -m venv supersurf_env

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source supersurf_env/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies... This may take a few minutes.${NC}"
python3.9 -m pip install --upgrade pip
python3.9 -m pip install -r requirements.txt

# Create a default .env file
echo -e "${YELLOW}Creating configuration file...${NC}"
if [ ! -f .env ]; then
    echo "# SuperSurf Configuration" > .env
    echo "WHISPER_MODEL=base" >> .env
    echo -e "${GREEN}Created default configuration file.${NC}"
else
    echo -e "${GREEN}Configuration file already exists.${NC}"
fi

echo ""
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  SuperSurf Installation Complete ${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo -e "To start SuperSurf, run the following command:"
echo -e "${BLUE}./run_enhanced.py${NC}"
echo ""
echo -e "${YELLOW}Note: The first run will download the Whisper model, which may take a few minutes.${NC}"
echo -e "${YELLOW}      Default model is 'base'. You can change this in Settings > Model Selection.${NC}"
echo "" 