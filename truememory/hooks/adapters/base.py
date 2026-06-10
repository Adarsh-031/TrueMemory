"""Abstract base class for CLI adapters.

Each supported CLI (Claude Code, Kimi, Hermes, OpenClaw) implements
this interface to handle its config format, hook registration, and
MCP server setup.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class CLIAdapter(ABC):
    """Base interface for CLI-specific TrueMemory integration."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable CLI name (e.g. 'Claude Code')."""

    @property
    @abstractmethod
    def cli_id(self) -> str:
        """Machine identifier (e.g. 'claude', 'kimi', 'hermes', 'openclaw')."""

    @property
    @abstractmethod
    def config_path(self) -> Path:
        """Path to the CLI's main config file."""

    @abstractmethod
    def detect(self) -> bool:
        """Return True if this CLI is installed on the system."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if TrueMemory is already wired into this CLI."""

    @abstractmethod
    def install_mcp(self, python_path: str | None = None) -> None:
        """Register the TrueMemory MCP server in the CLI's config."""

    @abstractmethod
    def install_hooks(
        self,
        python_path: str | None = None,
        user_id: str = "",
        db_path: str = "",
    ) -> None:
        """Register TrueMemory lifecycle hooks in the CLI's config."""

    @abstractmethod
    def uninstall(self) -> None:
        """Remove all TrueMemory entries from the CLI's config."""

    @abstractmethod
    def verify(self) -> bool:
        """Smoke-test the installation (config exists, paths resolve)."""

    @abstractmethod
    def get_system_prompt_path(self) -> Path | None:
        """Return the path to the CLI's system prompt file, or None."""

    @abstractmethod
    def get_system_prompt_content(self) -> str:
        """Return the TrueMemory system prompt content for this CLI."""


# Served when CLAUDE_TEMPLATE.md is missing or unreadable. Must carry the
# same directive guidance as the template (issue #589, D-7) so directives
# stay discoverable even on broken installs.
_FALLBACK_PROMPT = (
    "# TrueMemory — Persistent Memory\n\n"
    "You have access to TrueMemory MCP tools for persistent memory.\n"
    "- Use `truememory_store` to save user facts, preferences, and decisions.\n"
    '- When the user gives a standing instruction ("always do X", "never do Y", '
    '"from now on..."), store it as a directive: '
    '`truememory_store(content="...", directive=True)`. Directives auto-load '
    "at the start of every session — regular memories do not.\n"
    "- Use `truememory_search` to recall stored memories before answering.\n"
    "- Directives are injected automatically at session start — you do not "
    "need to search for them.\n"
    "- Search TrueMemory FIRST on any 'do you remember' question.\n"
)


def get_generic_system_prompt() -> str:
    """Return the TrueMemory system prompt for non-Claude CLIs."""
    template = Path(__file__).parent.parent.parent / "ingest" / "CLAUDE_TEMPLATE.md"
    if template.exists():
        try:
            content = template.read_text(encoding="utf-8").strip()
            content = content.replace("Claude Code's built-in auto-memory", "The host CLI's built-in memory")
            content = content.replace("(`MEMORY.md` files under `~/.claude/projects/*/memory/`)", "")
            return content
        except OSError:
            pass
    return _FALLBACK_PROMPT
