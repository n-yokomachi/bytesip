"""Tests for ByteSip Agent memory management.

TDD tests for AgentCore Memory STM integration.
"""

from unittest.mock import MagicMock

from bytesip_agent.memory import ProposedIdsManager


class TestProposedIdsManager:
    """Test ProposedIdsManager for tracking proposed news IDs."""

    def test_get_proposed_ids_returns_empty_initially(self) -> None:
        """Should return empty list when no IDs have been proposed."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {}

        manager = ProposedIdsManager(session=mock_session)
        ids = manager.get_proposed_ids()

        assert ids == []

    def test_get_proposed_ids_returns_stored_ids(self) -> None:
        """Should return previously stored IDs."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {
            "proposed_ids": ["qiita_1", "zenn_2", "github_3"]
        }

        manager = ProposedIdsManager(session=mock_session)
        ids = manager.get_proposed_ids()

        assert ids == ["qiita_1", "zenn_2", "github_3"]

    def test_record_proposed_ids_stores_new_ids(self) -> None:
        """Should store new IDs in session."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {}

        manager = ProposedIdsManager(session=mock_session)
        manager.record_proposed_ids(["qiita_1", "zenn_2"])

        mock_session.update_session_attributes.assert_called_once_with({
            "proposed_ids": ["qiita_1", "zenn_2"]
        })

    def test_record_proposed_ids_appends_to_existing(self) -> None:
        """Should append new IDs to existing ones."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {
            "proposed_ids": ["qiita_1"]
        }

        manager = ProposedIdsManager(session=mock_session)
        manager.record_proposed_ids(["zenn_2", "github_3"])

        mock_session.update_session_attributes.assert_called_once_with({
            "proposed_ids": ["qiita_1", "zenn_2", "github_3"]
        })

    def test_record_proposed_ids_avoids_duplicates(self) -> None:
        """Should not add duplicate IDs."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {
            "proposed_ids": ["qiita_1", "zenn_2"]
        }

        manager = ProposedIdsManager(session=mock_session)
        manager.record_proposed_ids(["zenn_2", "github_3"])

        # Check the call was made with expected IDs (order may vary due to set)
        mock_session.update_session_attributes.assert_called_once()
        call_args = mock_session.update_session_attributes.call_args[0][0]
        assert set(call_args["proposed_ids"]) == {"qiita_1", "zenn_2", "github_3"}

    def test_is_proposed_returns_true_for_existing_id(self) -> None:
        """Should return True for already proposed IDs."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {
            "proposed_ids": ["qiita_1", "zenn_2"]
        }

        manager = ProposedIdsManager(session=mock_session)

        assert manager.is_proposed("qiita_1") is True
        assert manager.is_proposed("zenn_2") is True

    def test_is_proposed_returns_false_for_new_id(self) -> None:
        """Should return False for new IDs."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {
            "proposed_ids": ["qiita_1"]
        }

        manager = ProposedIdsManager(session=mock_session)

        assert manager.is_proposed("github_3") is False

    def test_filter_unproposed_removes_proposed_ids(self) -> None:
        """Should filter out already proposed IDs."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {
            "proposed_ids": ["qiita_1", "zenn_2"]
        }

        manager = ProposedIdsManager(session=mock_session)
        ids_to_filter = ["qiita_1", "zenn_2", "github_3", "qiita_4"]
        filtered = manager.filter_unproposed(ids_to_filter)

        assert filtered == ["github_3", "qiita_4"]

    def test_filter_unproposed_returns_all_when_none_proposed(self) -> None:
        """Should return all IDs when none have been proposed."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {}

        manager = ProposedIdsManager(session=mock_session)
        filtered = manager.filter_unproposed(["qiita_1", "zenn_2"])

        assert filtered == ["qiita_1", "zenn_2"]

    def test_clear_proposed_ids(self) -> None:
        """Should clear all proposed IDs."""
        mock_session = MagicMock()
        mock_session.get_session_attributes.return_value = {
            "proposed_ids": ["qiita_1", "zenn_2"]
        }

        manager = ProposedIdsManager(session=mock_session)
        manager.clear()

        mock_session.update_session_attributes.assert_called_once_with({
            "proposed_ids": []
        })
