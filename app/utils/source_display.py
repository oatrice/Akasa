from __future__ import annotations

from typing import Optional


def normalize_source_display(source: Optional[str]) -> Optional[str]:
    """
    Normalize caller-provided `source` into a friendly product/IDE label for UI surfaces
    (e.g., Telegram notifications).

    The backend intentionally accepts free-form source strings. This helper provides a
    best-effort mapping for common IDEs/agents while preserving unknown values.
    """

    if source is None:
        return None

    raw = source.strip()
    if not raw:
        return None

    s = raw.lower()

    # IDEs / tools
    if s in {"cursor", "cursor ide"} or "cursor" in s:
        return "Cursor"

    if s in {"windsurf", "winsurf", "windsurf ide", "winsurf ide"} or "windsurf" in s or "winsurf" in s:
        return "Windsurf"

    if s in {"codex", "openai codex"} or "codex" in s:
        return "Codex"

    if s in {"antigravity", "antigravity ide"} or "antigravity" in s:
        return "Antigravity"

    # Assistants / CLIs
    if s in {"luma", "luma cli"} or "luma" in s:
        return "Luma"

    if s in {"gemini", "gemini cli"} or "gemini" in s:
        return "Gemini"

    if s in {"zed", "zed ide"} or "zed" in s:
        return "Zed"

    if s in {"ai assistant"}:
        return "AI Assistant"

    # Fallback: preserve the original value
    return raw

