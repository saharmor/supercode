#!/usr/bin/env python3
"""
SuperSurf Mac App Runner - Standard Mac version with menu bar interface.
This script launches the standard SuperSurf Mac application.
"""

import os
import sys
import time
import logging
import traceback
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure using the correct Python environment
ENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'supersurf_env', 'bin', 'python')
if os.path.exists(ENV_PYTHON) and sys.executable != ENV_PYTHON:
    print(f"Restarting with Python from virtual environment: {ENV_PYTHON}")
    os.execl(ENV_PYTHON, ENV_PYTHON, *sys.argv)

# Ensure current directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SuperSurfMac')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="SuperSurf Mac Application")
    parser.add_argument("--use-openai-api", action="store_true",
                        help="Use OpenAI's Whisper API instead of local model")
    parser.add_argument("--openai-model", type=str, default="whisper-1",
                        help="OpenAI Whisper model to use (default: whisper-1)")
    return parser.parse_args()

def main():
    """Initialize and start the SuperSurf Mac application"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Load environment variables
        logger.info("Loading environment variables...")
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(dotenv_path)
        
        # Override environment variables with command line arguments if provided
        if args.use_openai_api:
            os.environ["USE_OPENAI_API"] = "true"
            logger.info("Using OpenAI Whisper API (command line override)")
        
        if args.openai_model:
            os.environ["OPENAI_WHISPER_MODEL"] = args.openai_model
            logger.info(f"Using OpenAI model: {args.openai_model} (command line override)")
        
        # Basic configuration
        logger.info("Starting SuperSurf Mac standard version")
        model_name = os.getenv('WHISPER_MODEL', 'base')
        device_index = int(os.getenv('AUDIO_DEVICE_INDEX', '0'))
        logger.info(f"Whisper Model: {model_name}")
        logger.info(f"Audio Device Index: {device_index}")
        
        # Configure environment variables to limit threads
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['PYTORCH_NUM_THREADS'] = '1'
        os.environ['MKL_NUM_THREADS'] = '1' 
        os.environ['OPENBLAS_NUM_THREADS'] = '1'
        os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
        os.environ['NUMEXPR_NUM_THREADS'] = '1'
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        
        logger.info(f"OMP Threads: {os.environ['OMP_NUM_THREADS']}")
        logger.info(f"PyTorch Threads: {os.environ['PYTORCH_NUM_THREADS']}")
        
        # Import the SuperSurfApp from mac_app.py
        try:
            from super_surf.mac_app import SuperSurfApp
            logger.info("Successfully imported SuperSurfApp")
            
            # Initialize and run the app
            app = SuperSurfApp()
            app.run()
        except ImportError as e:
            logger.error(f"Could not import SuperSurfApp: {str(e)}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error initializing SuperSurf Mac app: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 