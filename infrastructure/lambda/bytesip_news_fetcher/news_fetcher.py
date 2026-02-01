"""News Fetcher orchestration module.

This module provides the NewsFetcher class for parallel fetching
from multiple news sources with cache-first strategy and graceful degradation.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from .cache_manager import CacheManager
from .handlers.base import BaseHandler
from .models import FetchNewsResponse, NewsItem, SourceError, SourceType


class NewsFetcher:
    """Orchestrates parallel fetching from multiple news sources.

    Implements cache-first strategy and graceful degradation
    when individual sources fail.
    """

    MAX_WORKERS = 3

    def __init__(
        self,
        cache_manager: CacheManager,
        handlers: dict[str, BaseHandler],
    ) -> None:
        """Initialize NewsFetcher.

        Args:
            cache_manager: CacheManager instance for cache operations
            handlers: Dictionary mapping source names to handler instances
        """
        self._cache = cache_manager
        self._handlers = handlers

    def fetch(
        self,
        sources: list[SourceType] | None = None,
        tags: list[str] | None = None,
        force_refresh: bool = False,
    ) -> FetchNewsResponse:
        """Fetch news from sources in parallel.

        Args:
            sources: List of sources to fetch from (None = all sources)
            tags: Optional list of tags to filter by
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            FetchNewsResponse containing items and any errors
        """
        target_sources = sources or list(self._handlers.keys())

        all_items: list[NewsItem] = []
        all_errors: list[SourceError] = []

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._fetch_source, source, tags, force_refresh): source
                for source in target_sources
                if source in self._handlers
            }

            for future in as_completed(futures):
                try:
                    items = future.result()
                    all_items.extend(items)
                except SourceError as e:
                    all_errors.append(e)

        return FetchNewsResponse(
            items=all_items,
            errors=all_errors if all_errors else None,
        )

    def _fetch_source(
        self,
        source: SourceType,
        tags: list[str] | None,
        force_refresh: bool,
    ) -> list[NewsItem]:
        """Fetch news from a single source.

        Uses cache-first strategy unless force_refresh is True.

        Args:
            source: The source to fetch from
            tags: Optional list of tags to filter by
            force_refresh: If True, bypass cache

        Returns:
            List of NewsItem from the source

        Raises:
            SourceError: If fetching fails
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self._cache.get(source)
            if cached is not None:
                return cached

        # Fetch from API
        handler = self._handlers[source]
        items = handler.fetch(tags=tags)

        # Update cache
        self._cache.set(source, items)

        return items
