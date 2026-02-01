"""Data models for ByteSip News Fetcher.

This module defines the core data structures used throughout the application:
- NewsItem: Individual news article/repository
- NewsRequest/NewsResponse: Agent-level request/response
- FetchNewsRequest/FetchNewsResponse: Lambda-level request/response
- SourceError: Error information for individual sources
- CacheEntry: DynamoDB cache structure
"""

from dataclasses import dataclass
from typing import Literal

SourceType = Literal["qiita", "zenn", "github"]
ErrorType = Literal["connection_error", "rate_limit", "parse_error"]


def generate_news_id(source: SourceType, original_id: str) -> str:
    """Generate a unique news ID in the format {source}_{original_id}.

    Args:
        source: The news source (qiita, zenn, github)
        original_id: The original ID from the source
            - Qiita: item_id (e.g., "abc123def456")
            - Zenn: slug (e.g., "my-article-slug")
            - GitHub: full_name (e.g., "owner/repo-name")

    Returns:
        A unique ID string (e.g., "qiita_abc123def456")
    """
    return f"{source}_{original_id}"


@dataclass
class NewsItem:
    """Represents a single news item (article or repository).

    Attributes:
        id: Unique identifier in format "{source}_{original_id}"
        title: Article/repository title
        url: Direct link to the content
        summary: Brief description (extracted from source)
        tags: Technology tags (empty list for Zenn trend feed)
        source: Origin of the news item
    """

    id: str
    title: str
    url: str
    summary: str
    tags: list[str]
    source: SourceType


@dataclass
class NewsRequest:
    """Request parameters for news retrieval (Agent level).

    Attributes:
        sources: Filter by specific sources (None = all sources)
        limit: Maximum items per source (default: 10, max: 10)
        tags: Filter by technology tags (None = no filter)
    """

    sources: list[SourceType] | None = None
    limit: int = 10
    tags: list[str] | None = None


@dataclass
class NewsResponse:
    """Response containing news items (Agent level).

    Attributes:
        items: List of news items
        has_more: Whether more items are available in cache
    """

    items: list[NewsItem]
    has_more: bool


@dataclass
class FetchNewsRequest:
    """Request parameters for Lambda invocation.

    Attributes:
        sources: Filter by specific sources (None = all sources)
        tags: Filter by technology tags (None = no filter)
        force_refresh: Bypass cache and fetch fresh data
    """

    sources: list[SourceType] | None = None
    tags: list[str] | None = None
    force_refresh: bool = False


class SourceError(Exception):
    """Error for a failed source fetch.

    Attributes:
        source: The source that failed
        error_type: Category of the error
        message: Human-readable error description
    """

    def __init__(self, source: SourceType, error_type: ErrorType, message: str) -> None:
        self.source = source
        self.error_type = error_type
        self.message = message
        super().__init__(message)


@dataclass
class FetchNewsResponse:
    """Response from Lambda function.

    Attributes:
        items: Successfully fetched news items
        errors: Errors from failed sources (None if all successful)
    """

    items: list[NewsItem]
    errors: list[SourceError] | None = None


@dataclass
class CacheEntry:
    """DynamoDB cache entry for a source.

    Attributes:
        source: The news source
        items: Cached news items (max 30 per source)
        cached_at: ISO 8601 timestamp of cache creation
        ttl: Unix timestamp for DynamoDB TTL (24 hours from cached_at)
    """

    source: SourceType
    items: list[NewsItem]
    cached_at: str
    ttl: int
