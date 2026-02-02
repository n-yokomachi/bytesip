"""Data models for ByteSip Agent."""

from dataclasses import dataclass
from typing import Literal

SourceType = Literal["qiita", "zenn", "github"]


@dataclass
class NewsItem:
    """Represents a news item from an external source."""

    id: str
    title: str
    url: str
    summary: str
    tags: list[str]
    source: SourceType


@dataclass
class NewsRequest:
    """Request parameters for fetching news."""

    sources: list[SourceType] | None = None
    limit: int = 10
    tags: list[str] | None = None


@dataclass
class NewsResponse:
    """Response from news fetching with pagination info."""

    items: list[NewsItem]
    has_more: bool


@dataclass
class SourceError:
    """Error information from a source."""

    source: SourceType
    error_type: Literal["connection_error", "rate_limit", "parse_error"]
    message: str


@dataclass
class FetchNewsResponse:
    """Raw response from the fetch_news Lambda."""

    items: list[NewsItem]
    errors: list[SourceError] | None = None
