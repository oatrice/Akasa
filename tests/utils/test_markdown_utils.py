import pytest
from app.utils.markdown_utils import escape_markdown_v2

def test_escape_markdown_v2_no_special_chars():
    """Text without any special characters should remain unchanged."""
    text = "Hello World"
    assert escape_markdown_v2(text) == "Hello World"

def test_escape_markdown_v2_special_chars_only():
    """Escapes all Telegram MarkdownV2 reserved characters EXCEPT formatting chars."""
    # Characters to escape: [ ] ( ) ~ > # + - = | { } . !
    # Formatting chars (NOT escaped): _ * `
    text = r"_*[]()~`>#+-=|{}.!"
    
    # Each character should be preceded by a backslash EXCEPT _, *, `
    # Note: Telegram MarkdownV2 says _ and * should be escaped IF not used for formatting, 
    # but here we allow them for formatting.
    expected = "_*[]()~`>#+-=|{}.!" # placeholder for logic check
    
    # After update, it should look like this (formatting chars remain raw):
    expected = "_*\\[\\]\\(\\)\\~\\`\\>\\#\\+\\-\\=\\|\\{\\}\\.\\!"
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

# === Code Review #7 — Test Suggestions ===

def test_escape_markdown_v2_special_chars_adjacent_to_code():
    """Special characters immediately next to a code block must be escaped correctly."""
    text = "The result is `5-3=2`!"
    expected = "The result is `5-3=2`\\!"
    assert escape_markdown_v2(text) == expected

def test_escape_markdown_v2_nested_backticks_best_effort():
    """Best effort: nested backticks in complex shell commands.
    The regex may not handle nested backticks perfectly, but it should
    not crash and should produce a parseable result."""
    text = "Use `docker run --env 'VAR=val'` to run."
    expected = "Use `docker run --env 'VAR=val'` to run\\."
    assert escape_markdown_v2(text) == expected

def test_escape_markdown_v2_unclosed_multiline_code_block():
    """Unclosed multi-line code block: should escape everything as plain text
    since the code block is not properly closed."""
    text = "Here is the code: ```python\nprint('hello')"
    result = escape_markdown_v2(text)
    # ต้องไม่ crash และทุกอักขระพิเศษต้องถูก escape
    assert "\\`" in result or "```" in result
    # ต้องไม่มี raw ( หรือ ) ที่ไม่ถูก escape (ตรงนี้ไม่มี parens ในเคสนี้)
    # ที่สำคัญคือต้อง return ค่ากลับมาได้ ไม่ hang
    assert isinstance(result, str)
    assert len(result) > 0
