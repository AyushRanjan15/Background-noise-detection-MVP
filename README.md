# Project motivation
Speakers in virtual meetings, recordings, and live presentations often experience background noise that degrades audio quality and communication effectiveness. Current solutions either lack real-time feedback or require post-processing, preventing speakers from addressing noise issues as they occur.
A near real-time background noise detection service that provides immediate visual feedback to speakers when background noise is present during their speech. The system processes audio on a frame-by-frame basis, running inference through a trained machine learning model to classify audio segments as "clean speech" or "noisy speech."

# MVP - Simplified Architecture

## Architecture Overview

### Tech Stack (Simplified for MVP)

- **Frontend**: HTML/JavaScript (simple web client)
- **Backend**: AWS Lambda with Python runtime
- **Communication**: API Gateway WebSocket for bidirectional streaming
- **Model Storage**: S3 or Lambda Layer (no VPC needed)
- **State Management**: Amazon DynamoDB for session tracking
- **Monitoring**: AWS CloudWatch for basic metrics

### System Flow

```
Browser Client
    ↓ (WebSocket connection)
AWS API Gateway WebSocket
    ↓ (frame-by-frame audio data)
AWS Lambda Function
    ├─ Load model from S3/Layer (first invocation)
    ├─ Run inference on audio frame
    └─ Return noise detection result
    ↓ (WebSocket response)
Browser UI updates immediately
```

## ML Model Storage Options

### Option 1: Lambda Layer (Recommended if model < 250MB)
- **Pros**: Fastest (no download), included in deployment
- **Cons**: 250MB unzipped limit
- **Setup**: Package model as Lambda Layer, attach to function
- **Best for**: Lightweight models (TensorFlow Lite, ONNX Runtime)

### Option 2: S3 Bucket
- **Pros**: Any model size, easy to update, no VPC needed
- **Cons**: Cold start delay (2-3 seconds to download)
- **Setup**: Upload model to S3, Lambda downloads on first run
- **Best for**: Larger models, frequent model updates

### Option 3: Bundled in Lambda
- **Pros**: Simplest deployment
- **Cons**: 50MB deployment package limit (250MB unzipped)
- **Setup**: Include model files in Lambda deployment zip
- **Best for**: Very small models only

### Option 4: EFS (Production - Not for MVP)
- **Pros**: Large models, fast access after mount
- **Cons**: Requires VPC, NAT Gateway (~$32/month), complex setup
- **Setup**: VPC + EFS + Lambda in VPC
- **Best for**: Production with models > 250MB and low latency requirements

**Current Approach**: Will implement **Option 1 or 2** based on model size once available

### In Scope

- Single-user audio processing via browser microphone
- Binary classification: Noise detected (yes/no) with confidence score
- Simple visual feedback: Color indicator (green = clean, red = noisy)
- Basic temporal smoothing: 3-5 frame moving average to reduce flicker
- Audio frame processing: 30-50ms chunks at 16kHz sample rate
- WebSocket connection: Persistent connection for continuous streaming
- Basic error handling: Connection failures, timeout recovery

## Quick Start

### Test Frontend (Demo Mode)
```bash
npm run frontend:dev
# Open: http://localhost:8000/frontend/public/
```

### Test with Mock Backend
```bash
# Terminal 1: Start mock backend
cd backend
pip3 install -r requirements.txt
python3 mock-server.py

# Terminal 2: Start frontend
npm run frontend:dev
# Open: http://localhost:8000/frontend/public/
```

## Project Structure
```
frontend/          # Web client with microphone access & UI
  ├── public/      # HTML & CSS
  └── src/         # JS modules (audio, WebSocket, smoothing)
backend/           # Lambda functions & mock server
infrastructure/    # AWS CDK code (TBD)
docs/             # Setup & deployment guides
```

## Implementation Status

✅ **Completed:**
- Frontend UI with real-time visual feedback
- Audio capture and frame processing (16kHz, 40ms frames)
- WebSocket client with reconnection
- Temporal smoothing (4-frame moving average)
- Mock backend for local testing

⏳ **Pending:**
- ML model (training/selection in progress)
- AWS CDK infrastructure setup (simplified - no VPC)
- Lambda function with model inference logic
- API Gateway WebSocket deployment
- DynamoDB session tracking
- End-to-end AWS integration

## AWS Deployment Configuration

**Profile**: `personal`
**Region**: `ap-southeast-2` (Sydney)

Infrastructure managed via AWS CDK with simplified architecture (no VPC/EFS for MVP)

See [docs/SETUP.md](docs/SETUP.md) for detailed instructions.