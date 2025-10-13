# Setup Guide

## Project Structure

```
Background-noise-detection-MVP/
├── frontend/              # Frontend web client
│   ├── public/           # Static assets and HTML
│   │   ├── index.html    # Main UI
│   │   └── styles.css    # Styling
│   └── src/              # JavaScript modules
│       ├── app.js        # Main application logic
│       ├── audioProcessor.js    # Audio capture & processing
│       ├── websocketClient.js   # WebSocket communication
│       └── noiseDetector.js     # Temporal smoothing logic
├── backend/              # Backend services
│   ├── lambda/          # AWS Lambda functions (TBD)
│   ├── mock-server.py   # Local development server
│   └── requirements.txt # Python dependencies
├── infrastructure/       # AWS CDK infrastructure code
│   └── cdk/            # CDK stack definitions (TBD)
├── tests/               # Test files
└── docs/                # Documentation

```

## Quick Start - Frontend Only (Demo Mode)

### Option 1: Run without backend (Demo Mode)

The frontend can run standalone with simulated noise detection:

```bash
# From project root
npm run frontend:dev
```

Then open: http://localhost:8000/frontend/public/

Click "Start Detection" - it will run in demo mode with simulated results.

### Option 2: Run with Mock Backend

1. Install Python dependencies:
```bash
cd backend
pip3 install -r requirements.txt
```

2. Start the mock WebSocket server:
```bash
python3 mock-server.py
```

3. In another terminal, start the frontend:
```bash
npm run frontend:dev
```

4. Open: http://localhost:8000/frontend/public/

Now the frontend will connect to the mock backend for more realistic testing.

## Browser Requirements

- Chrome, Firefox, Safari, or Edge (latest versions)
- HTTPS or localhost (required for microphone access)
- Microphone permissions granted

## Features Implemented

### Frontend (✅ Complete)
- Audio capture from microphone (16kHz, mono)
- Frame-by-frame processing (30-50ms chunks)
- WebSocket client with reconnection logic
- Temporal smoothing (4-frame moving average)
- Visual feedback (color-coded indicator)
- Real-time activity logging
- Error handling and recovery

### Backend (🚧 In Progress)
- Mock WebSocket server for local testing (✅)
- AWS Lambda function for inference (⏳)
- API Gateway WebSocket integration (⏳)
- EFS for ML model storage (⏳)
- DynamoDB session tracking (⏳)

## Next Steps

1. Test the frontend with microphone input
2. Verify WebSocket communication with mock backend
3. Train/obtain ML model for noise detection
4. Implement AWS CDK infrastructure
5. Deploy Lambda function with actual model
6. End-to-end integration testing

## Troubleshooting

### Microphone Not Working
- Ensure browser has microphone permissions
- Check browser console for errors
- Try HTTPS or localhost only

### WebSocket Connection Failed
- Verify mock server is running on port 8080
- Check firewall settings
- Frontend will fall back to demo mode automatically

### Audio Quality Issues
- Check sample rate in browser console
- Verify frame size is 30-50ms
- Review activity log for processing errors
