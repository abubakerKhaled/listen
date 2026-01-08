# Listen - Voice-to-Text for Linux

A local voice-to-text transcription tool using OpenAI's Whisper model. Works completely offline with no external API calls.

## Features

- 🎤 **Push-to-talk** or **toggle mode** recording
- 🧠 **Local AI** - Uses faster-whisper for fast, private transcription
- 📋 **Clipboard integration** - Automatically copies transcribed text
- 🎯 **Auto model selection** - Uses tiny for CPU, base for GPU
- ⌨️ **Keyboard shortcut** - Ctrl+Space to record

## Installation

1. **Install system dependencies:**

   ```bash
   sudo apt install libportaudio2 portaudio19-dev xclip
   ```

2. **Set up Python environment:**

   ```bash
   cd /home/bakar/dev/personal/listen
   python -m venv env
   source env/bin/activate
   pip install -r requirements.txt
   ```

## Usage

### Start the app

```bash
# Activate environment
source env/bin/activate

# Run in push-to-talk mode (hold Ctrl+Space to record)
python listen.py

# Or use toggle mode (press Ctrl+Space to start/stop)
python listen.py --toggle
```

### Controls

| Key | Action |
|-----|--------|
| `Ctrl+Space` | Start/stop recording |
| `Ctrl+C` | Exit |

### Options

```bash
python listen.py --help

Options:
  --toggle, -t     Use toggle mode instead of push-to-talk
  --model, -m      Specify model: tiny, base, small, medium, large-v3
  --no-copy        Don't auto-copy to clipboard
```

### Examples

```bash
# Use a larger model for better accuracy
python listen.py --model small

# Toggle mode without clipboard copy
python listen.py --toggle --no-copy
```

## System-wide Installation (Optional)

To run `listen` from anywhere:

```bash
# Create a wrapper script
mkdir -p ~/.local/bin
cat > ~/.local/bin/listen << 'EOF'
#!/bin/bash
cd /home/bakar/dev/personal/listen
source env/bin/activate
python listen.py "$@"
EOF
chmod +x ~/.local/bin/listen

# Make sure ~/.local/bin is in your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Now you can run `listen` from any terminal!

## Troubleshooting

### "No audio captured"

- Check your microphone is working: `arecord -l`
- Make sure PulseAudio/PipeWire is running

### Slow transcription on CPU

- Use the `tiny` model: `python listen.py --model tiny`

### Keyboard shortcut not working

- pynput requires access to input devices
- On Wayland, you may need to run from a terminal with proper permissions
