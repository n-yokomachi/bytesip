#!/usr/bin/env python3
"""ByteSip CDK Application Entry Point."""

import aws_cdk as cdk

from bytesip_stack.bytesip_stack import ByteSipStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    region=app.node.try_get_context("region") or "ap-northeast-1"
)

# Get environment name from context (default: development)
environment = app.node.try_get_context("environment") or "development"

ByteSipStack(
    app,
    f"ByteSipStack-{environment}",
    environment=environment,
    env=env,
)

app.synth()
