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
MEMORY_NAME = os.environ.get("BYTESIP_MEMORY_NAME", "bytesip-agent-memory")
# Memory ID from toolkit deployment (set by agentcore deploy)
AGENTCORE_MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID")

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

## 制約
- 1回の提案は最大10件まで（各ソース最大10件、合計最大30件）
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
    """
    # Extract parameters from payload
    user_message = payload.get("prompt", "今日のニュースを教えて")
    session_id = payload.get(
        "session_id", f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    actor_id = payload.get("actor_id", "default_user")

    # Create agent for this session
    agent = _create_agent(session_id=session_id, actor_id=actor_id)

    # Process the user message
    result = agent(user_message)

    return {
        "result": result.message,
        "session_id": session_id,
    }


if __name__ == "__main__":
    app.run()
