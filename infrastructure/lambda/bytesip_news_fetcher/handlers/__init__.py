"""External source handlers for ByteSip News Fetcher.

This module provides handlers for fetching news from various sources:
- QiitaHandler: Qiita API integration
- ZennHandler: Zenn RSS feed integration
- GitHubHandler: GitHub trending repositories
"""

from .base import BaseHandler
from .github import GitHubHandler
from .qiita import QiitaHandler
from .zenn import ZennHandler

__all__ = [
    "BaseHandler",
    "QiitaHandler",
    "ZennHandler",
    "GitHubHandler",
]
