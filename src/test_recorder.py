import sys
import time
from listen_app.recorder import AudioRecorder

print("Initializing Recorder...")
try:
    with AudioRecorder() as recorder:
        print("Recorder Initialized.")
        print("Starting recording...")
        recorder.start()
        print("Recording for 2 seconds...")
        time.sleep(2)
        print("Stopping recording...")
        wav_data = recorder.stop()
        print(f"Recorded {len(wav_data)} bytes.")
except Exception as e:
    print(f"Error: {e}")
