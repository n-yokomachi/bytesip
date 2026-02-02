"""ByteSip Streamlit UI.

A chat interface for the ByteSip IT/AI news curation agent.
"""

import json
import os
import uuid
from pathlib import Path

import boto3
import streamlit as st
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
AWS_REGION = os.environ.get("AWS_REGION", "")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")
AGENT_ID = os.environ.get("BYTESIP_AGENT_ID", "")

# Build ARN from components or use full ARN if provided
AGENT_ARN = os.environ.get("BYTESIP_AGENT_ARN", "")
if not AGENT_ARN and AWS_ACCOUNT_ID and AGENT_ID:
    AGENT_ARN = (
        f"arn:aws:bedrock-agentcore:{AWS_REGION}:{AWS_ACCOUNT_ID}"
        f":runtime/{AGENT_ID}"
    )

# Page configuration
st.set_page_config(
    page_title="ByteSip - IT/AIニュースエージェント",
    page_icon="☕",
    layout="centered",
)


def get_agentcore_client():
    """Get the Bedrock AgentCore client."""
    return boto3.client("bedrock-agentcore", region_name=AWS_REGION)


def invoke_agent(prompt: str, session_id: str) -> dict:
    """Invoke the ByteSip agent.

    Args:
        prompt: User message
        session_id: Session identifier for conversation continuity

    Returns:
        Agent response dictionary
    """
    if not AGENT_ARN:
        return {
            "result": "エージェントARNが設定されていません。"
            "BYTESIP_AGENT_ARNまたはAWS_ACCOUNT_IDを設定してください。",
            "error": "AGENT_ARN not configured",
        }

    client = get_agentcore_client()

    payload = {
        "prompt": prompt,
        "session_id": session_id,
    }

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            payload=json.dumps(payload),
        )

        # Parse the response
        response_payload = json.loads(response["response"].read())
        return response_payload
    except Exception as e:
        return {
            "result": f"エラーが発生しました: {e!s}",
            "error": str(e),
        }


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"


def display_chat_history():
    """Display chat message history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def process_user_input(user_input: str):
    """Process user input and get agent response."""
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("考え中..."):
            response = invoke_agent(user_input, st.session_state.session_id)

            # Extract the result
            if "result" in response:
                # Handle nested response structure
                result = response["result"]
                if isinstance(result, dict) and "content" in result:
                    # Extract text from content array
                    content = result.get("content", [])
                    if content and isinstance(content[0], dict):
                        assistant_message = content[0].get("text", str(result))
                    else:
                        assistant_message = str(result)
                else:
                    assistant_message = str(result)
            else:
                assistant_message = "応答を取得できませんでした。"

            st.markdown(assistant_message)

            # Show error if present
            if "error" in response:
                st.error(f"エラー詳細: {response['error']}")

    # Add assistant message to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_message,
    })


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()

    # Sidebar with title and session info
    with st.sidebar:
        st.title("☕ ByteSip")
        st.caption("IT/AIニュースキュレーションエージェント")

        st.divider()

        st.text(f"Session: {st.session_state.session_id[:12]}...")

        if st.button("新しいセッション"):
            st.session_state.messages = []
            st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"
            st.rerun()

        st.divider()
        st.markdown(
            """
            **使い方**
            - 「今日のニュースを教えて」
            - 「Pythonの記事を見せて」
            - 「Qiitaからのニュースだけ」
            - 「他のはある？」
            """
        )

    # Display chat history
    display_chat_history()

    # Chat input
    if user_input := st.chat_input("メッセージを入力..."):
        process_user_input(user_input)


if __name__ == "__main__":
    main()
