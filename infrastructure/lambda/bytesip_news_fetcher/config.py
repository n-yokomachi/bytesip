"""Configuration for ByteSip News Fetcher.

This module provides configuration for DynamoDB and external API access,
supporting both local development and AWS deployment.
"""

import os
from dataclasses import dataclass


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


def get_external_api_config() -> ExternalAPIConfig:
    """Get external API configuration from environment variables.

    Environment Variables:
        QIITA_ACCESS_TOKEN: Qiita API access token
        GITHUB_ACCESS_TOKEN: GitHub Personal Access Token

    Returns:
        ExternalAPIConfig instance
    """
    return ExternalAPIConfig(
        qiita_access_token=os.getenv("QIITA_ACCESS_TOKEN"),
        github_access_token=os.getenv("GITHUB_ACCESS_TOKEN"),
    )


# Constants for DynamoDB schema
DYNAMODB_PK_PREFIX = "SOURCE#"
DYNAMODB_SK_ITEM_PREFIX = "ITEM#"
DYNAMODB_SK_META = "META"

# Cache settings
CACHE_TTL_SECONDS = 86400  # 24 hours
MAX_ITEMS_PER_SOURCE = 30
