import pytest

from streamlit_app import MAX_LOG_ENTRIES, anomalies_to_csv, parse_log_text


def test_parse_log_text_skips_blank_lines():
    assert parse_log_text("  INFO ok  \n\nERROR failed\n") == ["INFO ok", "ERROR failed"]


def test_parse_log_text_limits_public_demo_size():
    with pytest.raises(ValueError, match=f"{MAX_LOG_ENTRIES:,}"):
        parse_log_text("INFO\n" * (MAX_LOG_ENTRIES + 1))


def test_anomalies_to_csv_handles_commas():
    csv_text = anomalies_to_csv([
        {"severity": "HIGH", "anomaly_score": -0.1, "log_entry": "ERROR key=a,b"}
    ])
    assert '"ERROR key=a,b"' in csv_text
    assert csv_text.startswith("severity,anomaly_score,log_entry\n")
