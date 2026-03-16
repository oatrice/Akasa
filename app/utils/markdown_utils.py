import re
from typing import Optional

# Module-level compiled patterns (avoids recompilation on every call)
_CONTENT_ESCAPE_CHARS = r"\_*[]()~`>#+-=|{}.!"
_CONTENT_ESCAPE_PATTERN = re.compile(rf"([{re.escape(_CONTENT_ESCAPE_CHARS)}])")


def escape_markdown_v2_content(text: Optional[str]) -> Optional[str]:
    """
    Escapes ALL Telegram MarkdownV2 special characters for use as dynamic content
    inside a pre-structured MarkdownV2 message (e.g., embedded inside *bold* labels).

    Unlike escape_markdown_v2(), this function also escapes * and _ to prevent
    accidental formatting from arbitrary user-supplied strings such as project names,
    task descriptions, or file paths.

    Use this when YOU control the surrounding markdown structure and need to safely
    embed untrusted content within it.

    Characters escaped: _ * [ ] ( ) ~ ` > # + - = | { } . ! \\
    """
    if not text:
        return text
    return _CONTENT_ESCAPE_PATTERN.sub(r"\\\1", text)


def escape_markdown_v2(text: str) -> str:
    """
    Escapes special characters in text for Telegram MarkdownV2 format.
    Characters inside inline or multi-line code blocks are preserved.
    Formatting characters (*, _, `) are NOT escaped to allow for basic styling.
    """
    if not text:
        return text

    # Characters to escape: [ ] ( ) ~ > # + - = | { } . !
    # We EXCLUDE *, _, ` from being escaped to allow user formatting
    chars_to_escape = r"[]()~>#+-=|{}.!"
    # Use negative lookbehind to avoid escaping characters that are already escaped
    escape_pattern = re.compile(rf"(?<!\\)([{re.escape(chars_to_escape)}])")

    # Regular expression to match code blocks (both ``` and `)
    # This pattern matches ```...``` first, then `...`
    # We use re.DOTALL so the dot matches newlines inside ``` blocks
    code_block_pattern = re.compile(r"(```.*?```|`.*?`)", flags=re.DOTALL)

    parts = code_block_pattern.split(text)
    escaped_parts = []

    for i, part in enumerate(parts):
        # re.split keeps the matched separators at odd indices if capturing parenthesis are used
        if i % 2 == 1:
            # Code block: inside pre and code entities, all '`' and '\' characters must be escaped
            if part.startswith("```") and part.endswith("```"):
                content = part[3:-3]
                content = content.replace('\\', '\\\\').replace('`', r'\`')
                escaped_parts.append(f"```{content}```")
            elif part.startswith("`") and part.endswith("`"):
                content = part[1:-1]
                content = content.replace('\\', '\\\\').replace('`', r'\`')
                escaped_parts.append(f"`{content}`")
            else:
                escaped_parts.append(part)
        else:
            # This is normal text, escape special characters
            escaped_part = escape_pattern.sub(r"\\\1", part)

            # Additional check: If there are any backticks in this "normal" part,
            # they must be unclosed/unmatched (since matched ones were handled by re.split).
            # Escape them to avoid Telegram parsing errors.
            escaped_part = escaped_part.replace("`", r"\`")

            escaped_parts.append(escaped_part)

    return "".join(escaped_parts)
