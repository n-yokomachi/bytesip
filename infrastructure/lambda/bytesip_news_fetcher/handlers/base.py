"""Base handler interface for external sources."""

from abc import ABC, abstractmethod

# Support both relative imports (local) and package imports (Lambda)
try:
    from ..models import NewsItem
except ImportError:
    from models import NewsItem


class BaseHandler(ABC):
    """Abstract base class for news source handlers.

    All source handlers must implement the fetch method to retrieve
    news items from their respective sources.
    """

    @abstractmethod
    def fetch(self, tags: list[str] | None = None) -> list[NewsItem]:
        """Fetch news items from the source.

        Args:
            tags: Optional list of tags to filter by

        Returns:
            List of NewsItem objects

        Raises:
            SourceError: If fetching fails (rate limit, connection error, etc.)
        """
        pass
