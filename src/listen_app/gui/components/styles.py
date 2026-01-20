"""CSS styling constants for the Listen GUI."""

MAIN_CSS = b"""
.recording-button {
    background: linear-gradient(to bottom, #e53935, #c62828);
    color: white;
}
.device-info-frame {
    background: alpha(@card_bg_color, 0.5);
    border-radius: 8px;
}
.device-info-label {
    font-size: 11px;
    font-family: monospace;
}
.gpu-active {
    color: #76b900;
}
.cpu-active {
    color: #0071c5;
}
"""
