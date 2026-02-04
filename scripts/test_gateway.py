#!/usr/bin/env python3
"""Test AgentCore Gateway connection with fetch_news tool.

Usage:
    cd agent && uv run python ../scripts/test_gateway.py

Prerequisites:
    - Gateway and target must be created
    - Cognito credentials must be available
"""

import json
import os

import boto3
import requests

# Configuration
REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
GATEWAY_ID = os.environ.get("BYTESIP_GATEWAY_ID", "bytesip-gateway-b8uvvqzk4p")
GATEWAY_URL = f"https://{GATEWAY_ID}.gateway.bedrock-agentcore.{REGION}.amazonaws.com/mcp"

# Cognito settings (from gateway creation)
USER_POOL_ID = "ap-northeast-1_SXo8DF8U6"
CLIENT_ID = "2fufk8ch1pfjtoe3154a73td2h"


def get_cognito_token():
    """Get OAuth token from Cognito for M2M authentication."""
    cognito = boto3.client("cognito-idp", region_name=REGION)

    # Get the client secret
    response = cognito.describe_user_pool_client(
        UserPoolId=USER_POOL_ID,
        ClientId=CLIENT_ID,
    )
    client_secret = response["UserPoolClient"].get("ClientSecret")

    if not client_secret:
        print("⚠️ Client secret not found. Gateway may need different auth setup.")
        return None

    # Get token using client credentials flow
    token_url = f"https://agentcore-2cc7dd74.auth.{REGION}.amazoncognito.com/oauth2/token"
    # Scope uses the resource server identifier, not gateway ID
    scope = "bytesip-gateway/invoke"

    import base64

    auth_string = f"{CLIENT_ID}:{client_secret}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_bytes}",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": scope,
    }

    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Failed to get token: {response.text}")
        return None


def call_gateway_tool(token: str, tool_name: str, arguments: dict):
    """Call a tool via the Gateway MCP endpoint."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # MCP tools/call request format
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
        "id": 1,
    }

    response = requests.post(GATEWAY_URL, headers=headers, json=payload)
    return response.json()


def list_gateway_tools(token: str):
    """List available tools from the Gateway."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # MCP tools/list request format
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1,
    }

    response = requests.post(GATEWAY_URL, headers=headers, json=payload)
    return response.json()


def main():
    """Test Gateway with fetch_news tool."""
    print(f"Testing Gateway: {GATEWAY_URL}")
    print()

    # Get authentication token
    print("1. Getting Cognito token...")
    token = get_cognito_token()
    if not token:
        print("❌ Could not get authentication token")
        return

    print("✅ Got authentication token")
    print()

    # List available tools
    print("2. Listing available tools...")
    tools_result = list_gateway_tools(token)
    print(json.dumps(tools_result, indent=2, ensure_ascii=False))
    print()

    # Find the fetch_news tool name
    tools = tools_result.get("result", {}).get("tools", [])
    fetch_news_tool = None
    for tool in tools:
        if "fetch_news" in tool.get("name", ""):
            fetch_news_tool = tool["name"]
            break

    if not fetch_news_tool:
        print("❌ fetch_news tool not found")
        return

    print(f"3. Calling tool: {fetch_news_tool}...")
    result = call_gateway_tool(
        token=token,
        tool_name=fetch_news_tool,
        arguments={"sources": ["zenn"], "force_refresh": True},
    )

    print("Response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
