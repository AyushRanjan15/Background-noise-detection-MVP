/**
 * AudioProcessor - Handles microphone access and audio frame processing
 * Captures audio at 16kHz sample rate and chunks into 30-50ms frames
 */
class AudioProcessor {
    constructor(frameSize = 40) {
        this.frameSize = frameSize; // milliseconds
        this.sampleRate = 16000; // 16kHz as per spec
        this.audioContext = null;
        this.mediaStream = null;
        this.audioWorkletNode = null;
        this.source = null;
        this.isProcessing = false;
        this.onAudioFrame = null; // Callback for when audio frame is ready
        this.frameBuffer = [];
        this.samplesPerFrame = Math.floor((this.sampleRate * this.frameSize) / 1000);
    }

    /**
     * Initialize and start audio capture from microphone
     */
    async start() {
        try {
            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: this.sampleRate,
                    echoCancellation: true,
                    noiseSuppression: false, // We want to detect noise, not suppress it
                    autoGainControl: false
                }
            });

            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate
            });

            // Create media stream source
            this.source = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create script processor for audio processing
            // Using ScriptProcessor (deprecated but widely supported)
            // TODO: Migrate to AudioWorklet for better performance
            const bufferSize = 4096;
            this.processor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

            this.processor.onaudioprocess = (e) => {
                if (!this.isProcessing) return;

                const inputData = e.inputBuffer.getChannelData(0);
                this.processAudioData(inputData);
            };

            // Connect audio nodes
            this.source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            this.isProcessing = true;
            return {
                success: true,
                sampleRate: this.audioContext.sampleRate,
                frameSize: this.frameSize
            };

        } catch (error) {
            console.error('Error starting audio capture:', error);
            throw new Error(`Microphone access failed: ${error.message}`);
        }
    }

    /**
     * Process incoming audio data and create frames
     */
    processAudioData(audioData) {
        // Add samples to buffer
        for (let i = 0; i < audioData.length; i++) {
            this.frameBuffer.push(audioData[i]);

            // When we have enough samples for a frame, send it
            if (this.frameBuffer.length >= this.samplesPerFrame) {
                const frame = this.frameBuffer.slice(0, this.samplesPerFrame);
                this.frameBuffer = this.frameBuffer.slice(this.samplesPerFrame);

                // Convert to appropriate format and send
                if (this.onAudioFrame) {
                    this.onAudioFrame(this.prepareFrame(frame));
                }
            }
        }
    }

    /**
     * Prepare audio frame for transmission
     * Converts Float32Array to base64 encoded string
     */
    prepareFrame(frameData) {
        // Convert Float32Array to Int16Array (16-bit PCM)
        const int16Array = new Int16Array(frameData.length);
        for (let i = 0; i < frameData.length; i++) {
            // Convert from [-1, 1] to [-32768, 32767]
            const s = Math.max(-1, Math.min(1, frameData[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        // Convert to base64 for transmission
        const uint8Array = new Uint8Array(int16Array.buffer);
        const base64 = btoa(String.fromCharCode.apply(null, uint8Array));

        return {
            audio: base64,
            sampleRate: this.sampleRate,
            samples: frameData.length,
            timestamp: Date.now()
        };
    }

    /**
     * Stop audio capture and cleanup resources
     */
    stop() {
        this.isProcessing = false;

        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }

        if (this.source) {
            this.source.disconnect();
            this.source = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        this.frameBuffer = [];
    }

    /**
     * Get current audio processing stats
     */
    getStats() {
        return {
            isProcessing: this.isProcessing,
            sampleRate: this.sampleRate,
            frameSize: this.frameSize,
            samplesPerFrame: this.samplesPerFrame,
            bufferSize: this.frameBuffer.length
        };
    }
}
