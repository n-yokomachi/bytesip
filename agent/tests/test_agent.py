"""Tests for ByteSip Agent.

TDD tests for filtering, count control, and duplicate prevention.
"""

from unittest.mock import MagicMock

from bytesip_agent.agent import ByteSipAgent
from bytesip_agent.memory import ProposedIdsManager


def create_mock_news_item(
    source: str, item_id: str, tags: list[str] | None = None
) -> dict:
    """Helper to create mock NewsItem dict."""
    return {
        "id": f"{source}_{item_id}",
        "title": f"Test Article {item_id}",
        "url": f"https://example.com/{item_id}",
        "summary": "Test summary",
        "tags": tags if tags is not None else ["python"],
        "source": source,
    }


class TestByteSipAgentFiltering:
    """Test ByteSipAgent filtering functionality."""

    def test_filters_by_source(self) -> None:
        """Should filter news by specified sources."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [
                create_mock_news_item("qiita", "1"),
                create_mock_news_item("zenn", "2"),
                create_mock_news_item("github", "3"),
            ]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        agent.get_news(sources=["qiita"])

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[1]["sources"] == ["qiita"]

    def test_filters_by_tags(self) -> None:
        """Should filter news by specified tags."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {"items": []}

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        agent.get_news(tags=["python", "rust"])

        call_args = mock_fetch.call_args
        assert call_args[1]["tags"] == ["python", "rust"]


class TestByteSipAgentLimitControl:
    """Test ByteSipAgent limit control."""

    def test_limits_results_to_specified_count(self) -> None:
        """Should limit results to specified count."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [create_mock_news_item("qiita", str(i)) for i in range(20)]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news(limit=5)

        assert len(response.items) == 5

    def test_default_limit_is_10(self) -> None:
        """Should use default limit of 10."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [create_mock_news_item("qiita", str(i)) for i in range(20)]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news()

        assert len(response.items) == 10

    def test_max_limit_per_source_is_10(self) -> None:
        """Should enforce max 10 items per source."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [create_mock_news_item("qiita", str(i)) for i in range(15)]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news(limit=15)

        # Should be capped at 10 per source
        assert len(response.items) == 10

    def test_max_total_limit_is_30(self) -> None:
        """Should enforce max 30 items total."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        items = []
        for source in ["qiita", "zenn", "github"]:
            items.extend([create_mock_news_item(source, str(i)) for i in range(15)])

        mock_fetch = MagicMock()
        mock_fetch.return_value = {"items": items}

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news(limit=50)

        # Should be capped at 30 total (10 per source * 3 sources)
        assert len(response.items) <= 30


class TestByteSipAgentDuplicatePrevention:
    """Test ByteSipAgent duplicate prevention."""

    def test_excludes_already_proposed_items(self) -> None:
        """Should exclude items that have already been proposed."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = ["qiita_1", "zenn_2"]
        mock_memory.filter_unproposed.return_value = ["github_3"]

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [
                create_mock_news_item("qiita", "1"),
                create_mock_news_item("zenn", "2"),
                create_mock_news_item("github", "3"),
            ]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news()

        assert len(response.items) == 1
        assert response.items[0].id == "github_3"

    def test_records_proposed_ids_after_fetch(self) -> None:
        """Should record proposed IDs after fetching."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [
                create_mock_news_item("qiita", "1"),
                create_mock_news_item("zenn", "2"),
            ]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        agent.get_news()

        mock_memory.record_proposed_ids.assert_called_once_with(["qiita_1", "zenn_2"])


class TestByteSipAgentHasMore:
    """Test ByteSipAgent has_more indicator."""

    def test_has_more_true_when_more_items_available(self) -> None:
        """Should indicate has_more when more items are available."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [create_mock_news_item("qiita", str(i)) for i in range(15)]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news(limit=5)

        assert response.has_more is True

    def test_has_more_false_when_no_more_items(self) -> None:
        """Should indicate no more when all items returned."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = []
        mock_memory.filter_unproposed.side_effect = lambda ids: ids

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [create_mock_news_item("qiita", str(i)) for i in range(3)]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news(limit=5)

        assert response.has_more is False

    def test_has_more_false_when_all_items_proposed(self) -> None:
        """Should indicate no more when all remaining items have been proposed."""
        mock_memory = MagicMock(spec=ProposedIdsManager)
        mock_memory.get_proposed_ids.return_value = ["qiita_0", "qiita_1", "qiita_2"]
        mock_memory.filter_unproposed.return_value = []

        mock_fetch = MagicMock()
        mock_fetch.return_value = {
            "items": [create_mock_news_item("qiita", str(i)) for i in range(3)]
        }

        agent = ByteSipAgent(
            memory_manager=mock_memory,
            fetch_func=mock_fetch,
        )
        response = agent.get_news()

        assert len(response.items) == 0
        assert response.has_more is False
