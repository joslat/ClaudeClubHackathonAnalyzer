"""Tool definitions (JSON schema) and dispatch for the chat agent."""
from __future__ import annotations

import json
from typing import Any

from . import analyzer_bridge, web_search


# ── Tool schemas (passed to Claude) ──────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "analyze_repo",
        "description": (
            "Analyze a single GitHub or GitLab repository using the Hackathon Analyzer. "
            "Clones the repo, runs multi-dimensional analysis (code quality, architecture, "
            "promise vs reality, testing, originality, build, documentation, vision & ambition, "
            "tech stack novelty, hackathon freshness, AI integration, structure), and returns "
            "a scored report with a 1.0-10.0 total score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full GitHub or GitLab repository URL, e.g. https://github.com/owner/repo",
                },
                "skip_build": {
                    "type": "boolean",
                    "description": "Skip the build attempt step (faster). Default false.",
                    "default": False,
                },
                "skip_plagiarism": {
                    "type": "boolean",
                    "description": "Skip the originality/plagiarism check (faster, no GitHub API calls). Default false.",
                    "default": False,
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "batch_analyze",
        "description": (
            "Analyze multiple GitHub/GitLab repositories at once. Runs the full analysis "
            "pipeline on each and generates a summary report comparing all repos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of repository URLs to analyze.",
                    "minItems": 1,
                },
                "skip_build": {
                    "type": "boolean",
                    "description": "Skip build attempts for all repos. Default false.",
                    "default": False,
                },
                "skip_plagiarism": {
                    "type": "boolean",
                    "description": "Skip plagiarism checks for all repos. Default false.",
                    "default": False,
                },
            },
            "required": ["urls"],
        },
    },
    {
        "name": "list_reports",
        "description": (
            "List all previously generated analysis reports. Returns per-repo reports "
            "and summary reports with their slugs, paths, and modification dates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_report",
        "description": (
            "Read the full content of a previously generated report by its slug "
            "(e.g. 'tiangolo-fastapi'). Use this to answer detailed questions about "
            "a specific repo's analysis results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "Report slug, e.g. 'owner-reponame'. Use list_reports to find available slugs.",
                },
            },
            "required": ["slug"],
        },
    },
    {
        "name": "generate_summary",
        "description": (
            "Generate or update the summary report from all existing per-repo reports. "
            "The summary includes a leaderboard, statistics, and dimension comparison table. "
            "Use this after analyzing repos, or when the user asks for a cross-repo comparison."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web using DuckDuckGo. Use this to look up information about "
            "hackathons, open-source projects, technologies, or anything else the user asks about."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 5).",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["query"],
        },
    },
]


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch(tool_name: str, tool_input: dict[str, Any]) -> Any:
    """Execute a tool call and return the result as a JSON-serializable value."""
    try:
        if tool_name == "analyze_repo":
            return analyzer_bridge.analyze_repo(
                url=tool_input["url"],
                skip_build=tool_input.get("skip_build", False),
                skip_plagiarism=tool_input.get("skip_plagiarism", False),
            )

        elif tool_name == "batch_analyze":
            return analyzer_bridge.batch_analyze(
                urls=tool_input["urls"],
                skip_build=tool_input.get("skip_build", False),
                skip_plagiarism=tool_input.get("skip_plagiarism", False),
            )

        elif tool_name == "list_reports":
            return analyzer_bridge.list_reports()

        elif tool_name == "read_report":
            return analyzer_bridge.read_report(slug=tool_input["slug"])

        elif tool_name == "generate_summary":
            return analyzer_bridge.generate_summary()

        elif tool_name == "web_search":
            return web_search.search(
                query=tool_input["query"],
                max_results=tool_input.get("max_results", 5),
            )

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except KeyError as exc:
        return {"error": f"Missing required parameter {exc} for tool '{tool_name}'"}
    except Exception as exc:
        return {"error": f"Tool '{tool_name}' failed: {exc}"}


def result_to_json(result: Any) -> str:
    """Serialize a tool result to a JSON string for Claude."""
    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": f"Serialization failed: {exc}"})
