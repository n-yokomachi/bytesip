"""Configuration for ByteSip News Fetcher.

This module provides configuration for DynamoDB and external API access,
supporting both local development and AWS deployment.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError


@dataclass
class DynamoDBConfig:
    """DynamoDB configuration.

    Attributes:
        table_name: Name of the DynamoDB table
        endpoint_url: Custom endpoint URL (for DynamoDB Local)
        region_name: AWS region
    """

    table_name: str
    endpoint_url: str | None
    region_name: str


@dataclass
class ExternalAPIConfig:
    """External API configuration.

    Attributes:
        qiita_access_token: Qiita API access token
        github_access_token: GitHub Personal Access Token
    """

    qiita_access_token: str | None
    github_access_token: str | None


def get_dynamodb_config() -> DynamoDBConfig:
    """Get DynamoDB configuration from environment variables.

    Environment Variables:
        DYNAMODB_TABLE_NAME: Table name (required)
        DYNAMODB_ENDPOINT_URL: Custom endpoint (for local development)
        AWS_REGION: AWS region (required)

    Returns:
        DynamoDBConfig instance
    """
    return DynamoDBConfig(
        table_name=os.getenv("DYNAMODB_TABLE_NAME", ""),
        endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION", ""),
    )


@lru_cache(maxsize=10)
def _get_secret(secret_name: str) -> str | None:
    """Get secret value from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret in Secrets Manager

    Returns:
        Secret value or None if not found
    """
    region = os.getenv("AWS_REGION", "")
    if not region:
        return None

    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response.get("SecretString")
    except ClientError:
        return None


def get_external_api_config() -> ExternalAPIConfig:
    """Get external API configuration.

    Supports two modes:
    1. Direct environment variables (local development):
       - QIITA_ACCESS_TOKEN
       - GITHUB_ACCESS_TOKEN
    2. Secrets Manager (Lambda deployment):
       - QIITA_SECRET_NAME → reads from Secrets Manager
       - GITHUB_SECRET_NAME → reads from Secrets Manager

    Returns:
        ExternalAPIConfig instance
    """
    # Try direct environment variables first (local development)
    qiita_token = os.getenv("QIITA_ACCESS_TOKEN")
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")

    # If not set, try Secrets Manager (Lambda deployment)
    if not qiita_token:
        qiita_secret_name = os.getenv("QIITA_SECRET_NAME")
        if qiita_secret_name:
            qiita_token = _get_secret(qiita_secret_name)

    if not github_token:
        github_secret_name = os.getenv("GITHUB_SECRET_NAME")
        if github_secret_name:
            github_token = _get_secret(github_secret_name)

    return ExternalAPIConfig(
        qiita_access_token=qiita_token,
        github_access_token=github_token,
    )


# Constants for DynamoDB schema
DYNAMODB_PK_PREFIX = "SOURCE#"
DYNAMODB_SK_ITEM_PREFIX = "ITEM#"
DYNAMODB_SK_META = "META"

# Cache settings
CACHE_TTL_SECONDS = 86400  # 24 hours
MAX_ITEMS_PER_SOURCE = 30
