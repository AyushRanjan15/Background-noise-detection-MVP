/**
 * Main application logic
 * Coordinates audio processing, WebSocket communication, and UI updates
 */

// Application state
const app = {
    audioProcessor: null,
    wsClient: null,
    noiseDetector: null,
    frameCount: 0,
    isRunning: false,
    currentDisplayState: null, // Current displayed state ('speech' or 'no-speech')
    stateFrameCount: 0, // How many consecutive frames in the same state
    stateChangeThreshold: 3 // Require N consecutive frames before changing display
};

// DOM elements
const elements = {
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    statusIndicator: document.getElementById('indicatorImage'),
    statusText: document.getElementById('statusText'),
    confidenceText: document.getElementById('confidenceText'),
    connectionStatus: document.getElementById('connectionStatus'),
    frameCount: document.getElementById('frameCount'),
    logContainer: document.getElementById('logContainer')
};

/**
 * Initialize the application
 */
function init() {
    // Initialize components
    app.audioProcessor = new AudioProcessor(40); // 40ms frames
    app.noiseDetector = new NoiseDetector(4); // 4-frame moving average

    // Set up event listeners
    elements.startBtn.addEventListener('click', startDetection);
    elements.stopBtn.addEventListener('click', stopDetection);

    // Add initial log
    addLog('Application initialized', 'info');
}

/**
 * Start noise detection
 */
async function startDetection() {
    try {
        addLog('Starting noise detection...', 'info');

        // Disable start button
        elements.startBtn.disabled = true;

        // Initialize WebSocket connection
        // Uses Config.WEBSOCKET_URL (AWS if set, otherwise local mock)
        const wsUrl = Config.WEBSOCKET_URL;
        addLog(`Connecting to: ${wsUrl}`, 'info');
        app.wsClient = new WebSocketClient({ wsUrl });

        // Set up WebSocket callbacks
        app.wsClient.onConnected = onWebSocketConnected;
        app.wsClient.onDisconnected = onWebSocketDisconnected;
        app.wsClient.onNoiseDetection = onNoiseDetectionResult;
        app.wsClient.onError = onWebSocketError;

        // Connect to WebSocket (will work once mock backend is ready)
        try {
            await app.wsClient.connect();
        } catch (error) {
            addLog('WebSocket connection failed - running in demo mode', 'info');
            // Continue without WebSocket for demo purposes
        }

        // Start audio capture
        const audioInfo = await app.audioProcessor.start();
        addLog(`Audio capture started: ${audioInfo.sampleRate}Hz, ${audioInfo.frameSize}ms frames`, 'success');

        // Set up audio frame callback
        app.audioProcessor.onAudioFrame = onAudioFrame;

        // Update UI
        app.isRunning = true;
        elements.stopBtn.disabled = false;
        elements.statusText.textContent = 'Listening...';
        elements.statusIndicator.classList.add('processing');
        updateConnectionStatus();

    } catch (error) {
        addLog(`Error starting detection: ${error.message}`, 'error');
        elements.startBtn.disabled = false;
        console.error(error);
    }
}

/**
 * Stop noise detection
 */
function stopDetection() {
    addLog('Stopping noise detection...', 'info');

    // Stop audio processing
    if (app.audioProcessor) {
        app.audioProcessor.stop();
    }

    // Disconnect WebSocket
    if (app.wsClient) {
        app.wsClient.disconnect();
    }

    // Reset noise detector
    if (app.noiseDetector) {
        app.noiseDetector.reset();
    }

    // Reset state
    app.isRunning = false;
    app.frameCount = 0;
    app.currentDisplayState = null;
    app.stateFrameCount = 0;

    // Update UI
    elements.startBtn.disabled = false;
    elements.stopBtn.disabled = true;
    elements.statusText.textContent = 'Not Connected';
    elements.confidenceText.textContent = 'Confidence: --';
    elements.statusIndicator.classList.remove('processing', 'clean', 'noisy');
    elements.statusIndicator.src = '/assets/no_peech.png'; // Reset to no speech image
    elements.statusIndicator.style.opacity = '1';
    elements.frameCount.textContent = '0';
    updateConnectionStatus();

    addLog('Detection stopped', 'info');
}

/**
 * Handle audio frame from processor
 */
function onAudioFrame(frameData) {
    app.frameCount++;
    elements.frameCount.textContent = app.frameCount;

    // Send to WebSocket if connected
    if (app.wsClient && app.wsClient.isConnected) {
        app.wsClient.sendAudioFrame(frameData);
    } else {
        // Demo mode: simulate noise detection locally
        simulateNoiseDetection();
    }
}

/**
 * Handle noise detection result from backend
 */
function onNoiseDetectionResult(result) {
    // Apply temporal smoothing
    const smoothed = app.noiseDetector.addDetection(result.isNoisy, result.confidence);

    // Update UI (pass VAD probability if available)
    updateNoiseStatus(smoothed.isNoisy, smoothed.confidence, result.vad_probability);
}

/**
 * Update noise status in UI
 */
function updateNoiseStatus(isNoisy, confidence, vadProbability) {
    // Determine the desired state
    const desiredState = isNoisy ? 'no-speech' : 'speech';

    // Check if state has changed from what we're tracking
    if (app.currentDisplayState !== desiredState) {
        app.stateFrameCount++;

        // Only switch display if we've seen consistent state for threshold frames
        if (app.stateFrameCount >= app.stateChangeThreshold) {
            // Update the displayed state
            app.currentDisplayState = desiredState;
            app.stateFrameCount = 0;

            // Determine the new image source
            const newImageSrc = isNoisy ? '/assets/no_peech.png' : '/assets/speech.gif';
            const currentImageSrc = elements.statusIndicator.src;

            // Only update if the image needs to change
            if (!currentImageSrc.endsWith(newImageSrc)) {
                // Smooth transition: fade out, change source, fade in
                elements.statusIndicator.style.opacity = '0';

                setTimeout(() => {
                    elements.statusIndicator.src = newImageSrc;
                    elements.statusIndicator.style.opacity = '1';
                }, 200); // Half of the transition duration for smooth effect
            }

            // Update CSS classes for visual effects
            elements.statusIndicator.classList.remove('processing', 'clean', 'noisy');
            elements.statusIndicator.classList.add(isNoisy ? 'noisy' : 'clean');

            // Update text
            const statusLabel = isNoisy ? 'No Speech / Noise' : 'Speech Detected';
            elements.statusText.textContent = statusLabel;
        }
    } else {
        // State is same as display, reset counter
        app.stateFrameCount = 0;
    }

    // Always update confidence text (regardless of state changes)
    if (vadProbability !== undefined) {
        elements.confidenceText.textContent = `Speech Probability: ${(vadProbability * 100).toFixed(1)}%`;
    } else {
        elements.confidenceText.textContent = `Confidence: ${(confidence * 100).toFixed(1)}%`;
    }

    // Log significant changes
    if (app.frameCount % 50 === 0) {
        const statusLabel = isNoisy ? 'No Speech / Noise' : 'Speech Detected';
        const probText = vadProbability !== undefined ?
            `VAD: ${(vadProbability * 100).toFixed(1)}%` :
            `Conf: ${(confidence * 100).toFixed(1)}%`;
        addLog(`Frame ${app.frameCount}: ${statusLabel} (${probText})`, 'info');
    }
}

/**
 * Simulate noise detection for demo mode (when backend not available)
 */
function simulateNoiseDetection() {
    // Simple simulation: randomly detect noise
    // In production, this will be replaced by actual ML inference
    const isNoisy = Math.random() > 0.7;
    const confidence = 0.6 + Math.random() * 0.3;

    onNoiseDetectionResult({ isNoisy, confidence, timestamp: Date.now() });
}

/**
 * WebSocket event handlers
 */
function onWebSocketConnected() {
    addLog('Connected to backend', 'success');
    updateConnectionStatus();
}

function onWebSocketDisconnected() {
    addLog('Disconnected from backend', 'info');
    updateConnectionStatus();
}

function onWebSocketError(error) {
    addLog(`WebSocket error: ${error.message}`, 'error');
}

/**
 * Update connection status display
 */
function updateConnectionStatus() {
    if (app.wsClient && app.wsClient.isConnected) {
        elements.connectionStatus.textContent = 'Connected';
        elements.connectionStatus.style.color = '#28a745';
    } else if (app.isRunning) {
        elements.connectionStatus.textContent = 'Demo Mode';
        elements.connectionStatus.style.color = '#ffc107';
    } else {
        elements.connectionStatus.textContent = 'Disconnected';
        elements.connectionStatus.style.color = '#6c757d';
    }
}

/**
 * Add log entry to UI
 */
function addLog(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.textContent = `[${timestamp}] ${message}`;

    elements.logContainer.appendChild(logEntry);

    // Auto-scroll to bottom
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;

    // Limit log entries
    while (elements.logContainer.children.length > 100) {
        elements.logContainer.removeChild(elements.logContainer.firstChild);
    }

    // Also log to console
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
