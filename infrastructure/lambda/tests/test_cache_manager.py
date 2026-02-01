"""Tests for CacheManager.

TDD tests for DynamoDB cache management functionality.
"""

import time
from unittest.mock import MagicMock

from bytesip_news_fetcher.cache_manager import CacheManager
from bytesip_news_fetcher.config import (
    CACHE_TTL_SECONDS,
    MAX_ITEMS_PER_SOURCE,
)
from bytesip_news_fetcher.models import NewsItem


class TestCacheManagerGet:
    """Test CacheManager.get() method."""

    def test_get_returns_none_when_no_cache_exists(self) -> None:
        """Return None when no cache entry exists for the source."""
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}

        manager = CacheManager(mock_table)
        result = manager.get("qiita")

        assert result is None

    def test_get_returns_cached_items_when_valid(self) -> None:
        """Return cached items when TTL is still valid."""
        future_ttl = int(time.time()) + 3600  # 1 hour from now

        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "SOURCE#qiita",
                    "SK": "ITEM#qiita_abc123",
                    "id": "qiita_abc123",
                    "title": "Test Article",
                    "url": "https://qiita.com/test",
                    "summary": "Test summary",
                    "tags": ["python", "aws"],
                    "source": "qiita",
                    "ttl": future_ttl,
                }
            ]
        }

        manager = CacheManager(mock_table)
        result = manager.get("qiita")

        assert result is not None
        assert len(result) == 1
        assert result[0].id == "qiita_abc123"
        assert result[0].title == "Test Article"

    def test_get_filters_expired_items(self) -> None:
        """Filter out items with expired TTL."""
        past_ttl = int(time.time()) - 3600  # 1 hour ago
        future_ttl = int(time.time()) + 3600  # 1 hour from now

        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "SOURCE#qiita",
                    "SK": "ITEM#qiita_expired",
                    "id": "qiita_expired",
                    "title": "Expired Article",
                    "url": "https://qiita.com/expired",
                    "summary": "Expired",
                    "tags": [],
                    "source": "qiita",
                    "ttl": past_ttl,
                },
                {
                    "PK": "SOURCE#qiita",
                    "SK": "ITEM#qiita_valid",
                    "id": "qiita_valid",
                    "title": "Valid Article",
                    "url": "https://qiita.com/valid",
                    "summary": "Valid",
                    "tags": [],
                    "source": "qiita",
                    "ttl": future_ttl,
                },
            ]
        }

        manager = CacheManager(mock_table)
        result = manager.get("qiita")

        assert result is not None
        assert len(result) == 1
        assert result[0].id == "qiita_valid"

    def test_get_queries_with_correct_partition_key(self) -> None:
        """Verify query uses correct partition key format."""
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}

        manager = CacheManager(mock_table)
        manager.get("zenn")

        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert "KeyConditionExpression" in call_kwargs


class TestCacheManagerSet:
    """Test CacheManager.set() method."""

    def test_set_stores_items_in_dynamodb(self) -> None:
        """Verify items are stored with correct attributes."""
        mock_table = MagicMock()
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        manager = CacheManager(mock_table)
        items = [
            NewsItem(
                id="qiita_abc123",
                title="Test Article",
                url="https://qiita.com/test",
                summary="Test summary",
                tags=["python"],
                source="qiita",
            )
        ]

        manager.set("qiita", items)

        mock_batch.put_item.assert_called_once()
        call_kwargs = mock_batch.put_item.call_args[1]
        item = call_kwargs["Item"]

        assert item["PK"] == "SOURCE#qiita"
        assert item["SK"] == "ITEM#qiita_abc123"
        assert item["title"] == "Test Article"
        assert "ttl" in item

    def test_set_limits_items_to_max_per_source(self) -> None:
        """Only store up to MAX_ITEMS_PER_SOURCE items."""
        mock_table = MagicMock()
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        manager = CacheManager(mock_table)

        # Create more items than the limit
        items = [
            NewsItem(
                id=f"qiita_{i}",
                title=f"Article {i}",
                url=f"https://qiita.com/{i}",
                summary=f"Summary {i}",
                tags=[],
                source="qiita",
            )
            for i in range(MAX_ITEMS_PER_SOURCE + 10)
        ]

        manager.set("qiita", items)

        # Should only call put_item MAX_ITEMS_PER_SOURCE times
        assert mock_batch.put_item.call_count == MAX_ITEMS_PER_SOURCE

    def test_set_calculates_ttl_correctly(self) -> None:
        """TTL should be current time + CACHE_TTL_SECONDS."""
        mock_table = MagicMock()
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)

        manager = CacheManager(mock_table)
        items = [
            NewsItem(
                id="qiita_abc123",
                title="Test",
                url="https://qiita.com/test",
                summary="Test",
                tags=[],
                source="qiita",
            )
        ]

        before_time = int(time.time())
        manager.set("qiita", items)
        after_time = int(time.time())

        call_kwargs = mock_batch.put_item.call_args[1]
        ttl = call_kwargs["Item"]["ttl"]

        expected_min = before_time + CACHE_TTL_SECONDS
        expected_max = after_time + CACHE_TTL_SECONDS

        assert expected_min <= ttl <= expected_max


class TestCacheManagerInvalidate:
    """Test CacheManager.invalidate() method."""

    def test_invalidate_deletes_all_items_for_source(self) -> None:
        """Delete all cached items for the specified source."""
        mock_table = MagicMock()
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.return_value = {
            "Items": [
                {"PK": "SOURCE#qiita", "SK": "ITEM#qiita_1"},
                {"PK": "SOURCE#qiita", "SK": "ITEM#qiita_2"},
            ]
        }

        manager = CacheManager(mock_table)
        manager.invalidate("qiita")

        # Should query to find items, then delete each one via batch
        mock_table.query.assert_called_once()
        assert mock_batch.delete_item.call_count == 2

    def test_invalidate_does_nothing_when_no_cache(self) -> None:
        """Do nothing when no cache exists for the source."""
        mock_table = MagicMock()
        mock_batch = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_batch
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.return_value = {"Items": []}

        manager = CacheManager(mock_table)
        manager.invalidate("github")

        mock_table.query.assert_called_once()
        mock_batch.delete_item.assert_not_called()
