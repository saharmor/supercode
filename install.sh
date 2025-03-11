#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script only works on macOS"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.9 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$PYTHON_VERSION < 3.9" | bc -l) )); then
    print_error "Python 3.9 or higher is required (current version: $PYTHON_VERSION)"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    print_error "pip3 not found. Please install pip3"
    exit 1
fi

if ! [ -d "/Applications/Windsurf.app" ]; then
    print_warning "Windsurf IDE not found in /Applications/"
fi

if [ ! -d "supersurf_env" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv supersurf_env
else
    print_warning "Virtual environment already exists"
fi

print_status "Activating virtual environment..."
source supersurf_env/bin/activate

print_status "Updating pip..."
pip install --upgrade pip

print_status "Installing dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    print_warning "File .env not found"
    echo "OPENAI_API_KEY=your_key_here" > .env
fi

print_status "Installing SuperSurf in development mode..."
pip install -e .

print_status "Installation completed!"
print_status "To start SuperSurf, run: python -m super_surf.main"

print_warning "IMPORTANT: SuperSurf needs accessibility permissions"
print_warning "Please go to System Preferences > Security and Privacy > Privacy > Accessibility"
print_warning "and add the Terminal or your IDE to the list of allowed applications"