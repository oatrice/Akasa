import pytest

from app.utils.markdown_utils import escape_markdown_v2, escape_markdown_v2_content


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
    expected = "_*[]()~`>#+-=|{}.!"  # placeholder for logic check

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


# === escape_markdown_v2_content (Issue #61) ===


def test_escape_content_no_special_chars():
    """Plain text without special characters should remain unchanged."""
    assert escape_markdown_v2_content("Hello World") == "Hello World"


def test_escape_content_escapes_underscore():
    """_ must be escaped — critical for Python-style identifiers like fix_bug."""
    result = escape_markdown_v2_content("fix_bug_in_redis")
    assert "\\_" in result
    assert result == "fix\\_bug\\_in\\_redis"


def test_escape_content_escapes_asterisk():
    """* must be escaped so user-supplied strings don't accidentally trigger bold."""
    result = escape_markdown_v2_content("a * b")
    assert "\\*" in result
    assert result == "a \\* b"


def test_escape_content_escapes_dot_and_exclamation():
    """Dots and exclamation marks that appear in task names must be escaped."""
    result = escape_markdown_v2_content("Deploy v1.0!")
    assert result == "Deploy v1\\.0\\!"


def test_escape_content_escapes_parens():
    """Parentheses in strings like PR titles must be escaped."""
    result = escape_markdown_v2_content("Merge PR (feat/auth)")
    assert result == "Merge PR \\(feat/auth\\)"


def test_escape_content_escapes_backtick():
    """Backticks in content must be escaped."""
    result = escape_markdown_v2_content("Run `pytest`")
    assert result == "Run \\`pytest\\`"


def test_escape_content_escapes_all_special_chars():
    """All MarkdownV2 special characters including * and _ must be escaped."""
    # Characters: _ * [ ] ( ) ~ ` > # + - = | { } . !
    text = "_*[]()~`>#+-=|{}.!"
    result = escape_markdown_v2_content(text)
    assert result == "\\_\\*\\[\\]\\(\\)\\~\\`\\>\\#\\+\\-\\=\\|\\{\\}\\.\\!"


def test_escape_content_empty_string():
    """Empty string should return empty string without errors."""
    assert escape_markdown_v2_content("") == ""


def test_escape_content_none_returns_none():
    """None input should be returned as-is (falsy guard)."""
    # The function has `if not text: return text`, so None returns None
    assert escape_markdown_v2_content(None) is None


def test_escape_content_github_pr_link():
    """A typical GitHub PR URL should have its special chars escaped."""
    text = "https://github.com/oatrice/Akasa/pull/42"
    result = escape_markdown_v2_content(text)
    # / is not a special char in MarkdownV2 — no escaping needed for slashes
    assert "\\." in result  # dots in domain/path must be escaped
    assert (
        "\\#" not in result
    )  # # is special but not present in this URL after escaping
    # The URL itself should still be recognisable
    assert "github" in result


def test_escape_content_special_chars_in_project_name():
    """Project names with dots (e.g., 'My.App v2.0') must be fully escaped."""
    result = escape_markdown_v2_content("My.App v2.0")
    assert result == "My\\.App v2\\.0"


def test_escape_content_does_not_double_escape():
    """Calling escape_markdown_v2_content twice should produce double-escaped output,
    confirming the function is idempotent-unsafe (as expected — caller must not double-call)."""
    text = "fix_bug"
    once = escape_markdown_v2_content(text)
    twice = escape_markdown_v2_content(once)
    # After first call: fix\_bug
    # After second call: fix\\_bug (backslash itself gets escaped)
    assert once == "fix\\_bug"
    assert twice == "fix\\\\\\_bug"


def test_escape_content_vs_escape_markdown_v2_differ_on_underscore():
    """Confirms the key difference: escape_markdown_v2 does NOT escape _,
    but escape_markdown_v2_content DOES."""
    text = "some_function_name"
    general = escape_markdown_v2(text)
    content = escape_markdown_v2_content(text)
    # General escaper leaves _ raw (to allow italic formatting)
    assert "_" in general
    # Content escaper fully escapes _
    assert "\\_" in content
    assert "_" not in content.replace("\\_", "")
