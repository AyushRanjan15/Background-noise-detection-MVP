"""
WebSocket Disconnect Handler
Handles disconnections and cleans up DynamoDB entries
"""

import json
import os
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
    Handle WebSocket $disconnect route
    """
    logger.info(f"Disconnect event: {json.dumps(event)}")

    connection_id = event['requestContext']['connectionId']

    try:
        # Remove connection from DynamoDB
        table.delete_item(
            Key={
                'connectionId': connection_id
            }
        )

        logger.info(f"Connection {connection_id} removed successfully")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Disconnected successfully'})
        }

    except ClientError as e:
        logger.error(f"Error removing connection: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Failed to disconnect'})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }
