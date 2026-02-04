"""Lambda handler for ByteSip News Fetcher.

This is the entry point for the Lambda function that fetches news
from external sources (Qiita, Zenn, GitHub).
"""

from dataclasses import asdict
from typing import Any

# Support both relative imports (local) and package imports (Lambda)
try:
    from .cache_manager import CacheManager
    from .config import get_dynamodb_config, get_external_api_config
    from .handlers.github import GitHubHandler
    from .handlers.qiita import QiitaHandler
    from .handlers.zenn import ZennHandler
    from .news_fetcher import NewsFetcher
except ImportError:
    from cache_manager import CacheManager
    from config import get_dynamodb_config, get_external_api_config
    from handlers.github import GitHubHandler
    from handlers.qiita import QiitaHandler
    from handlers.zenn import ZennHandler
    from news_fetcher import NewsFetcher


def _create_news_fetcher() -> NewsFetcher:
    """Create and configure the NewsFetcher instance."""
    # Get configurations
    dynamodb_config = get_dynamodb_config()
    api_config = get_external_api_config()

    # Create cache manager
    cache_manager = CacheManager(
        table_name=dynamodb_config.table_name,
        endpoint_url=dynamodb_config.endpoint_url,
        region_name=dynamodb_config.region_name,
    )

    # Create handlers
    handlers = {}

    if api_config.qiita_access_token:
        handlers["qiita"] = QiitaHandler(access_token=api_config.qiita_access_token)

    handlers["zenn"] = ZennHandler()

    if api_config.github_access_token:
        handlers["github"] = GitHubHandler(access_token=api_config.github_access_token)

    return NewsFetcher(cache_manager=cache_manager, handlers=handlers)


# Global fetcher instance for Lambda warm starts
_fetcher: NewsFetcher | None = None


def _get_fetcher() -> NewsFetcher:
    """Get or create the NewsFetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = _create_news_fetcher()
    return _fetcher


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda entry point for news fetching.

    Args:
        event: Lambda event containing request parameters:
            - sources: Optional list of sources to fetch from
            - tags: Optional list of tags to filter by
            - force_refresh: Optional boolean to bypass cache

    Returns:
        Response with news items or error information
    """
    # Parse input parameters
    sources = event.get("sources")
    tags = event.get("tags")
    force_refresh = event.get("force_refresh", False)

    # Get the fetcher and execute
    fetcher = _get_fetcher()

    try:
        response = fetcher.fetch(
            sources=sources,
            tags=tags,
            force_refresh=force_refresh,
        )

        # Convert to JSON-serializable format
        result = {
            "items": [asdict(item) for item in response.items],
            "errors": [asdict(error) for error in response.errors]
            if response.errors
            else None,
        }

        return result

    except Exception as e:
        return {
            "items": [],
            "errors": [
                {
                    "source": "system",
                    "error_type": "internal_error",
                    "message": str(e),
                }
            ],
        }
