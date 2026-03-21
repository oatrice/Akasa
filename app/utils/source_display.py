from __future__ import annotations

from typing import Optional


def normalize_source_display(source: Optional[str]) -> Optional[str]:
    """
    Normalize caller-provided `source` into a friendly product/IDE label for UI surfaces
    (e.g., Telegram notifications).

    The backend intentionally accepts free-form source strings. This helper provides a
    best-effort mapping for common IDEs/agents while preserving unknown values.

    Parenthesized context is preserved: e.g. "Luma CLI (MyProject)" → "Luma (MyProject)"
    """

    if source is None:
        return None

    raw = source.strip()
    if not raw:
        return None

    # Extract parenthesized context if present, e.g. "Luma CLI (dir-name)"
    context = None
    base = raw
    paren_start = raw.find("(")
    if paren_start > 0 and raw.endswith(")"):
        context = raw[paren_start:]  # "(dir-name)"
        base = raw[:paren_start].strip()

    s = base.lower()

    # IDEs / tools
    label = None
    if s in {"cursor", "cursor ide"} or "cursor" in s:
        label = "Cursor"

    elif s in {"windsurf", "winsurf", "windsurf ide", "winsurf ide"} or "windsurf" in s or "winsurf" in s:
        label = "Windsurf"

    elif s in {"codex", "openai codex"} or "codex" in s:
        label = "Codex"

    elif s in {"antigravity", "antigravity ide"} or "antigravity" in s:
        label = "Antigravity"

    # Assistants / CLIs
    elif s in {"luma", "luma cli"} or "luma" in s:
        label = "Luma"

    elif s in {"gemini", "gemini cli"} or "gemini" in s:
        label = "Gemini"

    elif s in {"zed", "zed ide"} or "zed" in s:
        label = "Zed"

    elif s in {"ai assistant"}:
        label = "AI Assistant"

    if label:
        if context:
            return f"{label} {context}"
        return label

    # Fallback: preserve the original value
    return raw

