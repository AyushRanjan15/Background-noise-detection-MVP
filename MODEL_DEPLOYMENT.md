# Voice Activity Detection Model Deployment Guide

## Overview

Deploying Silero VAD (Voice Activity Detection) model to AWS Lambda using Lambda Layers for real-time speech detection.

**Current Model**: Silero VAD (`silero_vad.onnx` - 629 KB)
**Method**: Lambda Layer (includes model + dependencies)
**Output**: Speech probability (0-1) displayed on frontend

## Model Comparison

Two VAD models are available in the `model/` directory:

### 1. Silero VAD (Currently Deployed)
- **File**: `silero_vad.onnx` (629 KB)
- **Status**: ✅ Deployed and tested
- **Performance**: Industry-standard, widely used in production
- **Input**: Raw audio samples [1, 512] (32ms at 16kHz)
- **LSTM States**: [2, 1, 64] for temporal context
- **Pros**: Well-documented, proven performance, simple preprocessing
- **Inference**: Frame-by-frame with state management

##### Install the framework using 
```bash
pip install sherpa-onnx
```

##### Download it using
```bash
wget https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx
```

##### Usage
```bash
import sherpa_onnx

# Initialize VAD
config = sherpa_onnx.VadModelConfig()
config.silero_vad.model = "silero_vad.onnx"
config.sample_rate = 16000
config.num_threads = 1
config.provider = "cpu"

vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=30)

# Process audio
# audio is numpy array, float32, shape: (num_samples,)
vad.accept_waveform(audio)

while not vad.empty():
    segment = vad.front()
    # segment.start: start time
    # segment.samples: audio samples
    print(f"Speech detected: {segment.start}s - {segment.start + len(segment.samples)/16000}s")
    vad.pop()
```

### 2. TEN VAD (Alternative)
- **File**: `ten-vad.onnx` (324 KB)
- **Status**: Downloaded, not yet tested
- **Performance**: Claims superior to Silero and WebRTC VAD
- **Input**: Feature-based (requires preprocessing investigation)
- **Pros**: Smaller model, potentially better precision/recall
- **Cons**: Less documentation, requires testing to understand interface

**Current deployment uses Silero VAD** due to proven local test results and clear ONNX interface.

## Deployment Steps

### 1. Create Lambda Layer

```bash
cd infrastructure/cdk
./create_lambda_layer.sh
```

This will:
- Install `onnxruntime==1.16.3` and `numpy==1.24.3` (optimized for Lambda Python 3.11)
- Copy `silero_vad.onnx` model from `../../model/`
- Create `ten-vad-layer.zip` (~44MB unzipped)

**Expected output:**
```
✓ Lambda layer created: ten-vad-layer.zip
  Size: 44M
```

**Note**: No librosa dependency needed - Silero VAD works with raw audio samples.

### 2. Deploy Stack

```bash
./deploy.sh deploy
```

This will:
- Upload Lambda Layer to AWS
- Update Message Handler Lambda with layer attachment
- Increase memory to 1024MB for ONNX Runtime

**Deployment time:** ~5-7 minutes

### 3. Test Frontend

```bash
cd ../../
npm run frontend:dev
# Open: http://localhost:8000/frontend/public/
```

Click "Start Detection" and speak into your microphone.

**Expected behavior:**
- **When speaking**: Green indicator, "Speech Detected", probability ~0.7-0.9
- **When silent**: Red indicator, "No Speech / Noise", probability ~0.1-0.3

## How It Works

### Data Flow

```
Microphone (16kHz PCM)
    ↓
Frontend (40ms frames = 640 samples, base64 encoded)
    ↓
Lambda message.py (WebSocket handler)
    ↓
vad_silero.py (decode + pad/truncate to 512 samples)
    ↓
Silero VAD ONNX Model
    ├─ Input: x=[1, 512] raw audio samples
    ├─ LSTM States: h=[2, 1, 64], c=[2, 1, 64]
    └─ Output: probability=[1, 1] (0-1)
    ↓
Frontend displays "Speech Probability: 87.3%"
```

**Note:** Frontend sends 640 samples (40ms), Lambda pads/truncates to 512 samples (32ms) for Silero VAD.

### Model Details: Silero VAD

**Architecture:**
- Pre-trained LSTM-based Voice Activity Detection
- Optimized for real-time frame-by-frame inference
- Maintains temporal context through LSTM states

**Input:**
- `x`: Raw audio samples `[1, 512]` (32ms at 16kHz, float32)
- `h`: LSTM hidden state `[2, 1, 64]` (maintained across frames)
- `c`: LSTM cell state `[2, 1, 64]` (maintained across frames)

**Output:**
- `output`: Speech probability `[1, 1]` (0 = silence/noise, 1 = speech)
- `hn`: Updated hidden state `[2, 1, 64]` for next frame
- `cn`: Updated cell state `[2, 1, 64]` for next frame

**Processing Pipeline:**
1. Decode base64 audio from frontend → int16 array
2. Convert to float32 normalized to [-1, 1]
3. Pad/truncate to exactly 512 samples
4. Reshape to [1, 512]
5. Run ONNX inference with LSTM states
6. Extract probability and update states
7. Send result back to frontend via WebSocket

**Threshold:** Probability > 0.5 = Speech detected

## Costs

**Lambda Layer storage:** Free (under 75GB limit)
**Increased Lambda memory:** 1024MB vs 512MB
- Cost increase: ~$0.0000166667 per 100ms
- For 1000 requests/day: ~$0.50/month extra

**Total estimated cost:** Still within free tier for MVP usage

## Troubleshooting

### Layer creation fails
```bash
# Install dependencies locally first
pip install onnxruntime librosa numpy
```

### Lambda out of memory
- Check CloudWatch logs
- Increase memory in `noise_detection_stack.py` (line 119)
- Currently set to 1024MB (can go up to 10240MB)

### Model not loading
Check Lambda logs:
```bash
aws logs tail /aws/lambda/NoiseDetectionStack-MessageHandler --follow \
  --profile personal --region ap-southeast-2
```

Look for:
```
TEN VAD model loaded successfully
```

### Wrong predictions
- Model expects 16kHz audio
- Check frontend sends correct sample rate
- Verify audio encoding (int16 PCM)

## Next Steps

1. ✅ Model deployed and working
2. ⏳ Collect real usage data
3. ⏳ Fine-tune feature extraction for better accuracy
4. ⏳ Consider training custom noise detection model (not just VAD)

## Notes

**VAD vs Noise Detection:**
- Current model detects **speech vs silence**
- Not specifically trained for **background noise during speech**
- Good for: Filtering silence, detecting when user is speaking
- Limitation: Won't detect background noise while speaking

For true noise detection during speech, you'll need:
- A model trained on clean vs noisy speech
- Or use VAD + additional noise estimation (SNR, spectral analysis)

For MVP: VAD provides useful feedback about speech activity!
