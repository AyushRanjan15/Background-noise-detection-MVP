# TEN VAD Model Deployment Guide

## Overview

Deploying the TEN VAD (Voice Activity Detection) model to AWS Lambda using Lambda Layers.

**Model**: ten-vad.onnx (324 KB)
**Method**: Lambda Layer (includes model + dependencies)
**Output**: Speech probability (0-1) displayed on frontend

## Deployment Steps

### 1. Create Lambda Layer

```bash
cd infrastructure/cdk
./create_lambda_layer.sh
```

This will:
- Install `onnxruntime`, `librosa`, `numpy`
- Copy `ten-vad.onnx` model
- Create `ten-vad-layer.zip` (~100MB)

**Expected output:**
```
✓ Lambda layer created: ten-vad-layer.zip
  Size: ~100M
```

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
Frontend (40ms frames, base64 encoded)
    ↓
Lambda message.py
    ↓
vad_model.py (decode + extract features)
    ↓
TEN VAD ONNX Model
    ├─ Input: [1, 3, 41] MFCC features
    ├─ Hidden States: [1, 64] x 4 (LSTM)
    └─ Output: VAD probability (0-1)
    ↓
Frontend displays "Speech Probability: 87.3%"
```

### Model Details

**Input:**
- `input_1`: Audio features `[batch, 3, 41]` (log-mel spectrogram)
- `input_2-7`: Hidden states `[batch, 64]` (LSTM memory across frames)

**Output:**
- `output_1`: Speech probability `[batch, 1, 1]` (0 = silence, 1 = speech)
- `output_2-7`: Updated hidden states for next frame

**Processing:**
1. Decode base64 audio → float32 array
2. Extract 3-band log-mel spectrogram (41 time frames)
3. Feed to ONNX model with hidden states
4. Get speech probability
5. Update hidden states for next frame

## File Changes

### New Files
- `backend/lambda/vad_model.py` - VAD model integration
- `infrastructure/cdk/create_lambda_layer.sh` - Layer creation script
- `infrastructure/cdk/ten-vad-layer.zip` - Lambda Layer package

### Modified Files
- `backend/lambda/message.py` - Use VAD instead of mock
- `frontend/src/app.js` - Display VAD probability
- `infrastructure/cdk/cdk/noise_detection_stack.py` - Add Lambda Layer

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
