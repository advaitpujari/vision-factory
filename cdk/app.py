#!/usr/bin/env python3
"""CDK App entry-point for the Vision Factory monitoring dashboard."""

import os
import aws_cdk as cdk
from dashboard_stack import VisionFactoryDashboardStack

app = cdk.App()

VisionFactoryDashboardStack(
    app,
    "VisionFactoryDashboard",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
    # Pass the Lambda function name via context or env var
    lambda_function_name=os.environ.get("LAMBDA_FUNCTION_NAME", "vision-factory"),
)

app.synth()
