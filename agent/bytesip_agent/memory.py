"""Memory management for ByteSip Agent.

Provides ProposedIdsManager for tracking proposed news IDs
using AgentCore Memory STM.
"""

from typing import Any, Protocol


class SessionProtocol(Protocol):
    """Protocol for session objects."""

    def get_session_attributes(self) -> dict[str, Any]:
        """Get session attributes."""
        ...

    def update_session_attributes(self, attributes: dict[str, Any]) -> None:
        """Update session attributes."""
        ...


class ProposedIdsManager:
    """Manager for tracking proposed news IDs in session memory.

    Uses AgentCore Memory STM to store proposed_ids list,
    enabling duplicate prevention within a session.
    """

    PROPOSED_IDS_KEY = "proposed_ids"

    def __init__(self, session: SessionProtocol) -> None:
        """Initialize the manager.

        Args:
            session: Session object for memory operations
        """
        self._session = session

    def get_proposed_ids(self) -> list[str]:
        """Get list of already proposed news IDs.

        Returns:
            List of news IDs that have been proposed in this session
        """
        attrs = self._session.get_session_attributes()
        return attrs.get(self.PROPOSED_IDS_KEY, [])

    def record_proposed_ids(self, ids: list[str]) -> None:
        """Record newly proposed news IDs.

        Args:
            ids: List of news IDs to mark as proposed
        """
        existing = set(self.get_proposed_ids())
        new_ids = [id for id in ids if id not in existing]
        updated = list(existing) + new_ids

        self._session.update_session_attributes({
            self.PROPOSED_IDS_KEY: updated
        })

    def is_proposed(self, news_id: str) -> bool:
        """Check if a news ID has already been proposed.

        Args:
            news_id: The news ID to check

        Returns:
            True if already proposed, False otherwise
        """
        return news_id in self.get_proposed_ids()

    def filter_unproposed(self, ids: list[str]) -> list[str]:
        """Filter out already proposed IDs.

        Args:
            ids: List of news IDs to filter

        Returns:
            List of IDs that have not been proposed yet
        """
        proposed = set(self.get_proposed_ids())
        return [id for id in ids if id not in proposed]

    def clear(self) -> None:
        """Clear all proposed IDs."""
        self._session.update_session_attributes({
            self.PROPOSED_IDS_KEY: []
        })
