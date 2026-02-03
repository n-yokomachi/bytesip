#!/usr/bin/env python3
"""Create AgentCore Gateway target for fetch_news Lambda function.

Usage:
    cd agent && uv run python ../scripts/create_gateway_target.py

Prerequisites:
    - Gateway must be created first using:
      agentcore gateway create-mcp-gateway --region ap-northeast-1 --name bytesip-gateway
    - Lambda function must be deployed via CDK
"""

import json
import os
import sys

import boto3

# Configuration - update these values for your environment
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "765653276628")

# Gateway settings (update gateway_id after creating gateway)
GATEWAY_ID = os.environ.get("BYTESIP_GATEWAY_ID", "bytesip-gateway-b8uvvqzk4p")
GATEWAY_ARN = f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:gateway/{GATEWAY_ID}"
GATEWAY_URL = f"https://{GATEWAY_ID}.gateway.bedrock-agentcore.{REGION}.amazonaws.com/mcp"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/AgentCoreGatewayExecutionRole"

# Lambda settings
ENVIRONMENT = os.environ.get("BYTESIP_ENVIRONMENT", "development")
LAMBDA_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:bytesip-news-fetcher-{ENVIRONMENT}"

# Tool schema for fetch_news
TOOL_SCHEMA = {
    "inlinePayload": [
        {
            "name": "fetch_news",
            "description": "Fetch IT/AI news from Qiita, Zenn, and GitHub. Results are cached for 24 hours.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sources to fetch from: qiita, zenn, github. If not specified, fetches from all.",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technology tags to filter by (e.g., python, rust)",
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "If true, bypass cache and fetch fresh data",
                    },
                },
            },
        }
    ]
}


def add_lambda_invoke_permission():
    """Add permission for Gateway role to invoke the Lambda function."""
    lambda_client = boto3.client("lambda", region_name=REGION)

    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_ARN,
            StatementId="AgentCoreGatewayInvoke",
            Action="lambda:InvokeFunction",
            Principal="bedrock-agentcore.amazonaws.com",
            SourceArn=GATEWAY_ARN,
        )
        print("✅ Added Lambda invoke permission for Gateway")
    except lambda_client.exceptions.ResourceConflictException:
        print("ℹ️ Lambda permission already exists")
    except Exception as e:
        print(f"⚠️ Could not add Lambda permission: {e}")


def main():
    """Create Gateway target for fetch_news Lambda."""
    print(f"Creating Gateway target for: {LAMBDA_ARN}")
    print(f"Gateway: {GATEWAY_ID}")

    # Add Lambda invoke permission first
    add_lambda_invoke_permission()

    # Create the target configuration
    target_config = {
        "mcp": {
            "lambda": {
                "lambdaArn": LAMBDA_ARN,
                "toolSchema": TOOL_SCHEMA,
            }
        }
    }

    credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    try:
        response = client.create_gateway_target(
            gatewayIdentifier=GATEWAY_ID,
            name="bytesip-fetch-news",
            description="Lambda target for fetching IT/AI news from Qiita, Zenn, and GitHub",
            targetConfiguration=target_config,
            credentialProviderConfigurations=credential_config,
        )
        print("✅ Gateway target created successfully!")
        print(json.dumps(response, indent=2, default=str))
    except client.exceptions.ConflictException:
        print("ℹ️ Gateway target already exists")
    except Exception as e:
        print(f"❌ Failed to create Gateway target: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
