import pytest
from app.utils.markdown_utils import escape_markdown_v2

def test_escape_markdown_v2_no_special_chars():
    """Text without any special characters should remain unchanged."""
    text = "Hello World"
    assert escape_markdown_v2(text) == "Hello World"

def test_escape_markdown_v2_special_chars_only():
    """Escapes all Telegram MarkdownV2 reserved characters."""
    # Characters: _ * [ ] ( ) ~ ` > # + - = | { } . !
    text = r"_*[]()~`>#+-=|{}.!"
    
    # Each character should be preceded by a backslash
    expected = r"\_*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!"
    # Raw string behavior was weird, let's just use double slashes for simplicity to ensure we want exactly one backslash before each.
    expected = "\\_\\*\\[\\]\\(\\)\\~\\`\\>\\#\\+\\-\\=\\|\\{\\}\\.\\!"
    assert escape_markdown_v2(text) == expected

def test_escape_markdown_v2_mixed_text():
    """Escapes special characters in regular text."""
    text = "Hello! This is a test. (Version 1-alpha)"
    expected = r"Hello\! This is a test\. \(Version 1\-alpha\)"
    assert escape_markdown_v2(text) == expected

def test_escape_markdown_v2_inline_code():
    """Content inside single-line code blocks should NOT be escaped."""
    text = "Run `print('Hello')` to see the output."
    expected = r"Run `print('Hello')` to see the output\."
    assert escape_markdown_v2(text) == expected

def test_escape_markdown_v2_multiline_code():
    """Content inside multi-line code blocks should NOT be escaped."""
    text = "Here is the code:\n```python\nprint(1 + 1)\n```\nDone."
    expected = "Here is the code:\n```python\nprint(1 + 1)\n```\nDone\\."
    assert escape_markdown_v2(text) == expected

def test_escape_markdown_v2_multiple_code_blocks():
    """Handles multiple code blocks mixed with text."""
    text = "Use `ls -l` or ```sh\ncat .env\n``` to view."
    expected = "Use `ls -l` or ```sh\ncat .env\n``` to view\\."
    assert escape_markdown_v2(text) == expected

def test_escape_markdown_v2_unmatched_backticks():
    """Edge case: unmatched backticks should just be escaped."""
    text = "This ` is unmatched."
    expected = r"This \` is unmatched\."
    assert escape_markdown_v2(text) == expected
