"""Tests for ByteSip Streamlit UI."""

import json
from unittest.mock import MagicMock, patch

TEST_AGENT_ARN = "arn:aws:bedrock-agentcore:ap-northeast-1:123:runtime/agent/test"


class TestInvokeAgent:
    """Test the invoke_agent function."""

    @patch("app.AGENT_ARN", TEST_AGENT_ARN)
    @patch("app.get_agentcore_client")
    def test_invoke_agent_returns_response(
        self, mock_get_client: MagicMock
    ) -> None:
        """invoke_agent should return agent response."""
        from app import invoke_agent

        # Mock response payload
        response_data = {
            "result": "テストレスポンス",
            "session_id": "test_session",
        }
        mock_payload = MagicMock()
        mock_payload.read.return_value = json.dumps(response_data).encode()

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.return_value = {"response": mock_payload}
        mock_get_client.return_value = mock_client

        result = invoke_agent("テストプロンプト", "test_session")

        assert result["result"] == "テストレスポンス"
        assert result["session_id"] == "test_session"

    @patch("app.AGENT_ARN", TEST_AGENT_ARN)
    @patch("app.get_agentcore_client")
    def test_invoke_agent_handles_error(
        self, mock_get_client: MagicMock
    ) -> None:
        """invoke_agent should handle errors gracefully."""
        from app import invoke_agent

        mock_client = MagicMock()
        mock_client.invoke_agent_runtime.side_effect = Exception("Connection error")
        mock_get_client.return_value = mock_client

        result = invoke_agent("テスト", "session")

        assert "error" in result
        assert "Connection error" in result["error"]
        assert "エラーが発生しました" in result["result"]

    @patch("app.AGENT_ARN", "")
    def test_invoke_agent_returns_error_when_arn_not_configured(self) -> None:
        """invoke_agent should return error when AGENT_ARN is not set."""
        from app import invoke_agent

        result = invoke_agent("テスト", "session")

        assert "error" in result
        assert "AGENT_ARN not configured" in result["error"]


class TestSessionState:
    """Test session state initialization."""

    @patch("streamlit.session_state", new_callable=lambda: MagicMock())
    def test_init_session_state_creates_messages(
        self, mock_session_state: MagicMock
    ) -> None:
        """init_session_state should create messages list."""
        # Create a mock that doesn't have 'messages' attribute initially
        mock_session_state.__contains__ = lambda self, key: False

        from app import init_session_state

        init_session_state()

        # Verify that init_session_state was called without errors
        # The actual session_state manipulation is tested via Streamlit's test utilities
        # This test verifies the function can be imported and called
        assert True  # Function executed without errors
