# Listen - Voice-to-Text for Linux

A local voice-to-text transcription tool using OpenAI's Whisper model. Works completely offline with no external API calls.

## Features

- 🎤 **Push-to-talk** or **toggle mode** recording
- 🧠 **Local AI** - Uses faster-whisper for fast, private transcription
- 📋 **Clipboard integration** - Automatically copies transcribed text
- 🎯 **Auto model selection** - Uses tiny for CPU, base for GPU
- ⌨️ **Keyboard shortcut** - Ctrl+Space to record
- 📦 **Portable** - Single AppImage works on any Linux distro

## Installation

### Download the AppImage

```bash
# Download from releases (replace with actual URL)
wget https://github.com/abubakerKhaled/listen/releases/download/v1.0.0/listen-1.0.0-x86_64.AppImage
chmod +x listen-1.0.0-x86_64.AppImage
```

### Install System-Wide (Recommended)

Install globally so you can run `listen` from anywhere:

```bash
# Copy to system bin
sudo cp listen-1.0.0-x86_64.AppImage /usr/local/bin/listen
sudo chmod +x /usr/local/bin/listen

# Now run from anywhere
listen --help
```

### Alternative: User-Only Installation

If you don't have sudo access:

```bash
# Create local bin directory
mkdir -p ~/.local/bin

# Copy AppImage
cp listen-1.0.0-x86_64.AppImage ~/.local/bin/listen
chmod +x ~/.local/bin/listen

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

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

## Building from Source

### Prerequisites

```bash
sudo apt install libportaudio2 portaudio19-dev wget python3-venv
```

### Build the AppImage

```bash
git clone https://github.com/abubakerKhaled/listen.git
cd listen
./build-appimage.sh
```

This creates `listen-1.0.0-x86_64.AppImage` in the project directory.

## Troubleshooting

### First run is slow

The Whisper model downloads on first use (~40MB for tiny, ~150MB for base). Subsequent runs are instant.

### "No audio captured"

- Check your microphone: `arecord -l`
- Ensure PulseAudio/PipeWire is running

### Slow transcription on CPU

Use the tiny model: `listen --model tiny`

### Keyboard shortcut not working

- pynput requires input device access
- On Wayland, run from a terminal with proper permissions

## Uninstall

```bash
# If installed system-wide
sudo rm /usr/local/bin/listen

# If installed in ~/.local/bin
rm ~/.local/bin/listen
```

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
