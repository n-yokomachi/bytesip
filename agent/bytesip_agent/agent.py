"""ByteSip Agent implementation.

Provides the main ByteSipAgent class for news curation with
filtering, count control, and duplicate prevention.
"""

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from .memory import ProposedIdsManager
from .models import NewsItem, NewsResponse, SourceType

# Limits
DEFAULT_LIMIT = 10
MAX_PER_SOURCE = 10
MAX_TOTAL = 30


class ByteSipAgent:
    """AI agent for IT/AI news curation.

    Handles filtering by source/tags, count control,
    and duplicate prevention using session memory.
    """

    def __init__(
        self,
        memory_manager: ProposedIdsManager,
        fetch_func: Callable[..., dict[str, Any]],
    ) -> None:
        """Initialize the agent.

        Args:
            memory_manager: Manager for tracking proposed news IDs
            fetch_func: Function to fetch news (typically fetch_news tool)
        """
        self._memory = memory_manager
        self._fetch = fetch_func

    def get_news(
        self,
        sources: list[SourceType] | None = None,
        tags: list[str] | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> NewsResponse:
        """Get news items with filtering and duplicate prevention.

        Args:
            sources: List of sources to fetch from (None = all)
            tags: Optional list of tags to filter by
            limit: Maximum number of items to return (default 10)

        Returns:
            NewsResponse with filtered items and has_more indicator
        """
        # Fetch news from sources
        result = self._fetch(
            sources=sources,
            tags=tags,
            force_refresh=False,
        )

        items_data = result.get("items", [])

        # Convert to NewsItem objects
        all_items = [
            NewsItem(
                id=item["id"],
                title=item["title"],
                url=item["url"],
                summary=item["summary"],
                tags=item["tags"],
                source=item["source"],
            )
            for item in items_data
        ]

        # Filter out already proposed items
        all_ids = [item.id for item in all_items]
        unproposed_ids = set(self._memory.filter_unproposed(all_ids))
        unproposed_items = [item for item in all_items if item.id in unproposed_ids]

        # Apply per-source limit
        items_by_source: dict[str, list[NewsItem]] = defaultdict(list)
        for item in unproposed_items:
            if len(items_by_source[item.source]) < MAX_PER_SOURCE:
                items_by_source[item.source].append(item)

        # Flatten and apply total limit
        limited_items: list[NewsItem] = []
        for source_items in items_by_source.values():
            limited_items.extend(source_items)

        # Sort by original order and apply requested limit
        original_order = {item.id: i for i, item in enumerate(unproposed_items)}
        limited_items.sort(key=lambda x: original_order.get(x.id, 0))

        # Apply user limit and max total
        effective_limit = min(limit, MAX_TOTAL)
        final_items = limited_items[:effective_limit]

        # Calculate has_more
        total_available = sum(
            min(len(items), MAX_PER_SOURCE) for items in items_by_source.values()
        )
        has_more = len(final_items) < total_available

        # Record proposed IDs
        if final_items:
            self._memory.record_proposed_ids([item.id for item in final_items])

        return NewsResponse(
            items=final_items,
            has_more=has_more,
        )
