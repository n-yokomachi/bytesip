"""Zenn RSS feed handler for fetching articles."""

import feedparser

# Support both relative imports (local) and package imports (Lambda)
try:
    from ..models import NewsItem, SourceError, generate_news_id
    from .base import BaseHandler
except ImportError:
    from models import NewsItem, SourceError, generate_news_id
    from handlers.base import BaseHandler


class ZennHandler(BaseHandler):
    """Handler for fetching articles from Zenn RSS feeds.

    Uses Zenn's public RSS feeds to retrieve trending articles
    and topic-specific content.
    """

    BASE_URL = "https://zenn.dev"
    FEED_PATH = "/feed"

    def fetch(self, tags: list[str] | None = None) -> list[NewsItem]:
        """Fetch articles from Zenn RSS feed.

        Args:
            tags: Optional list of topics to filter articles.
                  If provided, uses topic-specific feed for first tag.

        Returns:
            List of NewsItem objects

        Raises:
            SourceError: If RSS parsing fails
        """
        try:
            feed_url = self._build_feed_url(tags)
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                raise SourceError(
                    source="zenn",
                    error_type="parse_error",
                    message=str(feed.bozo_exception),
                )

            return self._parse_feed(feed.entries)

        except SourceError:
            raise
        except Exception as e:
            raise SourceError(
                source="zenn",
                error_type="connection_error",
                message=str(e),
            ) from e

    def _build_feed_url(self, tags: list[str] | None) -> str:
        """Build RSS feed URL.

        Args:
            tags: Optional list of topics

        Returns:
            Feed URL string
        """
        if tags and len(tags) > 0:
            return f"{self.BASE_URL}/topics/{tags[0]}/feed"
        return f"{self.BASE_URL}{self.FEED_PATH}"

    def _parse_feed(self, entries: list) -> list[NewsItem]:
        """Parse RSS feed entries into NewsItem objects.

        Args:
            entries: List of feed entries from feedparser

        Returns:
            List of NewsItem objects
        """
        news_items = []
        for entry in entries:
            slug = self._extract_slug(entry.id)

            news_items.append(
                NewsItem(
                    id=generate_news_id("zenn", slug),
                    title=entry.title,
                    url=entry.link,
                    summary=getattr(entry, "summary", ""),
                    tags=[],
                    source="zenn",
                )
            )
        return news_items

    def _extract_slug(self, entry_id: str) -> str:
        """Extract article slug from entry ID.

        Args:
            entry_id: RSS entry ID (usually the article URL)

        Returns:
            Article slug
        """
        # Entry ID is typically the full URL
        # e.g., https://zenn.dev/user/articles/my-article
        parts = entry_id.rstrip("/").split("/")
        return parts[-1] if parts else entry_id
