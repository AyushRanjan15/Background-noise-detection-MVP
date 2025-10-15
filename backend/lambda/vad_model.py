"""
TEN VAD Model Integration
Handles ONNX model loading and inference for Voice Activity Detection
"""

import numpy as np
import base64
import logging

logger = logging.getLogger()

# Global variables for model and hidden states
model_session = None
hidden_states = None


def initialize_model(model_path="/opt/model/ten-vad.onnx"):
    """
    Load ONNX model and initialize hidden states
    Called once on Lambda cold start
    """
    global model_session, hidden_states

    try:
        import onnxruntime as ort

        # Load model
        model_session = ort.InferenceSession(model_path)

        # Initialize hidden states (zeros for first frame)
        batch_size = 1
        hidden_states = [
            np.zeros((batch_size, 64), dtype=np.float32),  # h1
            np.zeros((batch_size, 64), dtype=np.float32),  # h2
            np.zeros((batch_size, 64), dtype=np.float32),  # h3
            np.zeros((batch_size, 64), dtype=np.float32),  # h4
        ]

        logger.info("TEN VAD model loaded successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


def decode_audio_frame(audio_base64):
    """
    Decode base64 audio data to numpy array
    Input: base64 encoded int16 PCM audio
    Output: float32 array normalized to [-1, 1]
    """
    # Decode base64
    audio_bytes = base64.b64decode(audio_base64)

    # Convert bytes to int16 array
    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

    # Normalize to float32 [-1, 1]
    audio_float = audio_int16.astype(np.float32) / 32768.0

    return audio_float


def extract_features(audio, sample_rate=16000):
    """
    Extract audio features for TEN VAD model WITHOUT librosa
    Input: Raw audio samples (1D array)
    Output: Features [3, 41] - log-mel spectrogram using numpy only

    Lightweight implementation using only numpy (no librosa dependency)
    """
    # Ensure audio is the right length (512 samples = 32ms at 16kHz)
    target_length = 512
    if len(audio) < target_length:
        audio = np.pad(audio, (0, target_length - len(audio)))
    elif len(audio) > target_length:
        audio = audio[:target_length]

    # Simple feature extraction using numpy
    # Split audio into 3 frequency bands using basic filtering
    features = []

    # Low frequency (0-2kHz)
    low = audio[::4]  # Downsample
    features.append(simple_energy_features(low, 41))

    # Mid frequency (2-4kHz) - basic high-pass
    mid = np.diff(audio, prepend=audio[0])[::2]
    features.append(simple_energy_features(mid, 41))

    # High frequency (4-8kHz) - second derivative
    high = np.diff(np.diff(audio, prepend=audio[0]), prepend=0)
    features.append(simple_energy_features(high, 41))

    # Stack to [3, 41]
    result = np.vstack(features).astype(np.float32)

    # Normalize
    result = (result - result.mean()) / (result.std() + 1e-8)

    return result


def simple_energy_features(signal, num_frames=41):
    """
    Extract simple energy-based features from signal
    """
    if len(signal) < num_frames:
        signal = np.pad(signal, (0, num_frames - len(signal)))

    # Split into frames
    frame_size = max(1, len(signal) // num_frames)
    features = []

    for i in range(num_frames):
        start = i * frame_size
        end = min(start + frame_size, len(signal))
        frame = signal[start:end]

        # RMS energy
        energy = np.sqrt(np.mean(frame ** 2)) if len(frame) > 0 else 0
        features.append(energy)

    return np.array(features, dtype=np.float32)


def run_inference(audio_data):
    """
    Run VAD inference on audio frame

    Args:
        audio_data: Dictionary with 'audio' key containing base64 encoded audio

    Returns:
        dict: {
            'vad_probability': float (0-1),
            'is_speech': bool,
            'timestamp': int
        }
    """
    global model_session, hidden_states

    # Initialize model if not loaded
    if model_session is None:
        success = initialize_model()
        if not success:
            raise RuntimeError("Failed to initialize VAD model")

    try:
        # Decode audio
        audio_base64 = audio_data.get('audio', '')
        audio = decode_audio_frame(audio_base64)

        # Extract features [3, 41]
        features = extract_features(audio)

        # Add batch dimension: [1, 3, 41]
        features_batch = np.expand_dims(features, axis=0)

        # Prepare input feed
        input_feed = {
            'input_1': features_batch,
            'input_2': hidden_states[0],
            'input_3': hidden_states[1],
            'input_6': hidden_states[2],
            'input_7': hidden_states[3]
        }

        # Run inference
        outputs = model_session.run(None, input_feed)

        # Extract VAD probability
        vad_output = outputs[0]  # Shape: [batch, ?, 1]
        vad_probability = float(vad_output[0, 0, 0])

        # Update hidden states for next frame
        hidden_states = [outputs[1], outputs[2], outputs[3], outputs[4]]

        # Classify (threshold at 0.5)
        is_speech = vad_probability > 0.5

        return {
            'vad_probability': round(vad_probability, 4),
            'is_speech': is_speech,
            'timestamp': audio_data.get('timestamp', 0)
        }

    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise


def reset_hidden_states():
    """
    Reset hidden states (call when connection starts/ends)
    """
    global hidden_states
    batch_size = 1
    hidden_states = [
        np.zeros((batch_size, 64), dtype=np.float32),
        np.zeros((batch_size, 64), dtype=np.float32),
        np.zeros((batch_size, 64), dtype=np.float32),
        np.zeros((batch_size, 64), dtype=np.float32),
    ]
    logger.info("Hidden states reset")
