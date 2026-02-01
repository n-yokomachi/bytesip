"""Tests for external source handlers.

TDD tests for Qiita, Zenn, and GitHub handlers.
"""

import time
from unittest.mock import MagicMock, patch

from bytesip_news_fetcher.handlers.base import BaseHandler
from bytesip_news_fetcher.handlers.qiita import QiitaHandler
from bytesip_news_fetcher.handlers.zenn import ZennHandler
from bytesip_news_fetcher.handlers.github import GitHubHandler
from bytesip_news_fetcher.models import NewsItem, SourceError


class TestQiitaHandler:
    """Test QiitaHandler."""

    def test_fetch_returns_news_items(self) -> None:
        """Fetch should return list of NewsItem."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "abc123",
                "title": "Python Tips",
                "url": "https://qiita.com/user/items/abc123",
                "body": "This is an article about Python. " * 20,
                "tags": [{"name": "python"}, {"name": "tips"}],
            }
        ]

        with patch("requests.get", return_value=mock_response):
            handler = QiitaHandler(access_token="test_token")
            result = handler.fetch()

        assert len(result) == 1
        assert result[0].id == "qiita_abc123"
        assert result[0].title == "Python Tips"
        assert result[0].source == "qiita"
        assert "python" in result[0].tags

    def test_fetch_with_tag_filter(self) -> None:
        """Fetch should filter by tag when specified."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch("requests.get", return_value=mock_response) as mock_get:
            handler = QiitaHandler(access_token="test_token")
            handler.fetch(tags=["python"])

        call_args = mock_get.call_args
        assert "tag:python" in call_args[1]["params"]["query"]

    def test_fetch_handles_rate_limit(self) -> None:
        """Fetch should raise SourceError on rate limit."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Rate limit exceeded"}

        with patch("requests.get", return_value=mock_response):
            handler = QiitaHandler(access_token="test_token")
            try:
                handler.fetch()
                assert False, "Should raise SourceError"
            except SourceError as e:
                assert e.error_type == "rate_limit"
                assert e.source == "qiita"

    def test_fetch_handles_connection_error(self) -> None:
        """Fetch should raise SourceError on connection error."""
        with patch("requests.get", side_effect=Exception("Connection failed")):
            handler = QiitaHandler(access_token="test_token")
            try:
                handler.fetch()
                assert False, "Should raise SourceError"
            except SourceError as e:
                assert e.error_type == "connection_error"

    def test_summary_strips_markdown(self) -> None:
        """Summary should be plain text without markdown."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "abc123",
                "title": "Test",
                "url": "https://qiita.com/test",
                "body": "# Heading\n\n**Bold** and `code`\n\nParagraph text here.",
                "tags": [],
            }
        ]

        with patch("requests.get", return_value=mock_response):
            handler = QiitaHandler(access_token="test_token")
            result = handler.fetch()

        # Should not contain markdown symbols
        assert "#" not in result[0].summary
        assert "**" not in result[0].summary
        assert "`" not in result[0].summary


class TestZennHandler:
    """Test ZennHandler."""

    def test_fetch_returns_news_items(self) -> None:
        """Fetch should return list of NewsItem from RSS."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            MagicMock(
                id="https://zenn.dev/user/articles/my-article",
                title="Zenn Article",
                link="https://zenn.dev/user/articles/my-article",
                summary="This is the article summary.",
            )
        ]

        with patch("feedparser.parse", return_value=mock_feed):
            handler = ZennHandler()
            result = handler.fetch()

        assert len(result) == 1
        assert result[0].id == "zenn_my-article"
        assert result[0].title == "Zenn Article"
        assert result[0].source == "zenn"

    def test_fetch_with_topic_uses_topic_feed(self) -> None:
        """Fetch with tags should use topic-specific RSS."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = []

        with patch("feedparser.parse", return_value=mock_feed) as mock_parse:
            handler = ZennHandler()
            handler.fetch(tags=["python"])

        call_args = mock_parse.call_args[0][0]
        assert "/topics/python/feed" in call_args

    def test_fetch_handles_parse_error(self) -> None:
        """Fetch should raise SourceError on RSS parse error."""
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse failed")

        with patch("feedparser.parse", return_value=mock_feed):
            handler = ZennHandler()
            try:
                handler.fetch()
                assert False, "Should raise SourceError"
            except SourceError as e:
                assert e.error_type == "parse_error"
                assert e.source == "zenn"

    def test_fetch_handles_connection_error(self) -> None:
        """Fetch should raise SourceError on connection error."""
        with patch("feedparser.parse", side_effect=Exception("Connection failed")):
            handler = ZennHandler()
            try:
                handler.fetch()
                assert False, "Should raise SourceError"
            except SourceError as e:
                assert e.error_type == "connection_error"


class TestGitHubHandler:
    """Test GitHubHandler."""

    def test_fetch_returns_news_items(self) -> None:
        """Fetch should return list of NewsItem from GitHub."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "owner/repo",
                    "html_url": "https://github.com/owner/repo",
                    "description": "A great repository",
                    "topics": ["python", "machine-learning"],
                }
            ]
        }

        with patch("requests.get", return_value=mock_response):
            handler = GitHubHandler(access_token="test_token")
            result = handler.fetch()

        assert len(result) == 1
        assert result[0].id == "github_owner/repo"
        assert result[0].title == "owner/repo"
        assert result[0].source == "github"
        assert "python" in result[0].tags

    def test_fetch_uses_trending_query(self) -> None:
        """Fetch should query for recently pushed repos with stars."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}

        with patch("requests.get", return_value=mock_response) as mock_get:
            handler = GitHubHandler(access_token="test_token")
            handler.fetch()

        call_args = mock_get.call_args
        query = call_args[1]["params"]["q"]
        assert "pushed:>" in query
        assert "stars:>" in query

    def test_fetch_handles_rate_limit(self) -> None:
        """Fetch should raise SourceError on rate limit."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "0"}

        with patch("requests.get", return_value=mock_response):
            handler = GitHubHandler(access_token="test_token")
            try:
                handler.fetch()
                assert False, "Should raise SourceError"
            except SourceError as e:
                assert e.error_type == "rate_limit"
                assert e.source == "github"

    def test_fetch_handles_connection_error(self) -> None:
        """Fetch should raise SourceError on connection error."""
        with patch("requests.get", side_effect=Exception("Connection failed")):
            handler = GitHubHandler(access_token="test_token")
            try:
                handler.fetch()
                assert False, "Should raise SourceError"
            except SourceError as e:
                assert e.error_type == "connection_error"

    def test_handles_missing_description(self) -> None:
        """Fetch should handle repos with no description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "owner/repo",
                    "html_url": "https://github.com/owner/repo",
                    "description": None,
                    "topics": [],
                }
            ]
        }

        with patch("requests.get", return_value=mock_response):
            handler = GitHubHandler(access_token="test_token")
            result = handler.fetch()

        assert result[0].summary == ""
