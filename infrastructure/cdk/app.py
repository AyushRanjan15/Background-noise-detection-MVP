#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.noise_detection_stack import NoiseDetectionStack


app = cdk.App()

# Configure for ap-southeast-2 (Sydney) region
# Use with: cdk deploy --profile personal
NoiseDetectionStack(
    app,
    "NoiseDetectionStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='ap-southeast-2'
    ),
    description="Background Noise Detection MVP - Simplified Architecture"
)

app.synth()
