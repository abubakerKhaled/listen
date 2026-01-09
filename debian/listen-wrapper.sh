#!/bin/bash
APPIMAGE_PATH="$HOME/.local/share/listen/listen.AppImage"
if [ ! -f "$APPIMAGE_PATH" ]; then
    echo "Listen AppImage not found. Running installer..."
    /usr/lib/listen/listen-installer.sh
fi
exec "$APPIMAGE_PATH" "$@"
