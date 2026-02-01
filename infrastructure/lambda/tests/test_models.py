"""Tests for data models."""

import pytest
from bytesip_news_fetcher.models import (
    NewsItem,
    NewsRequest,
    NewsResponse,
    FetchNewsRequest,
    FetchNewsResponse,
    SourceError,
    CacheEntry,
    generate_news_id,
)


class TestNewsItem:
    """Tests for NewsItem dataclass."""

    def test_create_news_item_with_all_fields(self):
        """NewsItem should be created with all required fields."""
        item = NewsItem(
            id="qiita_abc123",
            title="Test Article",
            url="https://qiita.com/test/items/abc123",
            summary="This is a test article summary.",
            tags=["python", "aws"],
            source="qiita",
        )
        assert item.id == "qiita_abc123"
        assert item.title == "Test Article"
        assert item.url == "https://qiita.com/test/items/abc123"
        assert item.summary == "This is a test article summary."
        assert item.tags == ["python", "aws"]
        assert item.source == "qiita"

    def test_create_news_item_with_empty_tags(self):
        """NewsItem should allow empty tags list (for Zenn)."""
        item = NewsItem(
            id="zenn_my-article",
            title="Zenn Article",
            url="https://zenn.dev/user/articles/my-article",
            summary="Zenn article summary.",
            tags=[],
            source="zenn",
        )
        assert item.tags == []

    def test_create_github_news_item(self):
        """NewsItem should work for GitHub repositories."""
        item = NewsItem(
            id="github_owner/repo-name",
            title="Awesome Repository",
            url="https://github.com/owner/repo-name",
            summary="A great open source project.",
            tags=["python", "machine-learning"],
            source="github",
        )
        assert item.source == "github"
        assert "/" in item.id


class TestGenerateNewsId:
    """Tests for ID generation function."""

    def test_generate_qiita_id(self):
        """Should generate ID in format qiita_{original_id}."""
        news_id = generate_news_id("qiita", "abc123def456")
        assert news_id == "qiita_abc123def456"

    def test_generate_zenn_id(self):
        """Should generate ID in format zenn_{slug}."""
        news_id = generate_news_id("zenn", "my-article-slug")
        assert news_id == "zenn_my-article-slug"

    def test_generate_github_id(self):
        """Should generate ID in format github_{full_name}."""
        news_id = generate_news_id("github", "owner/repo-name")
        assert news_id == "github_owner/repo-name"


class TestNewsRequest:
    """Tests for NewsRequest dataclass."""

    def test_create_default_request(self):
        """NewsRequest should have sensible defaults."""
        request = NewsRequest()
        assert request.sources is None
        assert request.limit == 10
        assert request.tags is None

    def test_create_request_with_sources(self):
        """NewsRequest should accept specific sources."""
        request = NewsRequest(sources=["qiita", "github"], limit=5)
        assert request.sources == ["qiita", "github"]
        assert request.limit == 5


class TestNewsResponse:
    """Tests for NewsResponse dataclass."""

    def test_create_response_with_items(self):
        """NewsResponse should contain items and has_more flag."""
        item = NewsItem(
            id="qiita_test",
            title="Test",
            url="https://example.com",
            summary="Summary",
            tags=[],
            source="qiita",
        )
        response = NewsResponse(items=[item], has_more=True)
        assert len(response.items) == 1
        assert response.has_more is True

    def test_create_empty_response(self):
        """NewsResponse should work with empty items."""
        response = NewsResponse(items=[], has_more=False)
        assert len(response.items) == 0
        assert response.has_more is False


class TestFetchNewsRequest:
    """Tests for FetchNewsRequest dataclass."""

    def test_create_default_fetch_request(self):
        """FetchNewsRequest should have sensible defaults."""
        request = FetchNewsRequest()
        assert request.sources is None
        assert request.tags is None
        assert request.force_refresh is False

    def test_create_fetch_request_with_force_refresh(self):
        """FetchNewsRequest should support force_refresh flag."""
        request = FetchNewsRequest(force_refresh=True)
        assert request.force_refresh is True


class TestFetchNewsResponse:
    """Tests for FetchNewsResponse dataclass."""

    def test_create_successful_response(self):
        """FetchNewsResponse should contain items without errors."""
        item = NewsItem(
            id="qiita_test",
            title="Test",
            url="https://example.com",
            summary="Summary",
            tags=[],
            source="qiita",
        )
        response = FetchNewsResponse(items=[item], errors=None)
        assert len(response.items) == 1
        assert response.errors is None

    def test_create_response_with_errors(self):
        """FetchNewsResponse should contain partial results with errors."""
        item = NewsItem(
            id="qiita_test",
            title="Test",
            url="https://example.com",
            summary="Summary",
            tags=[],
            source="qiita",
        )
        error = SourceError(
            source="github",
            error_type="rate_limit",
            message="API rate limit exceeded",
        )
        response = FetchNewsResponse(items=[item], errors=[error])
        assert len(response.items) == 1
        assert len(response.errors) == 1
        assert response.errors[0].source == "github"


class TestSourceError:
    """Tests for SourceError dataclass."""

    def test_create_connection_error(self):
        """SourceError should represent connection errors."""
        error = SourceError(
            source="qiita",
            error_type="connection_error",
            message="Failed to connect to Qiita API",
        )
        assert error.source == "qiita"
        assert error.error_type == "connection_error"

    def test_create_rate_limit_error(self):
        """SourceError should represent rate limit errors."""
        error = SourceError(
            source="github",
            error_type="rate_limit",
            message="Rate limit exceeded: 30 requests per minute",
        )
        assert error.error_type == "rate_limit"

    def test_create_parse_error(self):
        """SourceError should represent parse errors."""
        error = SourceError(
            source="zenn",
            error_type="parse_error",
            message="Failed to parse RSS feed",
        )
        assert error.error_type == "parse_error"


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_create_cache_entry(self):
        """CacheEntry should contain items with metadata."""
        item = NewsItem(
            id="qiita_test",
            title="Test",
            url="https://example.com",
            summary="Summary",
            tags=[],
            source="qiita",
        )
        entry = CacheEntry(
            source="qiita",
            items=[item],
            cached_at="2026-02-01T00:00:00Z",
            ttl=1738454400,  # Unix timestamp
        )
        assert entry.source == "qiita"
        assert len(entry.items) == 1
        assert entry.cached_at == "2026-02-01T00:00:00Z"
        assert entry.ttl == 1738454400
