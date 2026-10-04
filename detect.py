from pathlib import Path
import argparse
import csv
import json
import math

import numpy as np
from sklearn.ensemble import IsolationForest


LOG_FILE = Path("sample_logs.txt")
OUTPUT_FILE = Path("anomalies.csv")

ANOMALY_KEYWORDS = (
    "ERROR",
    "FAILED",
    "DENIED",
    "UNAUTHORIZED",
    "CRITICAL",
    "WARNING",
    "WARN",
    "TIMEOUT",
)

HIGH_SEVERITY_KEYWORDS = (
    "ERROR",
    "FAILED",
    "DENIED",
    "UNAUTHORIZED",
    "CRITICAL",
)

MEDIUM_SEVERITY_KEYWORDS = (
    "WARNING",
    "WARN",
    "TIMEOUT",
)


def load_logs(file_path):
    """Load non-empty log entries from a text file."""
    with file_path.open("r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def extract_features(line):
    """Convert a log entry into numeric features for IsolationForest."""
    upper_line = line.upper()
    line_length = max(len(line), 1)

    return [
        len(line),
        sum(char.isdigit() for char in line) / line_length,
        sum(char.isupper() for char in line) / line_length,
        sum(upper_line.count(keyword) for keyword in ANOMALY_KEYWORDS),
        line.count("="),
        line.count("/"),
    ]


def score_severity(line):
    """Assign a rule-based severity level to an anomalous log entry."""
    upper_line = line.upper()

    if any(keyword in upper_line for keyword in HIGH_SEVERITY_KEYWORDS):
        return "HIGH"

    if any(keyword in upper_line for keyword in MEDIUM_SEVERITY_KEYWORDS):
        return "MEDIUM"

    return "LOW"


def detect_anomalies(logs, contamination=0.20, threshold=0.0):
    """Detect unusual log entries using IsolationForest."""
    if contamination != "auto" and (
        not isinstance(contamination, (int, float)) or not 0 < contamination <= 0.5
    ):
        raise ValueError("contamination must be 'auto' or a number in (0, 0.5].")
    if not math.isfinite(threshold):
        raise ValueError("threshold must be finite.")
    if len(logs) < 5:
        raise ValueError("Add at least 5 log entries before running detection.")
    if any(not isinstance(line, str) or not line.strip() for line in logs):
        raise ValueError("Log entries must be non-empty strings.")
    features = np.array(
        [extract_features(line) for line in logs],
        dtype=float,
    )

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )

    model.fit(features)
    anomaly_scores = model.decision_function(features)

    anomalies = []

    for line, score in zip(logs, anomaly_scores):
        if score < threshold:
            anomalies.append(
                {
                    "severity": score_severity(line),
                    "anomaly_score": round(float(score), 4),
                    "log_entry": line,
                }
            )

    return anomalies


def save_anomalies(anomalies, output_file=OUTPUT_FILE):
    """Save detected anomalies to a CSV file."""
    with Path(output_file).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["severity", "anomaly_score", "log_entry"],
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(anomalies)


def build_summary(logs, anomalies, contamination=0.20, threshold=0.0):
    """Summarize a run without claiming accuracy on unlabeled data."""
    scores = [item["anomaly_score"] for item in anomalies]
    return {
        "logs_analyzed": len(logs),
        "anomalies_detected": len(anomalies),
        "anomaly_percentage": round(100 * len(anomalies) / len(logs), 2) if logs else 0.0,
        "severity_counts": {
            level: sum(item["severity"] == level for item in anomalies)
            for level in ("HIGH", "MEDIUM", "LOW")
        },
        "anomaly_score_range": {"min": min(scores), "max": max(scores)} if scores else None,
        "settings": {"contamination": contamination, "threshold": threshold, "random_state": 42},
    }


def parse_contamination(value):
    if value == "auto":
        return value
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use 'auto' or a number in (0, 0.5].") from error
    if not 0 < number <= 0.5:
        raise argparse.ArgumentTypeError("Use 'auto' or a number in (0, 0.5].")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect unusual log entries using Isolation Forest.")
    parser.add_argument("--input", type=Path, default=LOG_FILE)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    parser.add_argument("--summary", type=Path, default=Path("summary.json"))
    parser.add_argument("--contamination", type=parse_contamination, default=0.20)
    parser.add_argument("--threshold", type=float, default=0.0,
                        help="Flag decision scores below this value (default: 0).")
    args = parser.parse_args(argv)
    paths = [path.resolve() for path in (args.input, args.output, args.summary)]
    if len(set(paths)) != 3:
        parser.error("Input, CSV output, and summary must use different paths.")
    try:
        logs = load_logs(args.input)
        anomalies = detect_anomalies(logs, args.contamination, args.threshold)
        summary = build_summary(logs, anomalies, args.contamination, args.threshold)
        save_anomalies(anomalies, args.output)
        args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"\nScanned {len(logs)} log entries.")
    print(f"Detected {len(anomalies)} anomalies ({summary['anomaly_percentage']}%).")
    print(f"Severity counts: {summary['severity_counts']}\n")

    for anomaly in anomalies:
        print(
            f"[{anomaly['severity']}] "
            f"Score: {anomaly['anomaly_score']} | "
            f"{anomaly['log_entry']}"
        )

    print(f"\nResults saved to {args.output}")
    print(f"Run summary saved to {args.summary}")


if __name__ == "__main__":
    main()
