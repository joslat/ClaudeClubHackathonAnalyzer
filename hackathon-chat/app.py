"""Hackathon Analyzer Chat — Streamlit entry point.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from agent import chat_agent, formatters

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Hackathon Analyzer Chat",
    page_icon="🏆",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏆 Hackathon Analyzer")
    st.caption("Chat with an AI agent to analyze hackathon submissions.")

    st.divider()
    st.subheader("Analysis Options")
    skip_build = st.toggle("Skip build attempts", value=False, help="Faster — skips dry-run build step.")
    skip_plagiarism = st.toggle("Skip plagiarism check", value=False, help="Faster — skips GitHub code search.")

    st.divider()
    st.subheader("LLM Provider")
    provider_options = ["azure", "ollama", "anthropic"]
    default_provider = os.getenv("CHAT_PROVIDER", "azure")
    default_index = provider_options.index(default_provider) if default_provider in provider_options else 0
    provider = st.selectbox(
        "Provider",
        options=provider_options,
        index=default_index,
        format_func=lambda x: {"azure": "Azure OpenAI (GPT-4.1)", "ollama": "Ollama (local)", "anthropic": "Anthropic (Claude)"}[x],
        help="Azure = cloud GPT-4.1. Ollama = free local model. Anthropic = Claude API.",
    )
    os.environ["CHAT_PROVIDER"] = provider

    if provider == "azure":
        azure_endpoint = st.text_input(
            "Azure Endpoint",
            value=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            help="Azure OpenAI endpoint URL.",
        )
        if azure_endpoint:
            os.environ["AZURE_OPENAI_ENDPOINT"] = azure_endpoint
        azure_key = st.text_input(
            "Azure API Key",
            value=os.getenv("AZURE_OPENAI_API_KEY", ""),
            type="password",
            help="Can also be set via AZURE_OPENAI_API_KEY env var.",
        )
        if azure_key:
            os.environ["AZURE_OPENAI_API_KEY"] = azure_key
        azure_deployment = st.text_input(
            "Deployment name",
            value=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1"),
            help="Deployment name in Azure AI Foundry.",
        )
        os.environ["AZURE_OPENAI_DEPLOYMENT"] = azure_deployment
    elif provider == "ollama":
        ollama_url = st.text_input(
            "Ollama URL",
            value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            help="Ollama OpenAI-compatible endpoint.",
        )
        os.environ["OLLAMA_BASE_URL"] = ollama_url
        ollama_model = st.text_input(
            "Ollama Model",
            value=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
            help="Model name as shown by 'ollama list'.",
        )
        os.environ["OLLAMA_MODEL"] = ollama_model
    else:
        api_key_input = st.text_input(
            "Anthropic API Key",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            type="password",
            help="Can also be set via ANTHROPIC_API_KEY env var.",
        )
        if api_key_input:
            os.environ["ANTHROPIC_API_KEY"] = api_key_input

    st.divider()
    st.subheader("Analyzer Config")
    hackanalyze_path = st.text_input(
        "hackanalyze binary path",
        value=os.getenv("HACKANALYZE_PATH", "hackanalyze"),
        help="Path to the hackanalyze CLI. Defaults to 'hackanalyze' on PATH.",
    )
    if hackanalyze_path:
        os.environ["HACKANALYZE_PATH"] = hackanalyze_path

    reports_dir = st.text_input(
        "Reports directory",
        value=os.getenv("HACKANALYZE_REPORTS_DIR", ""),
        placeholder="Auto-detected",
        help="Path to hackathon-analyzer/reports. Leave blank for auto-detection.",
    )
    if reports_dir:
        os.environ["HACKANALYZE_REPORTS_DIR"] = reports_dir

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.tool_results = []
        st.rerun()

    provider_labels = {
        "azure": f"Azure OpenAI ({os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4.1')})",
        "ollama": f"Ollama ({os.getenv('OLLAMA_MODEL', 'gpt-oss:20b')})",
        "anthropic": "Claude Sonnet 4.6",
    }
    st.caption(f"Using {provider_labels.get(provider, provider)} + Streamlit")

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# tool_results: list of (tool_name, result, message_index) tuples
# stored so we can render visualizations inline with chat history
if "tool_results" not in st.session_state:
    st.session_state.tool_results = []

# ── Render chat history ───────────────────────────────────────────────────────

st.title("Hackathon Analyzer Chat")

# Welcome message on first load
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Hello! I'm your Hackathon Judge Assistant. I can:\n\n"
            "- **Analyze repos** — just paste a GitHub URL and I'll run a full technical analysis\n"
            "- **Compare submissions** — give me multiple URLs and I'll rank them\n"
            "- **Read past reports** — ask me about any previously analyzed repo\n"
            "- **Search the web** — I can look up anything about projects, technologies, or hackathons\n\n"
            "Try: *\"Analyze https://github.com/tiangolo/fastapi\"*"
        )

# Replay previous messages
for i, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    if role not in ("user", "assistant"):
        continue
    with st.chat_message(role):
        # For assistant messages, content may be a list of blocks
        content = msg.get("content", "")
        if isinstance(content, str):
            st.markdown(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    st.markdown(block["text"])
                elif hasattr(block, "type") and block.type == "text":
                    st.markdown(block.text)

    # Render any tool visualizations attached to this message index
    for tr in st.session_state.tool_results:
        if tr["message_index"] == i:
            with st.container():
                formatters.render_tool_result(tr["tool"], tr["result"])

# ── Chat input ────────────────────────────────────────────────────────────────

user_input = st.chat_input("Ask me to analyze a repo, compare submissions, search the web...")

if user_input:
    # Guard: require credentials for the selected provider
    active_provider = os.getenv("CHAT_PROVIDER", "azure")
    if active_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        st.error("Please set your Anthropic API Key in the sidebar before chatting.")
        st.stop()
    if active_provider == "azure" and (not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_API_KEY")):
        st.error("Please set your Azure OpenAI endpoint and API key in the sidebar.")
        st.stop()

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Append to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    message_index = len(st.session_state.messages) - 1

    # Inject sidebar toggles into the latest user message as context
    # (We do this by prepending a system note — simpler than modifying system prompt dynamically)
    agent_messages = list(st.session_state.messages)
    if skip_build or skip_plagiarism:
        flags = []
        if skip_build:
            flags.append("skip_build=true")
        if skip_plagiarism:
            flags.append("skip_plagiarism=true")
        # Inject as a note appended to the user's last message
        agent_messages[-1] = {
            "role": "user",
            "content": user_input + f"\n\n[User has toggled: {', '.join(flags)} — apply these to any analysis you run.]",
        }

    # Run agent with tool feedback
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        tool_status_placeholder = st.empty()

        collected_tool_results: list[dict] = []

        def on_tool_start(tool_name: str, tool_input: dict) -> None:
            label = {
                "analyze_repo": f"Analyzing `{tool_input.get('url', '')}`...",
                "batch_analyze": f"Analyzing {len(tool_input.get('urls', []))} repos...",
                "list_reports": "Listing reports...",
                "read_report": f"Reading report `{tool_input.get('slug', '')}`...",
                "web_search": f"Searching web for: *{tool_input.get('query', '')}*",
            }.get(tool_name, f"Running {tool_name}...")
            tool_status_placeholder.status(label, state="running")

        def on_tool_end(tool_name: str, result: dict) -> None:
            tool_status_placeholder.empty()
            collected_tool_results.append({"tool": tool_name, "result": result})

        try:
            for chunk in chat_agent.run(
                messages=agent_messages,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
            ):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

        except ValueError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Agent error: {e}")
            st.stop()

        # Render tool visualizations inline
        for tr in collected_tool_results:
            formatters.render_tool_result(tr["tool"], tr["result"])

    # Save assistant response to history
    assistant_message_index = len(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Save tool results for history replay
    for tr in collected_tool_results:
        st.session_state.tool_results.append({
            "message_index": assistant_message_index,
            "tool": tr["tool"],
            "result": tr["result"],
        })
