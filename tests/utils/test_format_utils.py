from app.utils.format_utils import format_duration_str

def test_format_duration_str_seconds():
    assert format_duration_str("45s") == "45s"
    assert format_duration_str("45") == "45s"

def test_format_duration_str_minutes():
    assert format_duration_str("65s") == "1m 5s"
    assert format_duration_str("120s") == "2m 0s"

def test_format_duration_str_hours():
    assert format_duration_str("7565s") == "2h 6m 5s"
    assert format_duration_str("3600") == "1h 0m 0s"
    assert format_duration_str("3661s") == "1h 1m 1s"

def test_format_duration_str_non_numeric():
    assert format_duration_str("abc") == "abc"
    assert format_duration_str("1h 30m") == "1h 30m"
    assert format_duration_str("") == ""
    assert format_duration_str(None) is None
