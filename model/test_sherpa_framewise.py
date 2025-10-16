#!/usr/bin/env python3
"""
Frame-by-frame VAD using Sherpa-ONNX
This approach processes each frame independently and returns probabilities
"""

import numpy as np
import onnxruntime as ort
import argparse


def load_audio(file_path, target_sr=16000):
    """Load audio file"""
    try:
        import librosa
        audio, sr = librosa.load(file_path, sr=target_sr, mono=True)
        print(f"✓ Loaded audio: {len(audio)} samples at {sr}Hz ({len(audio)/sr:.2f}s)")
        return audio, sr
    except ImportError:
        from scipy.io import wavfile
        sr, audio = wavfile.read(file_path)
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        if sr != target_sr:
            ratio = target_sr / sr
            new_length = int(len(audio) * ratio)
            audio = np.interp(
                np.linspace(0, len(audio), new_length),
                np.arange(len(audio)),
                audio
            )
            sr = target_sr
        print(f"✓ Loaded audio: {len(audio)} samples at {sr}Hz ({len(audio)/sr:.2f}s)")
        return audio, sr


def process_framewise_vad(audio_file, model_path="silero_vad.onnx"):
    """
    Process audio frame-by-frame through Silero VAD

    Silero VAD expects 512 samples (32ms at 16kHz)
    """
    print("=" * 80)
    print("Frame-by-Frame VAD Analysis")
    print("=" * 80)

    # Load audio
    audio, sr = load_audio(audio_file)

    # Load ONNX model directly
    print(f"\nLoading model: {model_path}")
    session = ort.InferenceSession(model_path)

    # Silero VAD uses 512 sample frames (32ms at 16kHz)
    frame_size = 512
    hop_length = 256  # 16ms hop = 50% overlap

    print(f"Frame size: {frame_size} samples (32ms)")
    print(f"Hop length: {hop_length} samples (16ms)")

    # Initialize LSTM states
    h = np.zeros((2, 1, 64), dtype=np.float32)
    c = np.zeros((2, 1, 64), dtype=np.float32)

    probabilities = []
    timestamps = []

    print(f"\nProcessing {len(audio)} samples...")

    # Process frame by frame
    for i in range(0, len(audio) - frame_size, hop_length):
        frame = audio[i:i+frame_size]

        # Ensure exact frame size
        if len(frame) != frame_size:
            frame = np.pad(frame, (0, frame_size - len(frame)))

        # Prepare input [1, 512]
        input_frame = frame.reshape(1, -1).astype(np.float32)

        # Run inference
        ort_inputs = {
            'x': input_frame,
            'h': h,
            'c': c
        }

        ort_outputs = session.run(None, ort_inputs)

        # Get probability [1, 1] and updated states
        prob = float(ort_outputs[0][0][0])
        h = ort_outputs[1]
        c = ort_outputs[2]

        probabilities.append(prob)
        timestamps.append(i / sr)

    probabilities = np.array(probabilities)
    timestamps = np.array(timestamps)

    print(f"\n✓ Processed {len(probabilities)} frames")
    print(f"  Mean probability: {probabilities.mean():.3f}")
    print(f"  Speech frames (>0.5): {(probabilities > 0.5).sum()} ({(probabilities > 0.5).sum()/len(probabilities)*100:.1f}%)")

    return audio, sr, timestamps, probabilities


def visualize_framewise(audio, sr, timestamps, probabilities, output_file=None):
    """Visualize frame-by-frame VAD results"""
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Waveform
    time_audio = np.arange(len(audio)) / sr
    ax1.plot(time_audio, audio, linewidth=0.5, alpha=0.7, color='#2E86AB')
    ax1.set_ylabel('Amplitude', fontsize=12)
    ax1.set_title('Audio Waveform', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-1, 1)

    # Highlight speech regions
    speech_mask = probabilities > 0.5
    for i in range(len(timestamps)-1):
        if speech_mask[i]:
            ax1.axvspan(timestamps[i], timestamps[i+1], alpha=0.1, color='green')

    # VAD Probability
    ax2.plot(timestamps, probabilities, linewidth=2, color='#2E86AB')
    ax2.fill_between(timestamps, probabilities, alpha=0.3, color='#2E86AB')
    ax2.axhline(y=0.5, color='red', linestyle='--', linewidth=1, label='Threshold (0.5)')
    ax2.set_ylabel('Speech Probability', fontsize=12)
    ax2.set_xlabel('Time (seconds)', fontsize=12)
    ax2.set_title('Silero VAD Output (Frame-by-Frame)', fontsize=14, fontweight='bold')
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Highlight speech regions
    for i in range(len(timestamps)-1):
        if speech_mask[i]:
            ax2.axvspan(timestamps[i], timestamps[i+1], alpha=0.1, color='green')

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"\n✓ Saved visualization to: {output_file}")

    plt.show()


def main():
    parser = argparse.ArgumentParser(description='Frame-by-frame VAD analysis')
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('--model', default='silero_vad.onnx', help='Path to VAD model')
    parser.add_argument('--output', help='Save visualization to file')

    args = parser.parse_args()

    # Process
    audio, sr, timestamps, probabilities = process_framewise_vad(
        args.audio_file,
        args.model
    )

    # Visualize
    visualize_framewise(audio, sr, timestamps, probabilities, args.output)

    # Statistics
    print("\n" + "=" * 80)
    print("STATISTICS:")
    print("=" * 80)
    speech_frames = np.sum(probabilities > 0.5)
    total_frames = len(probabilities)

    print(f"Total frames: {total_frames}")
    print(f"Speech frames (>0.5): {speech_frames} ({speech_frames/total_frames*100:.1f}%)")
    print(f"\nProbability distribution:")
    print(f"  0.0-0.2: {np.sum((probabilities >= 0.0) & (probabilities < 0.2))} frames")
    print(f"  0.2-0.4: {np.sum((probabilities >= 0.2) & (probabilities < 0.4))} frames")
    print(f"  0.4-0.6: {np.sum((probabilities >= 0.4) & (probabilities < 0.6))} frames")
    print(f"  0.6-0.8: {np.sum((probabilities >= 0.6) & (probabilities < 0.8))} frames")
    print(f"  0.8-1.0: {np.sum((probabilities >= 0.8) & (probabilities <= 1.0))} frames")


if __name__ == '__main__':
    main()
