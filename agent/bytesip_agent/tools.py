"""Tools for ByteSip Agent.

Provides fetch_news tool for retrieving IT/AI news from multiple sources.
"""

import json
from dataclasses import asdict
from typing import Any

from strands import tool

from .models import FetchNewsResponse, NewsItem, SourceError, SourceType


class FetchNewsClient:
    """Client for invoking the news fetcher Lambda function."""

    def __init__(
        self,
        lambda_client: Any,
        function_name: str = "bytesip-news-fetcher",
    ) -> None:
        """Initialize the client.

        Args:
            lambda_client: boto3 Lambda client
            function_name: Name of the Lambda function to invoke
        """
        self._lambda = lambda_client
        self._function_name = function_name

    def fetch(
        self,
        sources: list[SourceType] | None = None,
        tags: list[str] | None = None,
        force_refresh: bool = False,
    ) -> FetchNewsResponse:
        """Fetch news from the Lambda function.

        Args:
            sources: List of sources to fetch from (None = all)
            tags: Optional list of tags to filter by
            force_refresh: If True, bypass cache

        Returns:
            FetchNewsResponse containing items and any errors
        """
        payload = {
            "sources": sources,
            "tags": tags,
            "force_refresh": force_refresh,
        }

        response = self._lambda.invoke(
            FunctionName=self._function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        response_payload = json.loads(response["Payload"].read())
        return self._parse_response(response_payload)

    def _parse_response(self, data: dict) -> FetchNewsResponse:
        """Parse Lambda response into FetchNewsResponse.

        Args:
            data: Raw response dictionary from Lambda

        Returns:
            FetchNewsResponse object
        """
        items = [
            NewsItem(
                id=item["id"],
                title=item["title"],
                url=item["url"],
                summary=item["summary"],
                tags=item["tags"],
                source=item["source"],
            )
            for item in data.get("items", [])
        ]

        errors = None
        if data.get("errors"):
            errors = [
                SourceError(
                    source=error["source"],
                    error_type=error["error_type"],
                    message=error["message"],
                )
                for error in data["errors"]
            ]

        return FetchNewsResponse(items=items, errors=errors)


# Default client instance (can be replaced for testing)
_default_client: FetchNewsClient | None = None


def _get_default_client() -> FetchNewsClient:
    """Get or create the default FetchNewsClient."""
    global _default_client
    if _default_client is None:
        import boto3

        lambda_client = boto3.client("lambda")
        _default_client = FetchNewsClient(lambda_client=lambda_client)
    return _default_client


def set_client(client: FetchNewsClient | None) -> None:
    """Set the default FetchNewsClient (for testing).

    Args:
        client: FetchNewsClient instance or None to reset
    """
    global _default_client
    _default_client = client


@tool
def fetch_news(
    sources: list[str] | None = None,
    tags: list[str] | None = None,
    force_refresh: bool = False,
) -> dict:
    """Fetch IT/AI news from multiple sources.

    Retrieves the latest news articles from Qiita, Zenn, and GitHub.
    Results are cached for 24 hours to minimize API calls.

    Args:
        sources: List of sources to fetch from. Valid values: "qiita", "zenn", "github".
                 If not specified, fetches from all sources.
        tags: Optional list of technology tags to filter by (e.g., ["python", "rust"]).
        force_refresh: If True, bypass cache and fetch fresh data.

    Returns:
        Dictionary containing:
        - items: List of news items with id, title, url, summary, tags, source
        - errors: List of any errors that occurred (if any sources failed)
    """
    fetch_client = _get_default_client()

    response = fetch_client.fetch(
        sources=sources,
        tags=tags,
        force_refresh=force_refresh,
    )

    result: dict = {
        "items": [asdict(item) for item in response.items],
    }

    if response.errors:
        result["errors"] = [asdict(error) for error in response.errors]

    return result
