# CDK Deployment Guide

## Prerequisites

1. AWS CLI configured with `personal` profile
2. AWS CDK installed (`npm install -g aws-cdk`)
3. Python 3.11+
4. Virtual environment activated

## Setup

1. Install Python dependencies:
```bash
cd infrastructure/cdk
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Deployment Steps

### 1. Bootstrap (First time only)
Bootstrap your AWS environment for CDK:
```bash
./deploy.sh bootstrap
```

This creates an S3 bucket and other resources CDK needs to deploy.

### 2. Synthesize (Optional - Check CloudFormation)
Generate CloudFormation template without deploying:
```bash
./deploy.sh synth
```

### 3. Deploy
Deploy the stack to AWS:
```bash
./deploy.sh deploy
```

This will create:
- API Gateway WebSocket API
- 3 Lambda functions (connect, disconnect, message)
- DynamoDB table for connection tracking
- IAM roles and permissions
- CloudWatch log groups

**Deployment time**: ~3-5 minutes

### 4. Get WebSocket URL
After deployment, the WebSocket URL will be shown in outputs:
```
Outputs:
NoiseDetectionStack.WebSocketURL = wss://xxxxx.execute-api.ap-southeast-2.amazonaws.com/prod
```

Copy this URL and update your frontend: `frontend/src/app.js` line 33.

### 5. Destroy (Cleanup)
Remove all resources:
```bash
./deploy.sh destroy
```

## Stack Components

### API Gateway WebSocket
- **Routes**: `$connect`, `$disconnect`, `$default`
- **Stage**: prod
- **Region**: ap-southeast-2 (Sydney)

### Lambda Functions
1. **ConnectHandler** (256MB, 30s timeout)
   - Manages new connections
   - Stores connectionId in DynamoDB

2. **DisconnectHandler** (256MB, 30s timeout)
   - Cleanup on disconnect
   - Removes connectionId from DynamoDB

3. **MessageHandler** (512MB, 60s timeout)
   - Processes audio frames
   - Runs noise detection inference
   - Sends results back via WebSocket

### DynamoDB Table
- **Table**: ConnectionsTable
- **Key**: connectionId (String)
- **TTL**: 1 hour auto-cleanup
- **Billing**: Pay-per-request

## Costs (Estimated)

### Free Tier (First 12 months)
- Lambda: 1M requests/month free
- API Gateway: 1M messages free
- DynamoDB: 25GB storage + 25 write/read units free
- CloudWatch: 5GB logs free

### Beyond Free Tier (Light usage)
- API Gateway: $0.001 per message
- Lambda: $0.0000002 per request + duration
- DynamoDB: ~$1-2/month
- **Total**: ~$2-5/month for MVP usage

## Troubleshooting

### Bootstrap fails
```bash
# Check AWS credentials
aws sts get-caller-identity --profile personal

# Ensure region is correct
aws configure get region --profile personal
```

### Deploy fails - "No such file or directory: backend/lambda"
Ensure Lambda functions exist at `../../backend/lambda/` relative to CDK directory.

### WebSocket connection fails
1. Check CloudWatch logs for Lambda errors
2. Verify API Gateway stage is deployed
3. Test with wscat: `wscat -c wss://your-url`

## Next Steps

1. Deploy stack
2. Update frontend with WebSocket URL
3. Test connection
4. Add ML model (when ready)
5. Redeploy with model loading logic
