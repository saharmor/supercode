# SuperCode ✨

> The conversational assistant for vibe coders

SuperCode enhances your coding experience by letting you interact with your IDE using voice commands. Vibe coding how it should be.

(currently Mac only, more OS coming soon!)

## Features

### Core Functionality
- **Voice-Activated Commands**: Trigger actions with the "activate" keyword
- **IDE Integration**: Seamlessly works with supported IDEs (Cursor, Lovable, etc.)
- **Real-time Status Display**: Always know what SuperCode is doing with the overlay UI

### Most Used Features
**Talk to your IDE with natural language commands**: 
- "Activate type [text]" - Have the AI type and edit code for you
- "Activate change [ide]" - Switch to a different [supported IDE](#supported-ai-ides)
- "Activate learn [element] [name]" - Teach SuperCode about a new UI element
- "Activate click [element]" - Click a learned UI element
- "Activate find [text]" - Search for text in the current file
**Real-time voice notifications** - receive instant alerts when coding tasks are completed, eliminating the need to manually check if the coding agent is done.

## Supported AI IDEs
- Cursor - The AI-first code editor
- Windsurf - Open source AI coding environment
- Lovable - AI-powered web IDE for full-stack development
- Coming Soon: Claude Code, Base44, Bolt, v0

## Installation

For the easiest setup experience, use our installation script:

```bash
# Clone the repository
git clone https://github.com/saharmor/supercode.git
cd supercode

# Run the installation script (automatically sets up everything)
./install_and_run.sh
```

The script will:
1. Check for Python 3.8+ and install requirements
2. Create a virtual environment
3. Prompt for required API keys if not found
4. Configure the .env file (using .example.env as a template)
5. Launch SuperCode

## Setup & Requirements

### Dependencies
- Python 3.8+
- See `requirements.txt` for all dependencies

### API Keys Needed
- Anthropic API key for Claude Computer Use - [see guide for getting your key](https://www.youtube.com/watch?v=Vp4we-ged4w)
- OpenAI API key for Whisper transcription, optional, otherwise uses Google free ASR - [see guide for getting your key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key)
- Google Gemini API key for screenshots and image analysis - [see guide for getting your key](https://github.com/saharmor/gemini-multimodal-playground?tab=readme-ov-file#getting-your-gemini-api-key)

### Configuration
SuperCode uses a `.env` file for configuration. An example template (`.example.env`) is provided with the repository. The installation script will automatically create this file for you, but you can also manually copy and edit it:

```bash
cp .example.env .env
# Then edit .env with your preferred text editor
```

### System Requirements
- macOS (currently macOS-only)
- Requires Accessibility permissions
- Works when IDE is on your primary screen

### Costs
- Approximately $0.2/hour with default settings, originating from Claude Computer Use, which finds the location of the interacted elements on yoru screen, and OpenAI `gpt-4o-transcribe`
- Can be ~80% cheaper using Google's free ASR, but at the cost of lower transcription quality

## Usage

```
Activate [command] [parameters]
```

Example commands:
- `Activate type Write a function that sorts an array` - Start typing in the IDE
- `Activate change lovable` - Switch to the Lovable interface
- `Activate learn Accept the blue button to the right that runs the suggested terminal code` - Teach a new button


## Coming Soon
- Electron app for a more native experience
- Claude Code integration with reminder to run /compact
- Gemini Flash / OpenAI Realtime transcription
- Model selector when using "Activate Type" to optimize credits usage
- Error detection and fixing suggestions
- Rabbit hole detector to keep you on track
- Commit message generation for Windsurf
- Realtime audio APIs for faster and smoother experience
- Function calling for more robust voice command processing
- Support for additional languages: Spanish, German, and French


## Want to Partner?
Are you based in San Francisco? Let's code! Reach out to us on X [@theaievangelist](https://x.com/theaievangelist).



## License
Apache 2.0
