"""ByteSip Agent entrypoint for AgentCore Runtime.

This module provides the main entrypoint for deploying the ByteSip agent
to Amazon Bedrock AgentCore Runtime.
"""

import os
from datetime import datetime

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from strands import Agent
from strands.models import BedrockModel

from bytesip_agent.tools import fetch_news

# Configuration from environment variables
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
MEMORY_NAME = os.environ.get("BYTESIP_MEMORY_NAME", "bytesip_mem")
# Memory ID from toolkit deployment (set by agentcore deploy)
# Fallback to known memory ID if not provided
AGENTCORE_MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "bytesip_mem-Y05j1y8kDc")

# System prompt for the ByteSip agent
SYSTEM_PROMPT = """\
あなたは「ByteSip」という名前のIT/AIニュースキュレーションエージェントです。
エンジニアが朝のコーヒータイムに効率的にテック情報をキャッチアップできるよう、
Qiita・Zenn・GitHubから最新のニュースを取得して提案します。

## あなたの役割
- ユーザーのリクエストに基づいてニュースを取得・提案する
- ソース（Qiita/Zenn/GitHub）、技術タグ、件数のフィルタリングに対応する
- 一度提案したニュースは重複して提案しない
- ユーザーが「他のはある？」と聞いたら、まだ提案していないニュースを提案する

## ニュースの提案形式
各ニュースは以下の形式で提案してください：
- **タイトル**: [記事タイトル](URL)
- **要約**: 記事の概要
- **タグ**: 関連技術タグ
- **ソース**: Qiita/Zenn/GitHub

## 提案件数のルール
- 各ソース（Qiita/Zenn/GitHub）から均等に提案する（例: 3ソースなら各3〜4件）
- 合計の上限は10件
- ユーザーが件数を指定した場合はそれに従うが、ソース間の均等配分は維持する

## GitHubリポジトリの選定基準
- 誰もが知るような超有名プロジェクト（例: linux, react, vue, angular, tensorflow,
  pytorch, kubernetes, docker, vscode, rust, go, swift, node, deno, next.js,
  rails, django, flask, spring-boot, elasticsearch など）は提案から除外する
- 新しいプロジェクトや、最近注目を集めている成長中のリポジトリを優先して提案する
- 判断に迷う場合は、スター数が少なめでも話題性のあるものを選ぶ

## 制約
- キャッシュされたニュースがない場合や全て提案済みの場合は、
  「現在提案できるニュースがありません」と伝える
- エラーが発生した場合は、ユーザーにわかりやすく説明する

## 使用可能なツール
- fetch_news: Qiita/Zenn/GitHubからニュースを取得する
  - sources: 取得元の指定（省略時は全ソース）
  - tags: 技術タグでフィルタリング
  - force_refresh: キャッシュを無視して最新データを取得
"""

# Initialize the AgentCore app
app = BedrockAgentCoreApp()

# Global variables for lazy initialization
_memory_id: str | None = None
_agent: Agent | None = None


def _get_or_create_memory() -> str:
    """Get or create the AgentCore Memory instance.

    When deployed via agentcore toolkit, uses the pre-configured memory ID.
    For local development, falls back to creating a new memory.
    """
    global _memory_id
    if _memory_id is None:
        # Use toolkit-provided memory ID if available (production)
        if AGENTCORE_MEMORY_ID:
            _memory_id = AGENTCORE_MEMORY_ID
        else:
            # Local development: create or find memory
            client = MemoryClient(region_name=AWS_REGION)

            # Try to find existing memory by name
            memories = client.list_memories()
            for memory in memories.get("memories", []):
                if memory.get("name") == MEMORY_NAME:
                    _memory_id = memory["id"]
                    break

            # Create new memory if not found
            if _memory_id is None:
                memory = client.create_memory(
                    name=MEMORY_NAME,
                    description="ByteSip agent memory for session management",
                )
                _memory_id = memory["id"]

    return _memory_id


def _create_agent(session_id: str, actor_id: str) -> Agent:
    """Create a new agent instance with session management.

    Args:
        session_id: Unique session identifier
        actor_id: User/actor identifier

    Returns:
        Configured Strands Agent instance
    """
    memory_id = _get_or_create_memory()

    # Configure AgentCore memory
    memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=actor_id,
    )

    # Create session manager
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=memory_config,
        region_name=AWS_REGION,
    )

    # Configure Bedrock model with JP cross-region inference
    model = BedrockModel(
        model_id="jp.anthropic.claude-haiku-4-5-20251001-v1:0",
        region_name=AWS_REGION,
    )

    # Create agent with tools and memory
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[fetch_news],
        session_manager=session_manager,
    )


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Process incoming requests to the ByteSip agent.

    Args:
        payload: Request payload containing:
            - prompt: User message
            - session_id: Optional session identifier
            - actor_id: Optional actor/user identifier

    Returns:
        Response dictionary containing:
            - result: Agent's response message
            - session_id: Session identifier used
            - error: Error message (only present on failure)
    """
    # Extract parameters from payload
    user_message = payload.get("prompt", "今日のニュースを教えて")
    session_id = payload.get(
        "session_id", f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    actor_id = payload.get("actor_id", "default_user")

    try:
        # Create agent for this session
        agent = _create_agent(session_id=session_id, actor_id=actor_id)

        # Process the user message
        result = agent(user_message)

        return {
            "result": result.message,
            "session_id": session_id,
        }
    except Exception as e:
        return {
            "result": f"エラーが発生しました: {e!s}",
            "session_id": session_id,
            "error": str(e),
        }


if __name__ == "__main__":
    app.run()
