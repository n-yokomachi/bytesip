"""GitHub API handler for fetching trending repositories."""

from datetime import datetime, timedelta

import requests

from ..models import NewsItem, SourceError, generate_news_id
from .base import BaseHandler


class GitHubHandler(BaseHandler):
    """Handler for fetching trending repositories from GitHub.

    Uses GitHub Search API to find recently pushed repositories
    with high star counts.
    """

    SEARCH_URL = "https://api.github.com/search/repositories"
    MIN_STARS = 100
    DAYS_LOOKBACK = 7

    def __init__(self, access_token: str) -> None:
        """Initialize GitHubHandler.

        Args:
            access_token: GitHub personal access token
        """
        self._access_token = access_token

    def fetch(self, tags: list[str] | None = None) -> list[NewsItem]:
        """Fetch trending repositories from GitHub.

        Args:
            tags: Optional list of topics to filter repositories

        Returns:
            List of NewsItem objects

        Raises:
            SourceError: If API request fails
        """
        try:
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/vnd.github+json",
            }
            params = self._build_params(tags)

            response = requests.get(
                self.SEARCH_URL,
                headers=headers,
                params=params,
            )

            if response.status_code == 403:
                remaining = response.headers.get("X-RateLimit-Remaining", "0")
                if remaining == "0":
                    raise SourceError(
                        source="github",
                        error_type="rate_limit",
                        message="GitHub API rate limit exceeded",
                    )

            response.raise_for_status()
            return self._parse_response(response.json())

        except SourceError:
            raise
        except Exception as e:
            raise SourceError(
                source="github",
                error_type="connection_error",
                message=str(e),
            )

    def _build_params(self, tags: list[str] | None) -> dict:
        """Build query parameters for GitHub Search API.

        Args:
            tags: Optional list of topics to filter

        Returns:
            Dictionary of query parameters
        """
        date_threshold = datetime.now() - timedelta(days=self.DAYS_LOOKBACK)
        date_str = date_threshold.strftime("%Y-%m-%d")

        query_parts = [
            f"pushed:>{date_str}",
            f"stars:>{self.MIN_STARS}",
        ]

        if tags:
            for tag in tags:
                query_parts.append(f"topic:{tag}")

        return {
            "q": " ".join(query_parts),
            "sort": "stars",
            "order": "desc",
            "per_page": 30,
        }

    def _parse_response(self, data: dict) -> list[NewsItem]:
        """Parse GitHub API response into NewsItem objects.

        Args:
            data: Response data from GitHub Search API

        Returns:
            List of NewsItem objects
        """
        news_items = []
        for repo in data.get("items", []):
            news_items.append(
                NewsItem(
                    id=generate_news_id("github", repo["full_name"]),
                    title=repo["full_name"],
                    url=repo["html_url"],
                    summary=repo.get("description") or "",
                    tags=repo.get("topics", []),
                    source="github",
                )
            )
        return news_items
