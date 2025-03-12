# SuperSurf

SuperSurf is a voice control application that enables hands-free operation of the Windsurf IDE and other macOS applications, making coding more efficient and accessible. Using advanced voice recognition technology, it allows developers to execute commands, navigate code, and perform editing operations through voice commands.

## Recent Improvements

SuperSurf has undergone significant enhancements to improve reliability, user experience, and command recognition:

### Continuous Recording Mode
- Added continuous recording mode that keeps listening until explicitly stopped
- Fixed issues with premature recording termination
- Improved handling of multiprocessing to prevent OpenMP warnings and crashes
- Enhanced silence detection with configurable thresholds
- Added real-time audio level monitoring during recording

### Speech Recognition Options
- **Local Speech Recognition (Default)**
  - Uses local Whisper model for transcription (no internet required)
  - Full privacy - audio never leaves your device
  - Multiple model size options (tiny to large) for balancing speed vs. accuracy
  - Significantly reduced operating costs (free instead of per-API-call)

- **OpenAI Whisper API (Optional)**
  - Option to use OpenAI's cloud-based Whisper API for higher accuracy
  - Requires OpenAI API key and internet connection
  - Configurable via environment variables or command-line options
  - Better for complex commands or noisy environments

### Advanced Audio Processing
- Volume normalization for consistent audio levels
- Noise filtering to reduce background sounds
- Voice Activity Detection (VAD) to capture only speech
- Improved signal processing for clearer input

### Reliability Improvements
- Enhanced error handling with detailed error reporting and recovery
- Improved transcription stability with automatic retry mechanisms
- Automatic restart of audio system after consecutive errors
- Proper resource cleanup to prevent memory leaks
- Maximum restart attempt limits to prevent infinite error loops
- Graceful degradation when services are unavailable

### User Interface Enhancements
- Redesigned menu structure with intuitive categorization
- Enhanced status indicators in the menu bar
- Improved visual feedback for command execution
- Separate menus for commands, settings, tools, and help
- Real-time command success/error statistics
- Cleaner menu bar display without distracting emojis

### Command Recognition Improvements
- Enhanced fuzzy matching for better command detection
- Extensive dictionary of common transcription errors
- Ensemble transcription with multiple variants for higher accuracy
- Command confirmation interface for verification before execution

### Documentation and Help
- Comprehensive troubleshooting guide
- Detailed command examples with practical use cases
- Interactive tutorial for new users
- Better organized help menus with categorized commands
- How-to guides for common tasks and workflows

### Performance Optimizations
- Transcription performance monitoring and statistics
- Circular buffer for continuous listening
- Optimized audio preprocessing pipeline
- Configuration options for performance tuning
- Support for different Whisper model sizes (tiny to large)

## Features

### Voice Command Categories

#### Basic Editing Commands
- Type text (`"Surf type [text]"` or `"Surf write [text]"`) - Types the specified text
- Save file (`"Surf save"`) - Saves the current file (⌘S)
- Undo action (`"Surf undo"`) - Undoes the last action (⌘Z)
- Redo action (`"Surf redo"`) - Redoes the last undone action (⇧⌘Z)
- Copy text (`"Surf copy"`) - Copies selected text (⌘C)
- Paste text (`"Surf paste"`) - Pastes from clipboard (⌘V)
- Cut text (`"Surf cut"`) - Cuts selected text (⌘X)
- Select all (`"Surf select all"`) - Selects all text (⌘A)

#### Navigation Commands
- Find text (`"Surf find [text]"` or `"Surf search [text]"`) - Finds text in document (⌘F)
- Next result (`"Surf next"`) - Goes to next search result (⌘G)
- Previous result (`"Surf previous"`) - Goes to previous search result (⇧⌘G)
- Go to line (`"Surf go to line [number]"`) - Goes to specified line
- Go to top (`"Surf top"` or `"Surf go to top"`) - Goes to top of document (⌘↑)
- Go to bottom (`"Surf bottom"` or `"Surf go to bottom"`) - Goes to bottom of document (⌘↓)

### Tools and Utilities
- Microphone testing
- Keyboard functionality testing
- Speech translation
- Performance monitoring
- Audio device selection
- Model configuration

## System Requirements

- macOS 10.9 or later
- Python 3.9 or later
- Windsurf IDE
- Working microphone
- FFmpeg (install via `brew install ffmpeg`)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pedroarrudaa/SuperSurf.git
   cd SuperSurf
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv supersurf_env
   source supersurf_env/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install FFmpeg (if not already installed):
   ```bash
   brew install ffmpeg
   ```

5. Run the application:
   ```bash
   python run_enhanced.py
   ```

## Dependencies

- `openai-whisper`: Local Whisper model for speech recognition
- `pyaudio`: Audio capture and device management
- `pynput`: Keyboard control for command execution
- `rumps`: macOS menu bar application framework
- `python-dotenv`: Environment variable management
- `numpy`: Numerical operations for audio processing
- `pydub`: Audio processing utilities
- `torch`: Machine learning framework for Whisper model
- `FFmpeg`: Audio format conversion (system dependency)

## Usage

1. Click the SuperSurf icon in the menu bar
2. Select "Start Listening" to begin voice control
3. Speak commands prefixed with "Surf"
4. Monitor command status in the menu bar
5. Use the Help menu for command references

### Running in Continuous Mode
To use SuperSurf with continuous recording (recording until manually stopped):

```bash
# Run with standard time-limited recording
python run_enhanced.py

# Run with continuous recording (recommended)
./run_continuous.py
```

The continuous mode keeps listening for commands until you explicitly click "Stop Listening" in the menu bar, allowing for a more natural interaction without time pressure.

### Example Commands
```
"Surf type hello world"     # Types "hello world"
"Surf find example"         # Searches for "example"
"Surf save"                 # Saves current file
"Surf go to line 42"        # Goes to line 42
"Surf select all"           # Selects all text
"Surf copy"                 # Copies selected text
"Surf paste"                # Pastes from clipboard
```

## Configuration

SuperSurf offers several configuration options:

### Continuous Recording Settings
- MAX_RECORDING_TIME: Safety timeout (default: 60 seconds)
- SILENCE_THRESHOLD: Audio level for silence detection (default: 100, lower = more sensitive)
- OMP_NUM_THREADS: Controls OpenMP threading (set to 1 to prevent multiprocessing issues)

### Audio Settings
- Microphone selection
- Audio input level adjustments
- Recording parameters

### Model Configuration
- Whisper model selection (tiny, base, small, medium, large)
- Each model size offers different trade-offs between speed and accuracy
- Recommended starting point: "base" model

### Performance Settings
- Recognition timeout configuration
- Auto-restart settings
- Error handling preferences

## Whisper Model Selection

SuperSurf lets you choose between different Whisper model sizes:

| Model | Size | Speed | Accuracy | Memory Usage |
|-------|------|-------|----------|--------------|
| tiny  | 75MB | Fastest | Basic | ~1GB |
| base  | 142MB | Fast | Good | ~1GB |
| small | 466MB | Medium | Better | ~2GB |
| medium | 1.5GB | Slow | Very Good | ~5GB |
| large | 3GB | Slowest | Best | ~10GB |

The model is loaded when you start the application and can be changed in the Settings menu.

## Fine-tuning the Whisper Model

For even higher accuracy with your specific voice and command patterns, you can fine-tune the Whisper model:

### Requirements for Fine-tuning
- Python 3.9+
- PyTorch
- 8GB+ RAM
- NVIDIA GPU (recommended for faster training)

### Fine-tuning Steps

1. **Set up the fine-tuning environment**:
   ```bash
   pip install -U openai-whisper datasets transformers
   ```

2. **Create a training dataset of your commands**:
   Create a dataset in the format required by Whisper fine-tuning:
   ```
   # commands.json
   [
     {"audio_path": "data/save_command_1.wav", "text": "Surf save"},
     {"audio_path": "data/find_command_1.wav", "text": "Surf find example"},
     {"audio_path": "data/goto_command_1.wav", "text": "Surf go to line 100"},
     # Add more examples (20+ recommended for each command)
   ]
   ```

3. **Record command examples**:
   Use the built-in recording tool to capture examples of your voice commands:
   ```bash
   python tools/record_commands.py
   ```

4. **Run the fine-tuning script**:
   ```bash
   python tools/finetune_whisper.py --base-model base --dataset commands.json --output-dir ./fine_tuned_model
   ```

5. **Use the fine-tuned model**:
   ```bash
   # Update your .env file to point to the fine-tuned model
   WHISPER_MODEL=/path/to/fine_tuned_model
   ```

### Tips for Best Results
- Record in the same environment where you'll use SuperSurf
- Include variations in how you pronounce commands
- Add background noise similar to your working environment for robustness
- Include common errors you experience for targeted improvement
- Start with the "base" model for faster fine-tuning, then move to "small" or "medium"

### Example Fine-tuning Script

```python
# tools/finetune_whisper.py
import whisper
import torch
import json
import argparse
from datasets import Dataset
from transformers import WhisperProcessor, WhisperForConditionalGeneration, Seq2SeqTrainer, Seq2SeqTrainingArguments

def main(args):
    # Load base model and processor
    model = WhisperForConditionalGeneration.from_pretrained(f"openai/whisper-{args.base_model}")
    processor = WhisperProcessor.from_pretrained(f"openai/whisper-{args.base_model}")
    
    # Load your dataset
    with open(args.dataset, 'r') as f:
        data = json.load(f)
    
    # Preprocess the dataset
    def preprocess_function(example):
        audio_array, _ = whisper.load_audio(example["audio_path"])
        input_features = processor(audio_array, sampling_rate=16000, return_tensors="pt").input_features
        labels = processor.tokenizer(example["text"]).input_ids
        return {"input_features": input_features.squeeze(), "labels": labels}
    
    # Convert to HuggingFace dataset format
    dataset = Dataset.from_list(data)
    processed_dataset = dataset.map(preprocess_function)
    
    # Set up training arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=1,
        learning_rate=1e-5,
        warmup_steps=50,
        num_train_epochs=3,
        save_strategy="epoch",
        fp16=torch.cuda.is_available(),
        report_to="none",
    )
    
    # Initialize trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=processed_dataset,
    )
    
    # Start training
    trainer.train()
    
    # Save the fine-tuned model
    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"Fine-tuned model saved to {args.output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Whisper model on custom commands")
    parser.add_argument("--base-model", type=str, default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Base Whisper model to fine-tune")
    parser.add_argument("--dataset", type=str, required=True, help="Path to JSON dataset")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to save the fine-tuned model")
    args = parser.parse_args()
    main(args)

## Troubleshooting

### Common Issues

1. **Command Not Recognized**
   - Speak clearly and at a moderate pace
   - Ensure "surf" prefix is clearly pronounced
   - Check microphone input levels
   - Try alternative command variations

2. **Audio Input Issues**
   - Verify microphone permissions
   - Check system audio input settings
   - Ensure correct input device is selected
   - Try disconnecting and reconnecting your microphone

3. **Model Loading Issues**
   - Ensure you have enough RAM for your chosen model
   - Try using a smaller model size if you experience slowdowns
   - Make sure all dependencies are correctly installed
   - Check that FFmpeg is installed

4. **Slow Response Times**
   - Use a smaller Whisper model (e.g., "tiny" or "base")
   - Close other resource-intensive applications
   - Ensure your computer meets the minimum system requirements

### Audio Diagnostic Tools

SuperSurf includes diagnostic tools to help identify and resolve audio recording issues:

#### Continuous Recording Diagnostic

This tool helps diagnose issues with the continuous recording mode:

```bash
# List available audio devices
./tools/diagnose_continuous.py --list-devices

# Test a specific audio device (replace 4 with your device index)
./tools/diagnose_continuous.py --device 4 --duration 20

# Run without visualization (for terminal-only environments)
./tools/diagnose_continuous.py --no-visualize
```

The diagnostic tool provides:
- Real-time visualization of audio levels
- Detection of silence or low volume
- Recommendations for optimal silence threshold settings
- Saving of test recordings for further analysis
- Detailed logging of audio device performance

Use this tool if you experience issues with:
- Premature recording termination
- Microphone not detecting audio
- Silence detection problems
- Audio quality issues

## Contributing

Contributions are welcome! Please feel free to submit pull requests or create issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Future Development Plans

### Enhanced Command Recognition
- Machine learning-based command recognition
- Custom command creation and mapping
- Context-aware commands for different applications
- Command chaining for complex operations

### Expanded Application Support
- Specialized command sets for popular applications
- Application-specific shortcuts and functions
- Automatic detection of active application

### Accessibility Improvements
- Support for additional languages
- Voice profile training for better recognition
- Features for users with motor disabilities
- Alternative activation methods

### Performance Optimizations
- Faster model loading times
- Memory usage optimizations
- Buffered audio processing for faster responses
- Reduced latency between command and execution