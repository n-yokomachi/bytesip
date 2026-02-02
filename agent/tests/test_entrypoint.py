"""Tests for ByteSip Agent entrypoint.

TDD tests for AgentCore Runtime integration.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before and after each test."""
    import entrypoint

    entrypoint._memory_id = None
    yield
    entrypoint._memory_id = None


class TestInvokeEntrypoint:
    """Test the invoke entrypoint function."""

    @patch("entrypoint._create_agent")
    def test_invoke_returns_result_and_session_id(
        self, mock_create_agent: MagicMock
    ) -> None:
        """invoke should return result and session_id."""
        from entrypoint import invoke

        mock_agent = MagicMock()
        mock_agent.return_value.message = "ニュースを取得しました"
        mock_create_agent.return_value = mock_agent

        payload = {
            "prompt": "今日のニュースを教えて",
            "session_id": "test_session",
            "actor_id": "test_user",
        }

        result = invoke(payload)

        assert "result" in result
        assert "session_id" in result
        assert result["session_id"] == "test_session"
        mock_create_agent.assert_called_once_with(
            session_id="test_session",
            actor_id="test_user",
        )

    @patch("entrypoint._create_agent")
    def test_invoke_uses_default_prompt(self, mock_create_agent: MagicMock) -> None:
        """invoke should use default prompt when not provided."""
        from entrypoint import invoke

        mock_agent = MagicMock()
        mock_agent.return_value.message = "デフォルトの応答"
        mock_create_agent.return_value = mock_agent

        invoke({})

        mock_agent.assert_called_once_with("今日のニュースを教えて")

    @patch("entrypoint._create_agent")
    def test_invoke_generates_session_id_when_not_provided(
        self, mock_create_agent: MagicMock
    ) -> None:
        """invoke should generate session_id when not provided."""
        from entrypoint import invoke

        mock_agent = MagicMock()
        mock_agent.return_value.message = "応答"
        mock_create_agent.return_value = mock_agent

        result = invoke({"prompt": "テスト"})

        assert result["session_id"].startswith("session_")

    @patch("entrypoint._create_agent")
    def test_invoke_returns_error_on_exception(
        self, mock_create_agent: MagicMock
    ) -> None:
        """invoke should return error message when exception occurs."""
        from entrypoint import invoke

        mock_create_agent.side_effect = Exception("テスト用エラー")

        result = invoke({"prompt": "テスト", "session_id": "error_session"})

        assert "error" in result
        assert result["session_id"] == "error_session"
        assert "テスト用エラー" in result["result"]
        assert result["error"] == "テスト用エラー"


class TestCreateAgent:
    """Test the _create_agent function."""

    @patch("entrypoint.AgentCoreMemorySessionManager")
    @patch("entrypoint.BedrockModel")
    @patch("entrypoint.Agent")
    @patch("entrypoint._get_or_create_memory")
    def test_create_agent_configures_memory(
        self,
        mock_get_memory: MagicMock,
        mock_agent_class: MagicMock,
        mock_model_class: MagicMock,
        mock_session_manager_class: MagicMock,
    ) -> None:
        """_create_agent should configure AgentCore memory."""
        from entrypoint import _create_agent

        mock_get_memory.return_value = "test_memory_id"

        _create_agent(session_id="test_session", actor_id="test_actor")

        mock_session_manager_class.assert_called_once()
        call_kwargs = mock_session_manager_class.call_args[1]
        config = call_kwargs["agentcore_memory_config"]
        assert config.memory_id == "test_memory_id"
        assert config.session_id == "test_session"
        assert config.actor_id == "test_actor"

    @patch("entrypoint.AgentCoreMemorySessionManager")
    @patch("entrypoint.BedrockModel")
    @patch("entrypoint.Agent")
    @patch("entrypoint._get_or_create_memory")
    def test_create_agent_includes_fetch_news_tool(
        self,
        mock_get_memory: MagicMock,
        mock_agent_class: MagicMock,
        mock_model_class: MagicMock,
        mock_session_manager_class: MagicMock,
    ) -> None:
        """_create_agent should include fetch_news tool."""
        from bytesip_agent.tools import fetch_news
        from entrypoint import _create_agent

        mock_get_memory.return_value = "test_memory_id"

        _create_agent(session_id="test_session", actor_id="test_actor")

        mock_agent_class.assert_called_once()
        call_kwargs = mock_agent_class.call_args[1]
        assert fetch_news in call_kwargs["tools"]


class TestGetOrCreateMemory:
    """Test the _get_or_create_memory function."""

    @patch("entrypoint.MemoryClient")
    def test_creates_memory_when_not_exists(
        self, mock_memory_client_class: MagicMock
    ) -> None:
        """Should create new memory when none exists."""
        import entrypoint

        mock_client = MagicMock()
        mock_client.list_memories.return_value = {"memories": []}
        mock_client.create_memory.return_value = {"id": "new_memory_id"}
        mock_memory_client_class.return_value = mock_client

        result = entrypoint._get_or_create_memory()

        assert result == "new_memory_id"
        mock_client.create_memory.assert_called_once()

    @patch("entrypoint.MEMORY_NAME", "test-memory-name")
    @patch("entrypoint.MemoryClient")
    def test_reuses_existing_memory(
        self, mock_memory_client_class: MagicMock
    ) -> None:
        """Should reuse existing memory with matching name."""
        import entrypoint

        mock_client = MagicMock()
        mock_client.list_memories.return_value = {
            "memories": [
                {"name": "test-memory-name", "id": "existing_memory_id"},
            ]
        }
        mock_memory_client_class.return_value = mock_client

        result = entrypoint._get_or_create_memory()

        assert result == "existing_memory_id"
        mock_client.create_memory.assert_not_called()

    @patch("entrypoint.MemoryClient")
    def test_caches_memory_id(self, mock_memory_client_class: MagicMock) -> None:
        """Should cache memory_id after first call."""
        import entrypoint

        # Set cached memory_id for this test
        entrypoint._memory_id = "cached_memory_id"

        result = entrypoint._get_or_create_memory()

        assert result == "cached_memory_id"
        mock_memory_client_class.assert_not_called()
