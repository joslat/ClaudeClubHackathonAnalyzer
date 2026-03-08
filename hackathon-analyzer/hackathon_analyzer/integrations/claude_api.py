"""Thin Anthropic Claude API wrapper for architecture and plagiarism analysis."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-opus-4-5"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
    ) -> Optional[str]:
        """Send a prompt to Claude and return the response text.

        Returns None on any error (so callers can degrade gracefully).
        """
        try:
            client = self._get_client()
            messages = [{"role": "user", "content": prompt}]
            kwargs = {
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as exc:
            logger.warning("Claude API call failed: %s", exc)
            return None

    def analyze_architecture(self, structure_summary: str, language: str) -> Optional[str]:
        system = (
            "You are a senior software architect reviewing a hackathon project submission. "
            "Be concise, technical, and fair. 2-3 paragraphs maximum."
        )
        prompt = (
            f"Analyze the architecture of this {language} project based on its file structure. "
            f"Identify the architectural pattern (MVC, layered, microservice, script, etc.), "
            f"comment on design quality, and note any concerns.\n\n"
            f"Project structure:\n{structure_summary}"
        )
        return self.complete(prompt, system=system, max_tokens=512)

    def assess_plagiarism(
        self,
        snippets: list[str],
        matches: list[dict],
    ) -> Optional[str]:
        system = (
            "You are evaluating hackathon submissions for code originality. "
            "Be fair — common boilerplate (setup.py, hello world, standard patterns) "
            "should NOT be flagged. Only flag substantive copied logic."
        )
        snippet_text = "\n\n---\n\n".join(
            f"Snippet {i+1}:\n```\n{s[:500]}\n```" for i, s in enumerate(snippets)
        )
        match_text = "\n".join(
            f"- {m['repo']}: {m['url']}" for m in matches[:10]
        ) if matches else "No GitHub matches found."

        prompt = (
            f"These code snippets were found in a hackathon submission:\n\n{snippet_text}\n\n"
            f"GitHub code search found these potential matches:\n{match_text}\n\n"
            f"Assess the plagiarism risk. Consider:\n"
            f"- Are these snippets likely independently written or copied?\n"
            f"- Is the matched code trivial boilerplate or substantive logic?\n"
            f"End with a verdict: RISK: LOW, RISK: MEDIUM, or RISK: HIGH"
        )
        return self.complete(prompt, system=system, max_tokens=512)

    def assess_promise_reality(
        self,
        readme_text: str,
        codebase_summary: str,
    ) -> Optional[str]:
        """Ask Claude to assess whether the codebase matches README claims.

        Expected response format includes ALIGNMENT_SCORE: X.XX on its own line.
        """
        system = (
            "You are a senior hackathon judge evaluating whether a project's "
            "implementation matches its README claims. Be fair but rigorous. "
            "Look for concrete code evidence supporting each claim."
        )
        prompt = (
            "Compare this project's README (what it claims to do) with its actual "
            "codebase summary (what it really implements). Assess alignment.\n\n"
            "## README (Project Claims)\n\n"
            f"{readme_text[:3000]}\n\n"
            "## Codebase Summary (Actual Implementation)\n\n"
            f"{codebase_summary[:3000]}\n\n"
            "## Instructions\n\n"
            "1. List the key claims/features promised in the README.\n"
            "2. For each claim, state whether the codebase supports it (SUPPORTED / UNSUPPORTED / PARTIAL).\n"
            "3. Provide an overall alignment score.\n\n"
            "End your response with exactly this line:\n"
            "ALIGNMENT_SCORE: X.XX\n"
            "(where X.XX is between 0.00 and 1.00, where 1.00 = perfect alignment)"
        )
        return self.complete(prompt, system=system, max_tokens=1024)

    def assess_vision(self, readme_text: str) -> Optional[str]:
        """Ask Claude to score a project's vision/ambition based on its README.

        Expected response format includes four scores on separate lines:
        PROBLEM_CLARITY: X.XX
        SOLUTION_NOVELTY: X.XX
        SCOPE_AMBITION: X.XX
        AUDIENCE_SPECIFICITY: X.XX
        """
        system = (
            "You are a hackathon judge evaluating the vision and ambition of a "
            "project based solely on its README. Score the idea independently "
            "of implementation quality. Reward bold, novel ideas that address "
            "real problems, even if execution is incomplete."
        )
        prompt = (
            "Evaluate this project's README as a vision document. Score each "
            "sub-dimension from 0.00 to 1.00.\n\n"
            "## README\n\n"
            f"{readme_text[:2500]}\n\n"
            "## Scoring Rubric\n\n"
            "1. **Problem Clarity** (0–1): Is the problem well-defined and real?\n"
            "2. **Solution Novelty** (0–1): Is the approach meaningfully different from existing tools?\n"
            "3. **Scope Ambition** (0–1): Is the goal bold but achievable for a hackathon?\n"
            "4. **Audience Specificity** (0–1): Is there a clear target user who benefits?\n\n"
            "Provide a brief rationale, then end with exactly these four lines:\n"
            "PROBLEM_CLARITY: X.XX\n"
            "SOLUTION_NOVELTY: X.XX\n"
            "SCOPE_AMBITION: X.XX\n"
            "AUDIENCE_SPECIFICITY: X.XX"
        )
        return self.complete(prompt, system=system, max_tokens=768)
