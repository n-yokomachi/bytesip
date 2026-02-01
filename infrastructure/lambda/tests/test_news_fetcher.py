"""Tests for NewsFetcher orchestration.

TDD tests for parallel fetching and graceful degradation.
"""

from unittest.mock import MagicMock

from bytesip_news_fetcher.models import NewsItem, SourceError
from bytesip_news_fetcher.news_fetcher import NewsFetcher


def create_mock_news_item(
    source: str, item_id: str, tags: list[str] | None = None
) -> NewsItem:
    """Helper to create mock NewsItem."""
    return NewsItem(
        id=f"{source}_{item_id}",
        title=f"Test Article {item_id}",
        url=f"https://example.com/{item_id}",
        summary="Test summary",
        tags=tags if tags is not None else ["python"],
        source=source,
    )


class TestNewsFetcherParallelExecution:
    """Test parallel fetching from multiple sources."""

    def test_fetches_from_all_sources_when_none_specified(self) -> None:
        """Should fetch from all sources when sources parameter is None."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_handlers = {
            "qiita": MagicMock(),
            "zenn": MagicMock(),
            "github": MagicMock(),
        }
        mock_handlers["qiita"].fetch.return_value = [
            create_mock_news_item("qiita", "1")
        ]
        mock_handlers["zenn"].fetch.return_value = [create_mock_news_item("zenn", "2")]
        mock_handlers["github"].fetch.return_value = [
            create_mock_news_item("github", "3")
        ]

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch()

        assert len(response.items) == 3
        assert response.errors is None

    def test_fetches_from_specified_sources_only(self) -> None:
        """Should fetch only from specified sources."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_handlers = {
            "qiita": MagicMock(),
            "zenn": MagicMock(),
            "github": MagicMock(),
        }
        mock_handlers["qiita"].fetch.return_value = [
            create_mock_news_item("qiita", "1")
        ]
        mock_handlers["zenn"].fetch.return_value = [create_mock_news_item("zenn", "2")]

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita", "zenn"])

        assert len(response.items) == 2
        sources = {item.source for item in response.items}
        assert sources == {"qiita", "zenn"}
        mock_handlers["github"].fetch.assert_not_called()


class TestNewsFetcherCacheStrategy:
    """Test cache-first strategy."""

    def test_returns_cached_items_when_available(self) -> None:
        """Should return cached items without calling handlers."""
        cached_items = [create_mock_news_item("qiita", "cached")]
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_items

        mock_handlers = {
            "qiita": MagicMock(),
        }

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita"])

        assert len(response.items) == 1
        assert response.items[0].id == "qiita_cached"
        mock_handlers["qiita"].fetch.assert_not_called()

    def test_fetches_from_api_when_cache_miss(self) -> None:
        """Should fetch from API and update cache when cache is empty."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        api_items = [create_mock_news_item("qiita", "api")]
        mock_handlers = {
            "qiita": MagicMock(),
        }
        mock_handlers["qiita"].fetch.return_value = api_items

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita"])

        assert len(response.items) == 1
        assert response.items[0].id == "qiita_api"
        mock_cache.set.assert_called_once_with("qiita", api_items)

    def test_force_refresh_bypasses_cache(self) -> None:
        """Should bypass cache when force_refresh is True."""
        cached_items = [create_mock_news_item("qiita", "cached")]
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_items

        api_items = [create_mock_news_item("qiita", "fresh")]
        mock_handlers = {
            "qiita": MagicMock(),
        }
        mock_handlers["qiita"].fetch.return_value = api_items

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita"], force_refresh=True)

        assert len(response.items) == 1
        assert response.items[0].id == "qiita_fresh"
        mock_cache.set.assert_called_once()


class TestNewsFetcherGracefulDegradation:
    """Test graceful degradation on errors."""

    def test_returns_partial_results_on_single_source_failure(self) -> None:
        """Should return successful results even when one source fails."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_handlers = {
            "qiita": MagicMock(),
            "zenn": MagicMock(),
        }
        mock_handlers["qiita"].fetch.return_value = [
            create_mock_news_item("qiita", "1")
        ]
        mock_handlers["zenn"].fetch.side_effect = SourceError(
            source="zenn",
            error_type="connection_error",
            message="Connection failed",
        )

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita", "zenn"])

        assert len(response.items) == 1
        assert response.items[0].source == "qiita"
        assert response.errors is not None
        assert len(response.errors) == 1
        assert response.errors[0].source == "zenn"

    def test_returns_empty_with_errors_when_all_sources_fail(self) -> None:
        """Should return empty items with all errors when all sources fail."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_handlers = {
            "qiita": MagicMock(),
            "zenn": MagicMock(),
        }
        mock_handlers["qiita"].fetch.side_effect = SourceError(
            source="qiita",
            error_type="rate_limit",
            message="Rate limit exceeded",
        )
        mock_handlers["zenn"].fetch.side_effect = SourceError(
            source="zenn",
            error_type="connection_error",
            message="Connection failed",
        )

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita", "zenn"])

        assert len(response.items) == 0
        assert response.errors is not None
        assert len(response.errors) == 2

    def test_collects_different_error_types(self) -> None:
        """Should collect errors of different types."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_handlers = {
            "qiita": MagicMock(),
            "zenn": MagicMock(),
            "github": MagicMock(),
        }
        mock_handlers["qiita"].fetch.side_effect = SourceError(
            source="qiita",
            error_type="rate_limit",
            message="Rate limit",
        )
        mock_handlers["zenn"].fetch.side_effect = SourceError(
            source="zenn",
            error_type="parse_error",
            message="Parse error",
        )
        mock_handlers["github"].fetch.side_effect = SourceError(
            source="github",
            error_type="connection_error",
            message="Connection error",
        )

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch()

        assert response.errors is not None
        error_types = {e.error_type for e in response.errors}
        assert error_types == {"rate_limit", "parse_error", "connection_error"}


class TestNewsFetcherTagFiltering:
    """Test tag filtering."""

    def test_passes_tags_to_handlers(self) -> None:
        """Should pass tags parameter to handlers."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        mock_handlers = {
            "qiita": MagicMock(),
        }
        mock_handlers["qiita"].fetch.return_value = []

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        fetcher.fetch(sources=["qiita"], tags=["python", "rust"])

        mock_handlers["qiita"].fetch.assert_called_once_with(tags=["python", "rust"])

    def test_filters_cached_items_by_tags(self) -> None:
        """Should filter cached items by tags."""
        cached_items = [
            create_mock_news_item("qiita", "1", tags=["python", "django"]),
            create_mock_news_item("qiita", "2", tags=["rust", "wasm"]),
            create_mock_news_item("qiita", "3", tags=["python", "fastapi"]),
        ]
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_items

        mock_handlers = {
            "qiita": MagicMock(),
        }

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita"], tags=["python"])

        assert len(response.items) == 2
        assert all("python" in item.tags for item in response.items)
        mock_handlers["qiita"].fetch.assert_not_called()

    def test_returns_all_cached_items_when_no_tags(self) -> None:
        """Should return all cached items when tags is None."""
        cached_items = [
            create_mock_news_item("qiita", "1", tags=["python"]),
            create_mock_news_item("qiita", "2", tags=["rust"]),
        ]
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_items

        mock_handlers = {
            "qiita": MagicMock(),
        }

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita"])

        assert len(response.items) == 2

    def test_tag_filter_is_case_insensitive(self) -> None:
        """Should filter by tags case-insensitively."""
        cached_items = [
            create_mock_news_item("qiita", "1", tags=["Python", "Django"]),
            create_mock_news_item("qiita", "2", tags=["RUST"]),
        ]
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_items

        mock_handlers = {
            "qiita": MagicMock(),
        }

        fetcher = NewsFetcher(
            cache_manager=mock_cache,
            handlers=mock_handlers,
        )
        response = fetcher.fetch(sources=["qiita"], tags=["python"])

        assert len(response.items) == 1
        assert response.items[0].id == "qiita_1"
