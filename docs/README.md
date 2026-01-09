# Listen Documentation

Welcome to the **Listen** documentation! This comprehensive guide covers everything you need to know about the Listen voice-to-text transcription tool for Linux.

---

## 📚 Documentation Index

| Document | Description |
|----------|-------------|
| [Architecture Overview](./architecture.md) | System design, component interactions, and data flow |
| [Core Modules](./modules.md) | Detailed documentation of all source code modules |
| [Technical Decisions](./decisions.md) | Rationale behind key design choices |
| [API Reference](./api-reference.md) | Programmatic API for developers |
| [Build & Packaging](./build-packaging.md) | AppImage creation and distribution |
| [Contributing Guide](./contributing.md) | How to contribute to the project |

---

## 🎯 Project Overview

**Listen** is a voice-to-text transcription tool designed specifically for Linux. It provides both a modern GTK4/libadwaita GUI and a powerful terminal CLI interface, allowing users to quickly transcribe speech using OpenAI's Whisper model.

### Key Features

- 🖥️ **Dual Interface** — Modern GTK4 GUI with real-time waveform visualization AND terminal CLI with Rich formatting
- 🎤 **Flexible Recording** — Push-to-talk (hold) or toggle (press) recording modes
- 🧠 **Local AI Processing** — Uses faster-whisper for completely offline transcription
- 📋 **Clipboard Integration** — Automatic clipboard copy after transcription
- 🎯 **Smart Model Selection** — Auto-selects optimal Whisper model based on GPU memory
- 🌍 **Multilingual Support** — Enhanced Arabic support with language detection
- 📦 **Portable Distribution** — Single AppImage runs on any Linux distribution

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Speech Recognition | `faster-whisper` | Fast Whisper inference with CTranslate2 |
| Audio Recording | `PyAudio` | Cross-platform audio input |
| GUI Framework | GTK4 + libadwaita | Modern GNOME-style interface |
| CLI Interface | `rich` + `pynput` | Beautiful terminal UI with keyboard capture |
| Clipboard | `pyperclip` | Cross-platform clipboard access |
| Packaging | AppImage | Universal Linux distribution |

---

## 🗂️ Project Structure

```
listen/
├── src/
│   └── listen_app/           # Main application package
│       ├── __init__.py       # Package exports
│       ├── cli.py            # CLI entry point & terminal interface
│       ├── gui.py            # GTK4/libadwaita GUI interface
│       ├── recorder.py       # Audio recording module
│       └── transcriber.py    # Whisper transcription engine
├── appimage/
│   ├── AppRun                # AppImage entry point script
│   ├── listen.desktop        # Desktop integration file
│   └── listen.png            # Application icon
├── docs/                     # Documentation (you are here!)
├── build-appimage.sh         # AppImage build script
├── setup.sh                  # Unified setup script
├── install.sh                # User installation script
├── uninstall.sh              # Uninstallation script
├── pyproject.toml            # Python package configuration
└── README.md                 # Project README
```

---

## 🚀 Quick Links

- **[Getting Started](../README.md#-quick-start)** — Installation and first run
- **[Usage Guide](../README.md#-usage)** — How to use Listen
- **[Troubleshooting](../README.md#-troubleshooting)** — Common issues and solutions
- **[GitHub Repository](https://github.com/abubakerKhaled/listen)** — Source code and releases

---

<p align="center">
  <strong>Listen</strong> — Voice-to-Text for Linux<br>
  Made with ❤️ for the Linux community
</p>
