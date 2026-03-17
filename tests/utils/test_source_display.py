import pytest


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Cursor", "Cursor"),
        ("cursor ide", "Cursor"),
        ("my Cursor workflow", "Cursor"),
        ("Windsurf", "Windsurf"),
        ("Winsurf", "Windsurf"),
        ("windsurf ide", "Windsurf"),
        ("Codex", "Codex"),
        ("openai codex", "Codex"),
        ("Antigravity", "Antigravity"),
        ("antigravity ide", "Antigravity"),
        ("Luma", "Luma"),
        ("luma cli", "Luma"),
        ("Gemini CLI", "Gemini"),
        ("gemini", "Gemini"),
        ("Zed", "Zed"),
        ("zed ide", "Zed"),
        ("AI Assistant", "AI Assistant"),
        ("MyCustomAgent v1", "MyCustomAgent v1"),
    ],
)
def test_normalize_source_display(raw, expected):
    from app.utils.source_display import normalize_source_display

    assert normalize_source_display(raw) == expected


def test_normalize_source_display_none_or_empty():
    from app.utils.source_display import normalize_source_display

    assert normalize_source_display(None) is None
    assert normalize_source_display("") is None
    assert normalize_source_display("   ") is None

