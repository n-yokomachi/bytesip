"""Qiita API handler for fetching articles."""

import re

import requests

from ..models import NewsItem, SourceError, generate_news_id
from .base import BaseHandler


class QiitaHandler(BaseHandler):
    """Handler for fetching articles from Qiita API.

    Attributes:
        access_token: Qiita API access token
    """

    BASE_URL = "https://qiita.com/api/v2/items"
    SUMMARY_MAX_LENGTH = 200
    REQUEST_TIMEOUT = 10

    def __init__(self, access_token: str) -> None:
        """Initialize QiitaHandler.

        Args:
            access_token: Qiita API access token for authentication
        """
        self._access_token = access_token

    def fetch(self, tags: list[str] | None = None) -> list[NewsItem]:
        """Fetch articles from Qiita API.

        Args:
            tags: Optional list of tags to filter articles

        Returns:
            List of NewsItem objects

        Raises:
            SourceError: If API request fails
        """
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            params = self._build_params(tags)

            response = requests.get(
                self.BASE_URL,
                headers=headers,
                params=params,
                timeout=self.REQUEST_TIMEOUT,
            )

            if response.status_code == 403:
                raise SourceError(
                    source="qiita",
                    error_type="rate_limit",
                    message="Qiita API rate limit exceeded",
                )

            response.raise_for_status()
            return self._parse_response(response.json())

        except SourceError:
            raise
        except Exception as e:
            raise SourceError(
                source="qiita",
                error_type="connection_error",
                message=str(e),
            ) from e

    def _build_params(self, tags: list[str] | None) -> dict:
        """Build query parameters for Qiita API.

        Args:
            tags: Optional list of tags to filter

        Returns:
            Dictionary of query parameters
        """
        params: dict = {"per_page": 30}

        if tags:
            tag_query = " OR ".join(f"tag:{tag}" for tag in tags)
            params["query"] = tag_query

        return params

    def _parse_response(self, items: list[dict]) -> list[NewsItem]:
        """Parse Qiita API response into NewsItem objects.

        Args:
            items: List of article data from Qiita API

        Returns:
            List of NewsItem objects
        """
        news_items = []
        for item in items:
            summary = self._strip_markdown(item.get("body", ""))
            tags = [tag["name"] for tag in item.get("tags", [])]

            news_items.append(
                NewsItem(
                    id=generate_news_id("qiita", item["id"]),
                    title=item["title"],
                    url=item["url"],
                    summary=summary[: self.SUMMARY_MAX_LENGTH],
                    tags=tags,
                    source="qiita",
                )
            )
        return news_items

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown formatting from text.

        Args:
            text: Markdown text to clean

        Returns:
            Plain text without markdown symbols
        """
        # Remove headings
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        # Remove bold/italic
        text = re.sub(r"\*+([^*]+)\*+", r"\1", text)
        # Remove inline code
        text = re.sub(r"`([^`]+)`", r"\1", text)
        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        # Remove links but keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
        # Clean up whitespace
        text = re.sub(r"\n{2,}", "\n", text)
        return text.strip()
