"""Chat agent with tool_use loop — supports Azure OpenAI, Ollama, and Anthropic.

Drives the agentic loop: sends messages to the LLM, executes tool calls,
feeds results back, and yields text chunks for Streamlit.
"""
from __future__ import annotations

import json
import os
from collections.abc import Generator
from typing import Any

from .tools import TOOL_DEFINITIONS, dispatch, result_to_json

# ── Provider config ───────────────────────────────────────────────────────────

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = """You are a Hackathon Judge Assistant. You help hackathon organizers and judges evaluate and understand software project submissions.

You have access to the Hackathon Analyzer — a tool that clones GitHub/GitLab repositories and produces detailed technical analysis reports. Each report scores repos on a 1.0–10.0 scale across twelve dimensions:
- Code Quality (12%): linter issues, cyclomatic complexity, security findings
- Architecture (12%): architectural pattern, god files, CI/CD, Docker
- Promise vs Reality (12%): does the implementation match what the README claims?
- Testing (10%): test files, frameworks, test/code ratio, CI test step
- Originality (10%): GitHub search + Claude plagiarism verdict
- Build Success (8%): build system detected and dry-run succeeded
- Documentation (8%): README quality, license, changelog, docs
- Vision & Ambition (8%): problem clarity, solution novelty, scope ambition
- Tech Stack Novelty (6%): modern vs legacy dependency choices
- Hackathon Freshness (6%): was the repo created during the hackathon window?
- AI Integration (5%): depth and sophistication of AI/LLM usage
- Structure (3%): layout cleanliness, depth, naming

You can also search the web for information about hackathons, technologies, or open-source projects.

Guidelines:
- When a user gives you repo URLs, use analyze_repo or batch_analyze right away — don't ask for confirmation.
- When displaying analysis results, be concise. The UI renders score cards automatically; you just need to add your interpretation.
- For batch analyses, highlight the ranking and key differentiators between repos.
- When comparing repos, focus on the dimensions that matter most (Code Quality, Architecture, and Promise vs Reality have the highest weight at 12% each).
- Use web_search when users ask about external projects, hackathon events, or technologies you're not sure about.
- Be direct and opinionated — judges want clear recommendations, not hedging.
"""

# ── OpenAI-format tool definitions (for Ollama) ──────────────────────────────

def _openai_tools() -> list[dict]:
    """Convert our tool definitions to OpenAI function-calling format."""
    tools = []
    for t in TOOL_DEFINITIONS:
        tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        })
    return tools


# ── Clients ───────────────────────────────────────────────────────────────────

def _anthropic_client():
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
    return anthropic.Anthropic(api_key=api_key)


def _ollama_client():
    from openai import OpenAI
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    return OpenAI(base_url=base_url, api_key="ollama")


def _azure_client():
    from openai import AzureOpenAI
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set.")
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview"),
    )


# ── Stored tool results for UI rendering ──────────────────────────────────────

_last_tool_results: list[dict[str, Any]] = []


def get_last_tool_results() -> list[dict[str, Any]]:
    return _last_tool_results


# ── Anthropic agent loop ─────────────────────────────────────────────────────

def _run_anthropic(
    messages: list[dict],
    on_tool_start: Any = None,
    on_tool_end: Any = None,
) -> Generator[str, None, None]:
    """Agent loop using native Anthropic tool_use."""
    client = _anthropic_client()

    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        text_parts: list[str] = []
        tool_calls: list[dict] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        if text_parts:
            yield "".join(text_parts)

        if not tool_calls or response.stop_reason == "end_turn":
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tc in tool_calls:
            if on_tool_start:
                on_tool_start(tc["name"], tc["input"])

            result = dispatch(tc["name"], tc["input"])
            _last_tool_results.append({"tool": tc["name"], "input": tc["input"], "result": result})

            if on_tool_end:
                on_tool_end(tc["name"], result)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": result_to_json(result),
            })

        messages.append({"role": "user", "content": tool_results})


# ── OpenAI-compatible agent loop (Azure, Ollama, etc.) ────────────────────────

def _run_openai_compat(
    client,
    model: str,
    messages: list[dict],
    on_tool_start: Any = None,
    on_tool_end: Any = None,
) -> Generator[str, None, None]:
    """Agent loop using OpenAI-compatible API with native tool calling."""
    tools = _openai_tools()

    # Build message list with system prompt
    api_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, str):
            api_messages.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Flatten Anthropic-format content blocks to plain text
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block["text"])
                elif isinstance(block, dict) and block.get("type") == "tool_result":
                    text_parts.append(block.get("content", ""))
            if text_parts:
                api_messages.append({"role": role, "content": "\n".join(text_parts)})

    max_tool_rounds = 5
    for _ in range(max_tool_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            tools=tools,
            max_tokens=4096,
            temperature=0.7,
        )

        choice = response.choices[0]
        msg = choice.message

        # Yield any text content
        if msg.content:
            yield msg.content

        # Check for tool calls
        if not msg.tool_calls:
            break

        # Append assistant message with tool calls to history
        api_messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each tool call
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                tool_input = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                tool_input = {}

            if on_tool_start:
                on_tool_start(tool_name, tool_input)

            result = dispatch(tool_name, tool_input)
            _last_tool_results.append({"tool": tool_name, "input": tool_input, "result": result})

            if on_tool_end:
                on_tool_end(tool_name, result)

            # Append tool result message
            api_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_to_json(result),
            })
    else:
        yield "\n\n*Reached maximum tool call rounds.*"


# ── Public API ────────────────────────────────────────────────────────────────

def run(
    messages: list[dict],
    on_tool_start: Any = None,
    on_tool_end: Any = None,
) -> Generator[str, None, None]:
    """Run the agent loop. Yields text chunks for streaming display."""
    global _last_tool_results
    _last_tool_results = []

    provider = os.getenv("CHAT_PROVIDER", "azure")
    if provider == "anthropic":
        yield from _run_anthropic(messages, on_tool_start, on_tool_end)
    elif provider == "azure":
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
        yield from _run_openai_compat(_azure_client(), model, messages, on_tool_start, on_tool_end)
    else:  # ollama
        model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
        yield from _run_openai_compat(_ollama_client(), model, messages, on_tool_start, on_tool_end)
