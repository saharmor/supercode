#!/usr/bin/env python3
"""
SuperSurf Main Module - Entry point for the SuperSurf application.
This module provides the main function for starting the SuperSurf application.
"""

import os
import sys
import time
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SuperSurf')

def main():
    """Initialize and start the SuperSurf application"""
    try:
        # Load environment variables
        logger.info("Loading environment variables...")
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        load_dotenv(dotenv_path)
        
        # Basic configuration
        logger.info("Starting SuperSurf application")
        model_name = os.getenv('LOCAL_WHISPER_MODEL', 'base')
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
        logger.error(f"Error initializing SuperSurf app: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
