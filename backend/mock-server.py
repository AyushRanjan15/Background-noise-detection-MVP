#!/usr/bin/env python3
"""
Mock WebSocket server for local development and testing
Simulates the Lambda + API Gateway WebSocket behavior
"""

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Set

import websockets
from websockets.server import WebSocketServerProtocol

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track connected clients
connected_clients: Set[WebSocketServerProtocol] = set()

class MockNoiseDetector:
    """
    Mock ML model for noise detection
    In production, this will be replaced with actual trained model
    """

    def __init__(self):
        self.frame_count = 0
        self.noise_probability = 0.3  # 30% chance of detecting noise

    def predict(self, audio_data: dict) -> dict:
        """
        Simulate noise detection inference
        Returns classification result with confidence score
        """
        self.frame_count += 1

        # Simulate processing delay
        # In production, this will be actual model inference time

        # Random noise detection for demo
        is_noisy = random.random() < self.noise_probability

        # Confidence score (higher when clear signal)
        if is_noisy:
            confidence = 0.6 + random.random() * 0.3  # 0.6-0.9 for noisy
        else:
            confidence = 0.7 + random.random() * 0.3  # 0.7-1.0 for clean

        return {
            'type': 'noise_detection',
            'isNoisy': is_noisy,
            'confidence': round(confidence, 3),
            'timestamp': datetime.now().isoformat(),
            'frameNumber': self.frame_count
        }

async def handle_client(websocket: WebSocketServerProtocol, path: str):
    """
    Handle individual client connection
    """
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"Client connected: {client_id}")

    # Add to connected clients
    connected_clients.add(websocket)

    # Initialize mock detector for this session
    detector = MockNoiseDetector()

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            'type': 'connected',
            'message': 'Connected to mock backend',
            'timestamp': datetime.now().isoformat()
        }))

        # Handle incoming messages
        async for message in websocket:
            try:
                data = json.loads(message)

                if data.get('type') == 'audio_frame':
                    # Process audio frame
                    audio_data = data.get('data', {})

                    # Run mock inference
                    result = detector.predict(audio_data)

                    # Send back detection result
                    await websocket.send(json.dumps(result))

                elif data.get('type') == 'ping':
                    # Respond to heartbeat
                    await websocket.send(json.dumps({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }))

                else:
                    logger.warning(f"Unknown message type: {data.get('type')}")

            except json.JSONDecodeError:
                logger.error("Failed to parse message as JSON")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'error': 'Invalid JSON format'
                }))

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'error': str(e)
                }))

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_id}")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        # Remove from connected clients
        connected_clients.discard(websocket)
        logger.info(f"Cleaned up connection: {client_id}")

async def main():
    """
    Start the WebSocket server
    """
    host = 'localhost'
    port = 8080

    logger.info(f"Starting mock WebSocket server on ws://{host}:{port}")

    async with websockets.serve(handle_client, host, port):
        logger.info("Server started successfully")
        logger.info(f"Connected clients will be tracked: {len(connected_clients)}")

        # Keep server running
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
