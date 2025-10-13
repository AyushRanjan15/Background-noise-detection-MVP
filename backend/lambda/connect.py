"""
WebSocket Connect Handler
Manages new WebSocket connections and stores connection info in DynamoDB
"""

import json
import os
import time
import logging
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['CONNECTIONS_TABLE_NAME']
table = dynamodb.Table(table_name)


def handler(event, context):
    """
    Handle WebSocket $connect route
    """
    logger.info(f"Connect event: {json.dumps(event)}")

    connection_id = event['requestContext']['connectionId']

    try:
        # Store connection in DynamoDB
        ttl = int(time.time()) + 3600  # 1 hour TTL

        table.put_item(
            Item={
                'connectionId': connection_id,
                'connectedAt': int(time.time()),
                'ttl': ttl,
                'status': 'connected'
            }
        )

        logger.info(f"Connection {connection_id} stored successfully")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Connected successfully'})
        }

    except ClientError as e:
        logger.error(f"Error storing connection: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Failed to connect'})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }
