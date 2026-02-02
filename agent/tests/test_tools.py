"""Tests for ByteSip Agent tools.

TDD tests for fetch_news tool.
"""

from unittest.mock import MagicMock

import pytest

from bytesip_agent.models import FetchNewsResponse, NewsItem, SourceError
from bytesip_agent.tools import FetchNewsClient, fetch_news, set_client


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


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the default client before and after each test."""
    set_client(None)
    yield
    set_client(None)


class TestFetchNewsTool:
    """Test fetch_news tool function."""

    def test_fetch_news_returns_items(self) -> None:
        """fetch_news should return news items from the client."""
        mock_client = MagicMock(spec=FetchNewsClient)
        mock_client.fetch.return_value = FetchNewsResponse(
            items=[
                create_mock_news_item("qiita", "1"),
                create_mock_news_item("zenn", "2"),
            ],
            errors=None,
        )
        set_client(mock_client)

        result = fetch_news._tool_func(
            sources=["qiita", "zenn"],
            tags=["python"],
        )

        assert "items" in result
        assert len(result["items"]) == 2
        mock_client.fetch.assert_called_once_with(
            sources=["qiita", "zenn"],
            tags=["python"],
            force_refresh=False,
        )

    def test_fetch_news_with_no_sources(self) -> None:
        """fetch_news should fetch from all sources when none specified."""
        mock_client = MagicMock(spec=FetchNewsClient)
        mock_client.fetch.return_value = FetchNewsResponse(
            items=[
                create_mock_news_item("qiita", "1"),
                create_mock_news_item("zenn", "2"),
                create_mock_news_item("github", "3"),
            ],
            errors=None,
        )
        set_client(mock_client)

        result = fetch_news._tool_func()

        assert len(result["items"]) == 3
        mock_client.fetch.assert_called_once_with(
            sources=None,
            tags=None,
            force_refresh=False,
        )

    def test_fetch_news_includes_errors(self) -> None:
        """fetch_news should include errors in response when source fails."""
        mock_client = MagicMock(spec=FetchNewsClient)
        mock_client.fetch.return_value = FetchNewsResponse(
            items=[create_mock_news_item("qiita", "1")],
            errors=[
                SourceError(
                    source="zenn",
                    error_type="connection_error",
                    message="Connection failed",
                )
            ],
        )
        set_client(mock_client)

        result = fetch_news._tool_func(sources=["qiita", "zenn"])

        assert len(result["items"]) == 1
        assert "errors" in result
        assert len(result["errors"]) == 1
        assert result["errors"][0]["source"] == "zenn"

    def test_fetch_news_with_force_refresh(self) -> None:
        """fetch_news should pass force_refresh to client."""
        mock_client = MagicMock(spec=FetchNewsClient)
        mock_client.fetch.return_value = FetchNewsResponse(items=[], errors=None)
        set_client(mock_client)

        fetch_news._tool_func(force_refresh=True)

        mock_client.fetch.assert_called_once_with(
            sources=None,
            tags=None,
            force_refresh=True,
        )


class TestFetchNewsClient:
    """Test FetchNewsClient for Lambda invocation."""

    def test_client_invokes_lambda(self) -> None:
        """Client should invoke Lambda and parse response."""
        response_json = (
            b'{"items": [{"id": "qiita_1", "title": "Test", '
            b'"url": "https://example.com", "summary": "Summary", '
            b'"tags": ["python"], "source": "qiita"}], "errors": null}'
        )
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=lambda: response_json)
        }

        client = FetchNewsClient(
            lambda_client=mock_lambda,
            function_name="bytesip-news-fetcher",
        )
        response = client.fetch(sources=["qiita"])

        assert len(response.items) == 1
        assert response.items[0].id == "qiita_1"
        mock_lambda.invoke.assert_called_once()

    def test_client_handles_empty_response(self) -> None:
        """Client should handle empty items response."""
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=lambda: b'{"items": [], "errors": null}')
        }

        client = FetchNewsClient(
            lambda_client=mock_lambda,
            function_name="bytesip-news-fetcher",
        )
        response = client.fetch()

        assert len(response.items) == 0
        assert response.errors is None

    def test_client_parses_errors(self) -> None:
        """Client should parse error information from Lambda response."""
        response_json = (
            b'{"items": [], "errors": [{"source": "github", '
            b'"error_type": "rate_limit", "message": "Rate limit exceeded"}]}'
        )
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=lambda: response_json)
        }

        client = FetchNewsClient(
            lambda_client=mock_lambda,
            function_name="bytesip-news-fetcher",
        )
        response = client.fetch()

        assert response.errors is not None
        assert len(response.errors) == 1
        assert response.errors[0].source == "github"
        assert response.errors[0].error_type == "rate_limit"
