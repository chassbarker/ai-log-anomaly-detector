from pathlib import Path
import csv

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


def detect_anomalies(logs):
    """Detect unusual log entries using IsolationForest."""
    features = np.array(
        [extract_features(line) for line in logs],
        dtype=float,
    )

    model = IsolationForest(
        n_estimators=200,
        contamination=0.20,
        random_state=42,
    )

    predictions = model.fit_predict(features)
    anomaly_scores = model.decision_function(features)

    anomalies = []

    for line, prediction, score in zip(logs, predictions, anomaly_scores):
        if prediction == -1:
            anomalies.append(
                {
                    "severity": score_severity(line),
                    "anomaly_score": round(float(score), 4),
                    "log_entry": line,
                }
            )

    return anomalies


def save_anomalies(anomalies):
    """Save detected anomalies to a CSV file."""
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["severity", "anomaly_score", "log_entry"],
        )

        writer.writeheader()
        writer.writerows(anomalies)


def main():
    if not LOG_FILE.exists():
        print(f"Log file not found: {LOG_FILE}")
        return

    logs = load_logs(LOG_FILE)

    if len(logs) < 5:
        print("Add at least 5 log entries before running detection.")
        return

    anomalies = detect_anomalies(logs)
    save_anomalies(anomalies)

    print(f"\nScanned {len(logs)} log entries.")
    print(f"Detected {len(anomalies)} anomalies.\n")

    for anomaly in anomalies:
        print(
            f"[{anomaly['severity']}] "
            f"Score: {anomaly['anomaly_score']} | "
            f"{anomaly['log_entry']}"
        )

    print(f"\nResults saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
