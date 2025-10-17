/**
 * WebSocketClient - Manages WebSocket connection to backend
 * Handles bidirectional streaming of audio data and noise detection results
 */
class WebSocketClient {
    constructor(config = {}) {
        this.wsUrl = config.wsUrl || 'ws://localhost:8080'; // Default to local mock
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // ms

        // Callbacks
        this.onConnected = null;
        this.onDisconnected = null;
        this.onNoiseDetection = null;
        this.onError = null;
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        return new Promise((resolve, reject) => {
            try {
                this.socket = new WebSocket(this.wsUrl);

                this.socket.onopen = () => {
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    console.log('WebSocket connected');

                    if (this.onConnected) {
                        this.onConnected();
                    }

                    resolve();
                };

                this.socket.onmessage = (event) => {
                    this.handleMessage(event.data);
                };

                this.socket.onerror = (error) => {
                    console.error('WebSocket error:', error);

                    if (this.onError) {
                        this.onError(error);
                    }
                };

                this.socket.onclose = () => {
                    this.isConnected = false;
                    console.log('WebSocket disconnected');

                    if (this.onDisconnected) {
                        this.onDisconnected();
                    }

                    // Attempt to reconnect
                    this.attemptReconnect();
                };

            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                reject(error);
            }
        });
    }

    /**
     * Handle incoming messages from server
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data);

            switch (message.type) {
                case 'noise_detection':
                    if (this.onNoiseDetection) {
                        this.onNoiseDetection({
                            isNoisy: message.isNoisy,
                            confidence: message.confidence,
                            timestamp: message.timestamp
                        });
                    }
                    break;

                case 'error':
                    console.error('Server error:', message.error);
                    if (this.onError) {
                        this.onError(new Error(message.error));
                    }
                    break;

                case 'pong':
                    // Heartbeat response
                    break;

                default:
                    console.warn('Unknown message type:', message.type);
            }

        } catch (error) {
            console.error('Error parsing message:', error);
        }
    }

    /**
     * Send audio frame to server
     */
    sendAudioFrame(frameData) {
        if (!this.isConnected || !this.socket) {
            console.warn('Cannot send audio frame: Not connected');
            return false;
        }

        try {
            const message = {
                type: 'audio_frame',
                data: frameData
            };

            this.socket.send(JSON.stringify(message));
            return true;

        } catch (error) {
            console.error('Error sending audio frame:', error);
            return false;
        }
    }

    /**
     * Attempt to reconnect to server
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * this.reconnectAttempts;

        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);

        setTimeout(() => {
            this.connect().catch(error => {
                console.error('Reconnect failed:', error);
            });
        }, delay);
    }

    /**
     * Send ping to keep connection alive
     */
    sendPing() {
        if (this.isConnected) {
            const message = { type: 'ping' };
            this.socket.send(JSON.stringify(message));
        }
    }

    /**
     * Disconnect from server
     */
    disconnect() {
        if (this.socket) {
            this.maxReconnectAttempts = 0; // Prevent reconnection
            this.socket.close();
            this.socket = null;
        }
        this.isConnected = false;
    }

    /**
     * Get connection status
     */
    getStatus() {
        return {
            isConnected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            readyState: this.socket ? this.socket.readyState : null
        };
    }
}
