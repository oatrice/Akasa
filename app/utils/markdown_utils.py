import re

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
    escape_pattern = re.compile(rf"([{re.escape(chars_to_escape)}])")

    # Regular expression to match code blocks (both ``` and `)
    # This pattern matches ```...``` first, then `...`
    # We use re.DOTALL so the dot matches newlines inside ``` blocks
    code_block_pattern = re.compile(r"(```.*?```|`.*?`)", flags=re.DOTALL)

    parts = code_block_pattern.split(text)
    escaped_parts = []

    for i, part in enumerate(parts):
        # re.split keeps the matched separators at odd indices if capturing parenthesis are used
        if i % 2 == 1:
            # This is a code block, do not escape its contents
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
