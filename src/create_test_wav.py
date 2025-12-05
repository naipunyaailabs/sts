"""Create a short 16 kHz mono WAV file for testing the translation API."""

import numpy as np
import soundfile as sf

# Parameters
sample_rate = 16000
duration = 2.0  # seconds
frequency = 440.0  # A4 tone

# Generate a simple sine wave (this won't contain speech, but will test the pipeline)
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)

# Save as 16 kHz mono WAV
sf.write("test_en.wav", audio_data, sample_rate)
print("Created test_en.wav (16 kHz mono sine wave)")
