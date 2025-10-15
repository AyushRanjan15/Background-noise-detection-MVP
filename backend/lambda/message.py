"""
WebSocket Message Handler
Processes incoming audio frames and runs noise detection inference
"""

import json
import os
import logging
import boto3
import base64
import time
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
apigateway_client = boto3.client('apigatewaymanagementapi', endpoint_url=None)

table_name = os.environ['CONNECTIONS_TABLE_NAME']
table = dynamodb.Table(table_name)

# TODO: Load ML model when available
# Model loading will be added once model is ready
# Options: S3 download or Lambda Layer
model = None


def load_model():
    """
    Load ML model for noise detection
    This will be implemented based on chosen storage option (S3 or Lambda Layer)
    """
    global model

    # Placeholder for model loading
    # Option 1: Load from S3
    # s3 = boto3.client('s3')
    # model_bucket = os.environ.get('MODEL_BUCKET')
    # model_key = os.environ.get('MODEL_KEY')
    # s3.download_file(model_bucket, model_key, '/tmp/model.pkl')
    # model = load_model_from_file('/tmp/model.pkl')

    # Option 2: Load from Lambda Layer
    # model = load_model_from_file('/opt/model/noise_detector.pkl')

    logger.info("Model loading not yet implemented - using mock inference")
    return None


def mock_inference(audio_data):
    """
    Mock inference for testing without model
    Replace this with actual model inference once model is available
    """
    import random

    # Simulate processing time
    time.sleep(0.01)

    # Random noise detection for demo
    is_noisy = random.random() > 0.7
    confidence = 0.6 + random.random() * 0.3 if is_noisy else 0.7 + random.random() * 0.3

    return {
        'isNoisy': is_noisy,
        'confidence': round(confidence, 3)
    }


def run_inference(audio_data):
    """
    Run Silero VAD inference on audio frame
    """
    try:
        # Import Silero VAD module
        from vad_silero import run_vad_inference

        # Run VAD inference
        result = run_vad_inference(audio_data)

        # Convert VAD output to our format
        return {
            'isNoisy': not result['is_speech'],  # Invert: no speech = "noisy" (silence/noise)
            'vad_probability': result['vad_probability'],
            'confidence': result['vad_probability']
        }

    except Exception as e:
        logger.error(f"Silero VAD inference failed, using mock: {e}", exc_info=True)
        # Fallback to mock if VAD fails
        return mock_inference(audio_data)


def send_message(connection_id, endpoint_url, message):
    """
    Send message back to client via WebSocket
    """
    try:
        apigateway_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=endpoint_url
        )

        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )

        return True

    except apigateway_client.exceptions.GoneException:
        logger.warning(f"Connection {connection_id} is gone")
        # Clean up stale connection
        try:
            table.delete_item(Key={'connectionId': connection_id})
        except Exception as e:
            logger.error(f"Error cleaning up connection: {e}")
        return False

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False


def handler(event, context):
    """
    Handle WebSocket $default route (all messages)
    """
    logger.info(f"Message event received")

    connection_id = event['requestContext']['connectionId']
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']
    endpoint_url = f"https://{domain_name}/{stage}"

    try:
        # Parse message body
        body = json.loads(event.get('body', '{}'))
        message_type = body.get('type')

        logger.info(f"Message type: {message_type} from connection {connection_id}")

        if message_type == 'audio_frame':
            # Process audio frame
            audio_data = body.get('data', {})

            # Run inference
            result = run_inference(audio_data)

            # Send result back to client
            response_message = {
                'type': 'noise_detection',
                'isNoisy': result['isNoisy'],
                'confidence': result['confidence'],
                'vad_probability': result.get('vad_probability', result['confidence']),
                'timestamp': int(time.time() * 1000)
            }

            send_message(connection_id, endpoint_url, response_message)

        elif message_type == 'ping':
            # Respond to heartbeat
            send_message(connection_id, endpoint_url, {
                'type': 'pong',
                'timestamp': int(time.time() * 1000)
            })

        else:
            logger.warning(f"Unknown message type: {message_type}")
            send_message(connection_id, endpoint_url, {
                'type': 'error',
                'error': f'Unknown message type: {message_type}'
            })

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Message processed'})
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Invalid JSON'})
        }

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

        # Try to send error back to client
        try:
            send_message(connection_id, endpoint_url, {
                'type': 'error',
                'error': 'Internal server error'
            })
        except:
            pass

        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }
