/**
 * NoiseDetector - Implements temporal smoothing with moving average
 * Reduces flicker in noise detection results
 */
class NoiseDetector {
    constructor(windowSize = 4) {
        this.windowSize = windowSize; // 3-5 frame moving average as per spec
        this.detectionHistory = [];
        this.confidenceHistory = [];
    }

    /**
     * Add new detection result and compute smoothed output
     * @param {boolean} isNoisy - Raw detection result
     * @param {number} confidence - Confidence score (0-1)
     * @returns {object} Smoothed detection result
     */
    addDetection(isNoisy, confidence) {
        // Add to history
        this.detectionHistory.push(isNoisy ? 1 : 0);
        this.confidenceHistory.push(confidence);

        // Maintain window size
        if (this.detectionHistory.length > this.windowSize) {
            this.detectionHistory.shift();
            this.confidenceHistory.shift();
        }

        // Compute moving average
        const avgDetection = this.detectionHistory.reduce((a, b) => a + b, 0) / this.detectionHistory.length;
        const avgConfidence = this.confidenceHistory.reduce((a, b) => a + b, 0) / this.confidenceHistory.length;

        // Threshold: If more than 50% of recent frames detected noise, classify as noisy
        const smoothedIsNoisy = avgDetection > 0.5;

        return {
            isNoisy: smoothedIsNoisy,
            confidence: avgConfidence,
            rawIsNoisy: isNoisy,
            rawConfidence: confidence,
            historySize: this.detectionHistory.length
        };
    }

    /**
     * Reset detection history
     */
    reset() {
        this.detectionHistory = [];
        this.confidenceHistory = [];
    }

    /**
     * Get current state
     */
    getState() {
        return {
            windowSize: this.windowSize,
            historySize: this.detectionHistory.length,
            detectionHistory: [...this.detectionHistory],
            confidenceHistory: [...this.confidenceHistory]
        };
    }
}
