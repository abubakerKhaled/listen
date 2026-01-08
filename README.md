# Listen - Voice-to-Text for Linux

A local voice-to-text transcription tool using OpenAI's Whisper model. Works completely offline with no external API calls.

## Features

- 🎤 **Push-to-talk** or **toggle mode** recording
- 🧠 **Local AI** - Uses faster-whisper for fast, private transcription
- 📋 **Clipboard integration** - Automatically copies transcribed text
- 🎯 **Auto model selection** - Uses tiny for CPU, base for GPU
- ⌨️ **Keyboard shortcut** - Ctrl+Space to record

## Installation

### Option 1: AppImage (Recommended)

Download and run - works on any Linux distribution:

```bash
# Download the AppImage
wget https://github.com/abubakerKhaled/listen/releases/download/v1.0.0/listen-1.0.0-x86_64.AppImage

# Make it executable
chmod +x listen-1.0.0-x86_64.AppImage

# Run it
./listen-1.0.0-x86_64.AppImage
```

**Install system-wide (optional):**

```bash
sudo cp listen-1.0.0-x86_64.AppImage /usr/local/bin/listen
sudo chmod +x /usr/local/bin/listen

# Now you can run 'listen' from anywhere
listen --toggle
```

### Option 2: From Source

1. **Install system dependencies:**

   ```bash
   sudo apt install libportaudio2 portaudio19-dev xclip
   ```

2. **Clone and install:**

   ```bash
   git clone https://github.com/abubakerKhaled/listen.git
   cd listen
   pip install .
   ```

### Option 3: Development Setup

```bash
# Clone the repository
git clone https://github.com/abubakerKhaled/listen.git
cd listen

# Create virtual environment
python -m venv env
source env/bin/activate

# Install in editable mode
pip install -e .
```

## Usage

### Start the app

```bash
# Push-to-talk mode (hold Ctrl+Space to record)
listen

# Toggle mode (press Ctrl+Space to start/stop)
listen --toggle
```

### Controls

| Key | Action |
|-----|--------|
| `Ctrl+Space` | Start/stop recording |
| `Ctrl+C` | Exit |

### Options

```bash
listen --help

Options:
  --toggle, -t     Use toggle mode instead of push-to-talk
  --model, -m      Specify model: tiny, base, small, medium, large-v3
  --no-copy        Don't auto-copy to clipboard
```

### Examples

```bash
# Use a larger model for better accuracy
listen --model small

# Toggle mode without clipboard copy
listen --toggle --no-copy
```

## Building the AppImage

To build the AppImage yourself:

```bash
# Install system dependencies
sudo apt install libportaudio2 portaudio19-dev wget

# Run the build script
./build-appimage.sh
```

The script will create `listen-1.0.0-x86_64.AppImage` in the project directory.

## Troubleshooting

### "No audio captured"

- Check your microphone is working: `arecord -l`
- Make sure PulseAudio/PipeWire is running

### Slow transcription on CPU

- Use the `tiny` model: `listen --model tiny`

### Keyboard shortcut not working

- pynput requires access to input devices
- On Wayland, you may need to run from a terminal with proper permissions

### First run is slow

- The Whisper model downloads on first use (~40MB for tiny, ~150MB for base)
- Subsequent runs will be much faster

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
