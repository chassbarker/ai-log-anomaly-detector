import csv
import json
from pathlib import Path

import numpy as np
import pytest

from detect import (build_summary, detect_anomalies, extract_features,
                    load_logs, main, save_anomalies, score_severity)

SAMPLE = Path(__file__).resolve().parents[1] / "sample_logs.txt"


def test_features_preserve_numeric_information():
    assert extract_features("AB12=/") == [6, 2 / 6, 2 / 6, 0, 1, 1]


def test_empty_features_are_finite():
    assert extract_features("") == [0, 0, 0, 0, 0, 0]
    assert np.isfinite(extract_features("")).all()


@pytest.mark.parametrize("line,expected", [
    ("error request timeout", "HIGH"),
    ("Unauthorized access", "HIGH"),
    ("warning CPU usage", "MEDIUM"),
    ("request TIMEOUT", "MEDIUM"),
    ("INFO unusually long request", "LOW"),
])
def test_severity_priority_and_case(line, expected):
    assert score_severity(line) == expected


def test_load_logs_skips_blanks_and_preserves_unicode(tmp_path):
    path = tmp_path / "logs.txt"
    path.write_text("  INFO café  \n\n \nERROR failed\n", encoding="utf-8")
    assert load_logs(path) == ["INFO café", "ERROR failed"]


@pytest.mark.parametrize("logs", [[], ["INFO"] * 4, ["INFO"] * 4 + [""], ["INFO"] * 4 + [None]])
def test_invalid_input_is_rejected(logs):
    with pytest.raises(ValueError):
        detect_anomalies(logs)


@pytest.mark.parametrize("value", [0, -0.1, 0.51, float("nan"), "invalid"])
def test_invalid_contamination_is_rejected(value):
    with pytest.raises(ValueError, match="contamination"):
        detect_anomalies(["INFO"] * 5, contamination=value)


def test_nonfinite_threshold_is_rejected():
    with pytest.raises(ValueError, match="threshold"):
        detect_anomalies(["INFO"] * 5, threshold=float("inf"))


def test_detection_is_reproducible_and_scores_are_negative():
    logs = load_logs(SAMPLE)
    result = detect_anomalies(logs)
    assert result == detect_anomalies(logs)
    assert 0 < len(result) < len(logs)
    assert all(row["log_entry"] in logs and row["anomaly_score"] < 0 for row in result)
    assert all(row["severity"] == score_severity(row["log_entry"]) for row in result)


def test_threshold_changes_selection_and_auto_is_supported():
    logs = load_logs(SAMPLE)
    assert detect_anomalies(logs, threshold=-10) == []
    assert len(detect_anomalies(logs, contamination="auto", threshold=10)) == len(logs)


def test_csv_round_trip_escapes_log_content(tmp_path):
    rows = [{"severity": "HIGH", "anomaly_score": -0.125,
             "log_entry": 'ERROR message="failed, café"'}]
    output = tmp_path / "results.csv"
    save_anomalies(rows, output)
    with output.open(encoding="utf-8", newline="") as file:
        actual = list(csv.DictReader(file))
    assert actual == [{**rows[0], "anomaly_score": "-0.125"}]
    save_anomalies([], output)
    assert output.read_text().strip() == "severity,anomaly_score,log_entry"


def test_summary_counts_and_empty_results():
    rows = [{"severity": level, "anomaly_score": score}
            for level, score in [("HIGH", -0.2), ("HIGH", -0.1), ("LOW", -0.05)]]
    summary = build_summary(["INFO"] * 10, rows)
    assert summary["logs_analyzed"] == 10
    assert summary["anomalies_detected"] == 3
    assert summary["anomaly_percentage"] == 30.0
    assert summary["severity_counts"] == {"HIGH": 2, "MEDIUM": 0, "LOW": 1}
    assert summary["anomaly_score_range"] == {"min": -0.2, "max": -0.05}
    assert build_summary([], [])["anomaly_percentage"] == 0
    assert build_summary(["INFO"] * 5, [])["anomaly_score_range"] is None


def test_cli_exports_consistent_csv_and_json(tmp_path):
    output, summary = tmp_path / "out.csv", tmp_path / "summary.json"
    main(["--input", str(SAMPLE), "--output", str(output), "--summary", str(summary),
          "--contamination", "0.1"])
    data = json.loads(summary.read_text())
    with output.open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert data["logs_analyzed"] == 20
    assert data["anomalies_detected"] == len(rows)
    assert sum(data["severity_counts"].values()) == len(rows)
    assert data["settings"]["contamination"] == 0.1


@pytest.mark.parametrize("case", ["missing", "short", "contamination", "threshold", "same_path"])
def test_cli_errors_exit_nonzero_without_outputs(tmp_path, case):
    source = tmp_path / "logs.txt"
    source.write_text("INFO\n" * (4 if case == "short" else 5))
    output, summary = tmp_path / "out.csv", tmp_path / "summary.json"
    args = ["--input", str(source), "--output", str(output), "--summary", str(summary)]
    if case == "missing":
        source.unlink()
    elif case == "contamination":
        args += ["--contamination", "0.9"]
    elif case == "threshold":
        args += ["--threshold", "nan"]
    elif case == "same_path":
        args += ["--output", str(source)]
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert not output.exists() and not summary.exists()
    if case == "same_path":
        assert source.read_text() == "INFO\n" * 5
