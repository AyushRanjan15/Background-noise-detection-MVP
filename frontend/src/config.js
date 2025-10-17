/**
 * Configuration for frontend
 * Update WEBSOCKET_URL after deploying CDK stack
 */

const Config = {
    // Local mock backend (for development)
    MOCK_WS_URL: 'ws://localhost:8080',

    // AWS WebSocket URL (from CDK deployment)
    AWS_WS_URL: 'wss://xx87lr80yd.execute-api.ap-southeast-2.amazonaws.com/prod',

    // Auto-select: Use AWS if available, otherwise local
    get WEBSOCKET_URL() {
        return this.AWS_WS_URL || this.MOCK_WS_URL;
    },

    // Other config
    FRAME_SIZE_MS: 40,  // Audio frame size in milliseconds
    SAMPLE_RATE: 16000, // Audio sample rate in Hz
    SMOOTHING_WINDOW: 4 // Moving average window size
};
