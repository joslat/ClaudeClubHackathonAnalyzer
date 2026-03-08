"""Configuration: env vars, constants, validated settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API credentials (optional)
    github_token: str = Field(default="", description="GitHub PAT for code search and repo info")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for AI analysis")

    # Directories
    repos_dir: Path = Field(default=Path("./repos"), description="Where cloned repos are stored")
    reports_dir: Path = Field(default=Path("./reports"), description="Where reports are written")
    cache_dir: Path = Field(default=Path("./cache"), description="API response cache directory")

    # Safety limits
    max_repo_size_mb: int = Field(default=500, description="Skip repos larger than this (MB)")
    build_timeout_seconds: int = Field(default=120, description="Max seconds for build attempts")
    clone_timeout_seconds: int = Field(default=300, description="Max seconds for git clone")

    # Cache
    cache_ttl_seconds: int = Field(default=86400, description="GitHub search cache TTL (seconds)")

    # GitHub rate limiting
    github_search_rate_limit: int = Field(
        default=30, description="GitHub code search requests per minute"
    )

    # Claude model
    claude_model: str = Field(
        default="claude-opus-4-5", description="Claude model for AI analysis"
    )

    # Hackathon freshness
    hackathon_start_date: str = Field(
        default="", description="ISO date (e.g. 2026-03-01) — when the hackathon started"
    )

    @property
    def has_github_token(self) -> bool:
        return bool(self.github_token)

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.anthropic_api_key)

    def ensure_dirs(self) -> None:
        """Create all required directories if they don't exist."""
        for d in [self.repos_dir, self.reports_dir, self.cache_dir]:
            d.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / "per-repo").mkdir(exist_ok=True)
        (self.reports_dir / "summary").mkdir(exist_ok=True)
        (self.cache_dir / "github_search").mkdir(exist_ok=True)
