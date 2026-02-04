#!/usr/bin/env python3
"""Setup permissions for AgentCore Runtime to invoke Lambda.

This script adds the necessary permissions for the ByteSip agent
running in AgentCore Runtime to invoke the news fetcher Lambda function.

Usage:
    python scripts/setup_agentcore_permissions.py

Prerequisites:
    - AWS CLI configured with appropriate credentials
    - Lambda function deployed via CDK
    - AgentCore agent deployed
"""

import os
import sys

import boto3
from botocore.exceptions import ClientError

# Configuration
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "765653276628")
ENVIRONMENT = os.environ.get("BYTESIP_ENVIRONMENT", "development")

LAMBDA_FUNCTION_NAME = f"bytesip-news-fetcher-{ENVIRONMENT}"
AGENTCORE_ROLE_NAME = f"AmazonBedrockAgentCoreSDKRuntime-{REGION}-4f761cb595"


def add_lambda_permission():
    """Add Lambda resource policy for AgentCore Runtime."""
    lambda_client = boto3.client("lambda", region_name=REGION)

    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId="AgentCoreRuntimeInvoke",
            Action="lambda:InvokeFunction",
            Principal="bedrock-agentcore.amazonaws.com",
            SourceArn=f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:runtime/*",
        )
        print(f"✅ Added Lambda permission for AgentCore Runtime")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceConflictException":
            print(f"ℹ️ Lambda permission already exists")
        else:
            print(f"❌ Failed to add Lambda permission: {e}")
            return False
    return True


def attach_iam_policy():
    """Attach Lambda invoke policy to AgentCore execution role."""
    iam_client = boto3.client("iam", region_name=REGION)

    try:
        iam_client.attach_role_policy(
            RoleName=AGENTCORE_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaRole",
        )
        print(f"✅ Attached AWSLambdaRole policy to {AGENTCORE_ROLE_NAME}")
    except ClientError as e:
        if "already attached" in str(e).lower():
            print(f"ℹ️ Policy already attached to role")
        else:
            print(f"❌ Failed to attach policy: {e}")
            return False
    return True


def main():
    """Setup all required permissions."""
    print(f"Setting up AgentCore permissions for {ENVIRONMENT} environment")
    print(f"Region: {REGION}")
    print(f"Lambda: {LAMBDA_FUNCTION_NAME}")
    print(f"Role: {AGENTCORE_ROLE_NAME}")
    print()

    success = True

    # Add Lambda resource policy
    print("1. Adding Lambda resource policy...")
    if not add_lambda_permission():
        success = False

    # Attach IAM policy
    print("2. Attaching IAM policy to execution role...")
    if not attach_iam_policy():
        success = False

    print()
    if success:
        print("✅ All permissions configured successfully!")
        print()
        print("Note: IAM policy changes may take a few minutes to propagate.")
    else:
        print("⚠️ Some permissions failed to configure. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
