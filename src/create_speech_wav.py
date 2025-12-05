"""Create a short speech-like WAV file for testing the translation API.
We'll generate a simple synthetic 'speech' pattern using two tones to simulate speech.
"""

import numpy as np
import soundfile as sf

# Parameters
sample_rate = 16000
duration = 1.5  # seconds

# Create a simple pattern that resembles speech (two-tone sequence)
t1 = np.linspace(0, 0.6, int(sample_rate * 0.6), endpoint=False)
tone1 = 0.3 * np.sin(2 * np.pi * 200 * t1)  # Low tone

t2 = np.linspace(0, 0.6, int(sample_rate * 0.6), endpoint=False)
tone2 = 0.3 * np.sin(2 * np.pi * 800 * t2)  # Higher tone

# Add some noise to make it more speech-like
noise = 0.02 * np.random.normal(0, 1, len(tone1) + len(tone2))

# Combine
audio_data = np.concatenate([tone1, np.zeros(int(sample_rate * 0.2)), tone2])
# Add noise of matching length
noise = 0.02 * np.random.normal(0, 1, len(audio_data))
audio_data = audio_data + noise

# Normalize
audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

# Save as 16 kHz mono WAV
sf.write("test_speech.wav", audio_data, sample_rate)
print("Created test_speech.wav (16 kHz mono synthetic speech pattern)")
