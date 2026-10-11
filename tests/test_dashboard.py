"""Offline test for the dashboard HTML builder."""
from dashboard import build_html


def test_build_html_empty():
    html_out = build_html([])
    assert "Failure Pattern Memory" in html_out
    assert "No failures recorded yet." in html_out


def test_build_html_escapes_and_counts():
    rows = [{
        "timestamp": "2026-01-01T10:00:00+00:00",
        "error_category": "BUILD_ERROR",
        "context_pattern": "<script>bad</script>",
        "task_type": "script_run",
        "severity": "high",
    }]
    html_out = build_html(rows)
    assert "<script>bad</script>" not in html_out
    assert "&lt;script&gt;bad&lt;/script&gt;" in html_out
    assert "Total records: 1" in html_out
