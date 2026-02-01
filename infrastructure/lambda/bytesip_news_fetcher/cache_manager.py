"""Cache Manager for ByteSip News Fetcher.

This module provides DynamoDB-based caching for news items
with TTL support and per-source item limits.
"""

import time
from typing import Any

from boto3.dynamodb.conditions import Key

from .config import (
    CACHE_TTL_SECONDS,
    DYNAMODB_PK_PREFIX,
    DYNAMODB_SK_ITEM_PREFIX,
    MAX_ITEMS_PER_SOURCE,
)
from .models import NewsItem, SourceType


class CacheManager:
    """Manages DynamoDB cache for news items.

    Provides methods to get, set, and invalidate cached news items
    with automatic TTL management and per-source limits.
    """

    def __init__(self, table: Any) -> None:
        """Initialize CacheManager with a DynamoDB table.

        Args:
            table: boto3 DynamoDB Table resource
        """
        self._table = table

    def get(self, source: SourceType) -> list[NewsItem] | None:
        """Retrieve cached news items for a source.

        Args:
            source: The news source (qiita, zenn, github)

        Returns:
            List of NewsItem if valid cache exists, None otherwise.
            Expired items (past TTL) are filtered out.
        """
        pk = f"{DYNAMODB_PK_PREFIX}{source}"

        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk)
            & Key("SK").begins_with(DYNAMODB_SK_ITEM_PREFIX)
        )

        items = response.get("Items", [])
        if not items:
            return None

        current_time = int(time.time())
        valid_items = []

        for item in items:
            if item.get("ttl", 0) > current_time:
                valid_items.append(
                    NewsItem(
                        id=item["id"],
                        title=item["title"],
                        url=item["url"],
                        summary=item["summary"],
                        tags=item.get("tags", []),
                        source=item["source"],
                    )
                )

        return valid_items if valid_items else None

    def set(self, source: SourceType, items: list[NewsItem]) -> None:
        """Store news items in cache.

        Args:
            source: The news source (qiita, zenn, github)
            items: List of NewsItem to cache (limited to MAX_ITEMS_PER_SOURCE)
        """
        pk = f"{DYNAMODB_PK_PREFIX}{source}"
        ttl = int(time.time()) + CACHE_TTL_SECONDS

        # Limit items to MAX_ITEMS_PER_SOURCE
        items_to_store = items[:MAX_ITEMS_PER_SOURCE]

        for item in items_to_store:
            sk = f"{DYNAMODB_SK_ITEM_PREFIX}{item.id}"

            self._table.put_item(
                Item={
                    "PK": pk,
                    "SK": sk,
                    "id": item.id,
                    "title": item.title,
                    "url": item.url,
                    "summary": item.summary,
                    "tags": item.tags,
                    "source": item.source,
                    "ttl": ttl,
                }
            )

    def invalidate(self, source: SourceType) -> None:
        """Remove all cached items for a source.

        Args:
            source: The news source (qiita, zenn, github)
        """
        pk = f"{DYNAMODB_PK_PREFIX}{source}"

        response = self._table.query(
            KeyConditionExpression=Key("PK").eq(pk)
            & Key("SK").begins_with(DYNAMODB_SK_ITEM_PREFIX),
            ProjectionExpression="PK, SK",
        )

        items = response.get("Items", [])

        for item in items:
            self._table.delete_item(
                Key={
                    "PK": item["PK"],
                    "SK": item["SK"],
                }
            )
