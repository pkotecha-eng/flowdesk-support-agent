import os
from typing import List, Dict, Generator

from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

from knowledge_base import SYSTEM_PROMPT, ESCALATION_KEYWORDS


def init_environment() -> str:
    load_dotenv()
    return os.getenv("OPENAI_API_KEY", "")


def init_client(api_key: str) -> OpenAI | None:
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []


def reset_conversation() -> None:
    st.session_state.messages = []


def has_escalation_keyword(text: str) -> bool:
    lower_text = text.lower()
    return any(keyword.lower() in lower_text for keyword in ESCALATION_KEYWORDS)


def stream_completion(
    client: OpenAI, messages: List[Dict[str, str]]
) -> Generator[str, None, None]:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        stream=True,
    )
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def main() -> None:
    st.set_page_config(page_title="FlowDesk Support", page_icon="💬")

    api_key = init_environment()
    client = init_client(api_key)

    st.title("💬 FlowDesk Support")

    with st.sidebar:
        st.header("🗂️ FlowDesk Help")
        st.markdown(
            "FlowDesk is a project management platform for B2B teams. "
            "Ask product, pricing, and account questions here."
        )
        if st.button("New Conversation"):
            reset_conversation()

    init_session_state()

    # Suggested question chips on first load
    if not st.session_state.messages:
        st.markdown("**Suggested questions**")
        cols = st.columns(3)
        suggestions = [
            "What does FlowDesk cost?",
            "How do I cancel my plan?",
            "What integrations do you support?",
        ]
        triggered_suggestion: str | None = None
        for col, suggestion in zip(cols, suggestions):
            with col:
                if st.button(suggestion):
                    triggered_suggestion = suggestion

        if triggered_suggestion:
            user_input = triggered_suggestion
        else:
            user_input = st.chat_input("Ask me anything about FlowDesk...")
    else:
        user_input = st.chat_input("Ask me anything about FlowDesk...")

    # Render existing conversation
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle new user input
    if user_input:
        # Escalation detection
        if has_escalation_keyword(user_input):
            st.warning(
                "🔴 This looks like it needs human attention — "
                "escalating to support team. Average wait: 2 min"
            )

        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            if not client:
                st.error(
                    "OpenAI API key is missing. Please set `OPENAI_API_KEY` in your `.env` file."
                )
            else:
                try:
                    conversation = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        *st.session_state.messages,
                    ]
                    streamed_text = st.write_stream(
                        stream_completion(client, conversation)
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": streamed_text}
                    )
                except Exception as e:
                    st.error(f"Something went wrong talking to the AI: {e}")


if __name__ == "__main__":
    main()

