"""Streamlit renderers for tool results.

Called after a tool completes to display structured visualizations
(score cards, dimension tables, report previews, search results).
"""
from __future__ import annotations

from typing import Any

import streamlit as st

# Score color thresholds
def _score_color(score: float) -> str:
    if score >= 8.0:
        return "🟢"
    elif score >= 6.0:
        return "🟡"
    elif score >= 4.0:
        return "🟠"
    else:
        return "🔴"


def render_analyze_result(result: dict[str, Any]) -> None:
    """Render the result of analyze_repo."""
    url = result.get("url", "unknown")
    slug = result.get("slug", "")
    success = result.get("success", False)
    score = result.get("total_score")
    dimensions = result.get("dimensions", [])

    if not success:
        st.error(f"Analysis failed for `{slug}`")
        cli_output = result.get("cli_output", "")
        if cli_output:
            with st.expander("Error details"):
                st.code(cli_output)
        return

    # Header
    st.markdown(f"**Analysis complete:** [{slug}]({url})")

    if score is not None:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric(
                label="Total Score",
                value=f"{_score_color(score)} {score:.1f} / 10",
            )
        with col2:
            st.progress(score / 10.0)

    # Dimension table
    if dimensions:
        st.markdown("**Dimension Scores**")
        rows = []
        for d in dimensions:
            s = d.get("score", 0.0)
            bar = "█" * int(s * 10) + "░" * (10 - int(s * 10))
            rows.append({
                "Dimension": d.get("name", ""),
                "Weight": d.get("weight", ""),
                "Score": f"{s:.2f}",
                "Visual": bar,
                "Rationale": d.get("rationale", ""),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    # Report preview
    report_text = result.get("report_text")
    if report_text:
        with st.expander("Full Report"):
            st.markdown(report_text)


def render_batch_result(result: dict[str, Any]) -> None:
    """Render the result of batch_analyze."""
    success = result.get("success", False)
    results = result.get("results", [])

    if not success:
        st.error("Batch analysis failed.")
        with st.expander("CLI output"):
            st.code(result.get("cli_output", ""))
        return

    st.markdown(f"**Batch analysis complete — {len(results)} repo(s)**")

    # Ranking table
    scored = [(r["slug"], r.get("total_score")) for r in results if r.get("total_score") is not None]
    scored.sort(key=lambda x: x[1] or 0, reverse=True)

    if scored:
        st.markdown("**Rankings**")
        rank_rows = []
        for rank, (slug, score) in enumerate(scored, 1):
            rank_rows.append({
                "Rank": rank,
                "Repo": slug,
                "Score": f"{_score_color(score)} {score:.1f}",
            })
        st.dataframe(rank_rows, use_container_width=True, hide_index=True)

    # Individual cards
    for r in results:
        with st.expander(f"{r['slug']} — {r.get('total_score', 'N/A')}"):
            render_analyze_result(r)

    # Summary report link
    summary_path = result.get("summary_report_path")
    if summary_path:
        st.info(f"Summary report saved to: `{summary_path}`")


def render_list_reports(result: dict[str, Any]) -> None:
    """Render the result of list_reports."""
    per_repo = result.get("per_repo", [])
    summaries = result.get("summaries", [])

    if not per_repo and not summaries:
        st.info(f"No reports found in `{result.get('reports_dir', 'reports/')}`.")
        return

    if per_repo:
        st.markdown(f"**Per-repo reports ({len(per_repo)})**")
        st.dataframe(
            [{"Repo": r["slug"], "Modified": r["modified"], "Path": r["path"]} for r in per_repo],
            use_container_width=True,
            hide_index=True,
        )

    if summaries:
        st.markdown(f"**Summary reports ({len(summaries)})**")
        st.dataframe(
            [{"File": s["name"], "Modified": s["modified"]} for s in summaries],
            use_container_width=True,
            hide_index=True,
        )


def render_read_report(result: dict[str, Any]) -> None:
    """Render the result of read_report."""
    if not result.get("found"):
        st.warning(result.get("error", "Report not found."))
        return

    score = result.get("total_score")
    slug = result.get("slug", "")

    if score is not None:
        st.metric(label=f"Score — {slug}", value=f"{_score_color(score)} {score:.1f} / 10")

    text = result.get("text", "")
    if text:
        with st.expander("Report content", expanded=True):
            st.markdown(text)


def render_web_search(result: list[dict[str, str]]) -> None:
    """Render web search results."""
    if not result:
        st.info("No results found.")
        return

    st.markdown(f"**{len(result)} web result(s)**")
    for r in result:
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        if url:
            st.markdown(f"**[{title}]({url})**")
        else:
            st.markdown(f"**{title}**")
        if snippet:
            st.caption(snippet)
        st.divider()


# ── Main dispatch ─────────────────────────────────────────────────────────────

def render_tool_result(tool_name: str, result: Any) -> None:
    """Dispatch rendering based on tool name."""
    if tool_name == "analyze_repo":
        render_analyze_result(result)
    elif tool_name == "batch_analyze":
        render_batch_result(result)
    elif tool_name == "list_reports":
        render_list_reports(result)
    elif tool_name == "read_report":
        render_read_report(result)
    elif tool_name == "web_search":
        render_web_search(result)
