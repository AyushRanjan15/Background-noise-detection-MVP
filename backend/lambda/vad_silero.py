"""
Silero VAD Integration for Lambda
Frame-by-frame VAD with proper probabilities
"""

import numpy as np
import base64
import logging

logger = logging.getLogger()

# Global variables
vad_session = None
vad_state_h = None
vad_state_c = None


def initialize_vad(model_path="/opt/model/silero_vad.onnx"):
    """
    Initialize Silero VAD ONNX model
    Called once on Lambda cold start
    """
    global vad_session, vad_state_h, vad_state_c

    try:
        import onnxruntime as ort

        logger.info(f"Loading Silero VAD model from: {model_path}")
        vad_session = ort.InferenceSession(model_path)

        # Initialize LSTM states [2, 1, 64]
        vad_state_h = np.zeros((2, 1, 64), dtype=np.float32)
        vad_state_c = np.zeros((2, 1, 64), dtype=np.float32)

        logger.info("✓ Silero VAD initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize VAD: {e}", exc_info=True)
        return False


def decode_audio_frame(audio_base64):
    """
    Decode base64 audio to float32 array
    """
    audio_bytes = base64.b64decode(audio_base64)
    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
    audio_float = audio_int16.astype(np.float32) / 32768.0
    return audio_float


def run_vad_inference(audio_data):
    """
    Run Silero VAD on audio frame

    Args:
        audio_data: Dictionary with 'audio' key (base64 encoded)

    Returns:
        dict: {
            'vad_probability': float (0-1),
            'is_speech': bool,
            'timestamp': int
        }
    """
    global vad_session, vad_state_h, vad_state_c

    # Initialize if not loaded
    if vad_session is None:
        success = initialize_vad()
        if not success:
            raise RuntimeError("Failed to initialize Silero VAD")

    try:
        # Decode audio
        audio_base64 = audio_data.get('audio', '')
        audio = decode_audio_frame(audio_base64)

        # Silero VAD expects exactly 512 samples (32ms at 16kHz)
        frame_size = 512

        # Pad or truncate to 512 samples
        if len(audio) < frame_size:
            audio = np.pad(audio, (0, frame_size - len(audio)))
        elif len(audio) > frame_size:
            audio = audio[:frame_size]

        # Reshape to [1, 512]
        input_frame = audio.reshape(1, -1).astype(np.float32)

        # Run inference
        ort_inputs = {
            'x': input_frame,
            'h': vad_state_h,
            'c': vad_state_c
        }

        ort_outputs = vad_session.run(None, ort_inputs)

        # Get probability [1, 1] and update states
        vad_probability = float(ort_outputs[0][0][0])
        vad_state_h = ort_outputs[1]
        vad_state_c = ort_outputs[2]

        # Classify as speech if probability > 0.5
        is_speech = vad_probability > 0.5

        return {
            'vad_probability': round(vad_probability, 4),
            'is_speech': is_speech,
            'timestamp': audio_data.get('timestamp', 0)
        }

    except Exception as e:
        logger.error(f"VAD inference error: {e}", exc_info=True)
        raise


def reset_vad_state():
    """
    Reset VAD state (call when connection starts/ends)
    """
    global vad_state_h, vad_state_c

    vad_state_h = np.zeros((2, 1, 64), dtype=np.float32)
    vad_state_c = np.zeros((2, 1, 64), dtype=np.float32)

    logger.info("VAD state reset")
