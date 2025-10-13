#!/bin/bash
set -e

# Deployment script for Background Noise Detection MVP
# Usage: ./deploy.sh [bootstrap|deploy|destroy]

PROFILE="personal"
REGION="ap-southeast-2"

echo "========================================="
echo "Background Noise Detection MVP Deployment"
echo "Profile: $PROFILE"
echo "Region: $REGION"
echo "========================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

case "$1" in
    bootstrap)
        echo "Bootstrapping CDK environment..."
        cdk bootstrap --profile $PROFILE --region $REGION
        ;;
    deploy)
        echo "Deploying stack..."
        cdk deploy --profile $PROFILE --require-approval never
        ;;
    destroy)
        echo "Destroying stack..."
        cdk destroy --profile $PROFILE --force
        ;;
    synth)
        echo "Synthesizing CloudFormation template..."
        cdk synth --profile $PROFILE
        ;;
    diff)
        echo "Showing changes..."
        cdk diff --profile $PROFILE
        ;;
    *)
        echo "Usage: $0 {bootstrap|deploy|destroy|synth|diff}"
        echo ""
        echo "Commands:"
        echo "  bootstrap  - Prepare AWS environment for CDK (run once)"
        echo "  deploy     - Deploy the stack to AWS"
        echo "  destroy    - Remove all resources"
        echo "  synth      - Generate CloudFormation template"
        echo "  diff       - Show changes before deploy"
        exit 1
        ;;
esac

echo "Done!"
