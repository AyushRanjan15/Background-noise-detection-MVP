from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class NoiseDetectionStack(Stack):
    """
    Background Noise Detection Stack - Simplified MVP Architecture

    Components:
    - API Gateway WebSocket for bidirectional communication
    - Lambda functions for connection management and audio processing
    - DynamoDB for session tracking
    - CloudWatch for logging

    No VPC/EFS - Using S3 or Lambda Layer for model storage
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ========================================
        # DynamoDB Table for Session Tracking
        # ========================================
        connections_table = dynamodb.Table(
            self,
            "ConnectionsTable",
            partition_key=dynamodb.Attribute(
                name="connectionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For MVP - delete on stack destroy
            time_to_live_attribute="ttl",  # Auto-cleanup old connections
        )

        # ========================================
        # Lambda Execution Role
        # ========================================
        lambda_role = iam.Role(
            self,
            "NoiseDetectionLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Grant DynamoDB permissions
        connections_table.grant_read_write_data(lambda_role)

        # ========================================
        # Lambda Layer for Model
        # ========================================
        vad_model_layer = _lambda.LayerVersion(
            self,
            "VadModelLayer",
            code=_lambda.Code.from_asset("ten-vad-layer.zip"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="TEN VAD ONNX model with onnxruntime and librosa",
        )

        # ========================================
        # Lambda Functions
        # ========================================

        # Common environment variables
        lambda_environment = {
            "CONNECTIONS_TABLE_NAME": connections_table.table_name,
            "LOG_LEVEL": "INFO",
        }

        # Connect Handler - Manages new WebSocket connections
        connect_handler = _lambda.Function(
            self,
            "ConnectHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="connect.handler",
            code=_lambda.Code.from_asset("../../backend/lambda"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=lambda_environment,
            role=lambda_role,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Disconnect Handler - Cleanup when client disconnects
        disconnect_handler = _lambda.Function(
            self,
            "DisconnectHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="disconnect.handler",
            code=_lambda.Code.from_asset("../../backend/lambda"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=lambda_environment,
            role=lambda_role,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Message Handler - Processes audio frames and runs inference
        message_handler = _lambda.Function(
            self,
            "MessageHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="message.handler",
            code=_lambda.Code.from_asset("../../backend/lambda"),
            timeout=Duration.seconds(60),  # Longer for model inference
            memory_size=1024,  # More memory for ML inference with onnxruntime
            environment=lambda_environment,
            role=lambda_role,
            layers=[vad_model_layer],  # Attach VAD model layer
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # ========================================
        # API Gateway WebSocket
        # ========================================

        # Create WebSocket API
        web_socket_api = apigwv2.CfnApi(
            self,
            "NoiseDetectionWebSocketAPI",
            name="NoiseDetectionWebSocketAPI",
            protocol_type="WEBSOCKET",
            route_selection_expression="$request.body.action",
            description="WebSocket API for real-time noise detection",
        )

        # Create integrations for Lambda functions
        connect_integration = apigwv2.CfnIntegration(
            self,
            "ConnectIntegration",
            api_id=web_socket_api.ref,
            integration_type="AWS_PROXY",
            integration_uri=f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{connect_handler.function_arn}/invocations",
        )

        disconnect_integration = apigwv2.CfnIntegration(
            self,
            "DisconnectIntegration",
            api_id=web_socket_api.ref,
            integration_type="AWS_PROXY",
            integration_uri=f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{disconnect_handler.function_arn}/invocations",
        )

        message_integration = apigwv2.CfnIntegration(
            self,
            "MessageIntegration",
            api_id=web_socket_api.ref,
            integration_type="AWS_PROXY",
            integration_uri=f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{message_handler.function_arn}/invocations",
        )

        # Create routes
        connect_route = apigwv2.CfnRoute(
            self,
            "ConnectRoute",
            api_id=web_socket_api.ref,
            route_key="$connect",
            authorization_type="NONE",
            target=f"integrations/{connect_integration.ref}",
        )

        disconnect_route = apigwv2.CfnRoute(
            self,
            "DisconnectRoute",
            api_id=web_socket_api.ref,
            route_key="$disconnect",
            target=f"integrations/{disconnect_integration.ref}",
        )

        default_route = apigwv2.CfnRoute(
            self,
            "DefaultRoute",
            api_id=web_socket_api.ref,
            route_key="$default",
            target=f"integrations/{message_integration.ref}",
        )

        # Create deployment
        deployment = apigwv2.CfnDeployment(
            self,
            "Deployment",
            api_id=web_socket_api.ref,
        )
        deployment.add_dependency(connect_route)
        deployment.add_dependency(disconnect_route)
        deployment.add_dependency(default_route)

        # Create stage
        stage = apigwv2.CfnStage(
            self,
            "ProdStage",
            api_id=web_socket_api.ref,
            stage_name="prod",
            deployment_id=deployment.ref,
            description="Production stage",
        )

        # Grant API Gateway permission to invoke Lambda functions
        connect_handler.add_permission(
            "ApiGatewayInvokeConnect",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{web_socket_api.ref}/*",
        )

        disconnect_handler.add_permission(
            "ApiGatewayInvokeDisconnect",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{web_socket_api.ref}/*",
        )

        message_handler.add_permission(
            "ApiGatewayInvokeMessage",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{web_socket_api.ref}/*",
        )

        # Grant Lambda permission to post to connections (for sending messages back)
        message_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["execute-api:ManageConnections"],
                resources=[
                    f"arn:aws:execute-api:{self.region}:{self.account}:{web_socket_api.ref}/*"
                ],
            )
        )

        # ========================================
        # Outputs
        # ========================================
        from aws_cdk import CfnOutput

        CfnOutput(
            self,
            "WebSocketURL",
            value=f"wss://{web_socket_api.ref}.execute-api.{self.region}.amazonaws.com/prod",
            description="WebSocket API URL for frontend client",
        )

        CfnOutput(
            self,
            "ConnectionsTableName",
            value=connections_table.table_name,
            description="DynamoDB table for connection tracking",
        )
