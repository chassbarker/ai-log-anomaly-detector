import csv
import io
import json
from pathlib import Path

import streamlit as st

from detect import build_summary, detect_anomalies

SAMPLE_FILE = Path(__file__).with_name("sample_logs.txt")
MAX_UPLOAD_BYTES = 1_000_000
MAX_LOG_ENTRIES = 5_000


def parse_log_text(text):
    """Return stripped, non-empty log entries from pasted or uploaded text."""
    logs = [line.strip() for line in text.splitlines() if line.strip()]
    if len(logs) > MAX_LOG_ENTRIES:
        raise ValueError(f"Use {MAX_LOG_ENTRIES:,} log entries or fewer in the demo.")
    return logs


def anomalies_to_csv(anomalies):
    """Serialize anomaly rows for the download button."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["severity", "anomaly_score", "log_entry"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(anomalies)
    return buffer.getvalue()


def main():
    st.set_page_config(page_title="AI Log Anomaly Detector", page_icon="🔎", layout="wide")

    st.title("AI Log Anomaly Detector")
    st.write(
        "Explore a lightweight machine learning pipeline that uses Isolation Forest to "
        "surface unusual system log entries and rule-based severity to prioritize review."
    )
    st.caption("Portfolio demo · Python · scikit-learn · Isolation Forest · Streamlit")

    with st.sidebar:
        st.header("Detection settings")
        contamination = st.slider(
            "Expected anomaly proportion",
            min_value=0.05,
            max_value=0.50,
            value=0.20,
            step=0.05,
            help="Isolation Forest contamination controls the model's expected outlier proportion.",
        )
        threshold = st.slider(
            "Decision threshold",
            min_value=-0.20,
            max_value=0.10,
            value=0.00,
            step=0.01,
            help="Entries with decision scores below this value are flagged. Lower values are stricter.",
        )
        st.info("This demo identifies statistical outliers. It does not make a security diagnosis.")

    sample_text = SAMPLE_FILE.read_text(encoding="utf-8")
    source = st.radio(
        "Choose log input",
        ["Sample logs", "Paste logs", "Upload .txt"],
        horizontal=True,
    )

    if source == "Sample logs":
        log_text = sample_text
        st.text_area("Sample input", value=sample_text, height=230, disabled=True)
    elif source == "Paste logs":
        log_text = st.text_area(
            "Paste one log entry per line",
            height=230,
            placeholder=(
                "2026-10-03 09:15:17 WARNING High CPU usage detected "
                "host=app-02 cpu=91%"
            ),
        )
    else:
        uploaded = st.file_uploader("Upload a UTF-8 text file", type=["txt", "log"])
        log_text = ""
        if uploaded is not None:
            if uploaded.size > MAX_UPLOAD_BYTES:
                st.error("Please upload a file smaller than 1 MB for this public demo.")
            else:
                try:
                    log_text = uploaded.getvalue().decode("utf-8")
                    st.caption(f"Loaded {uploaded.name}")
                except UnicodeDecodeError:
                    st.error("The uploaded file must use UTF-8 text encoding.")

    if st.button("Analyze logs", type="primary", use_container_width=True):
        try:
            logs = parse_log_text(log_text)
            anomalies = detect_anomalies(
                logs,
                contamination=contamination,
                threshold=threshold,
            )
            summary = build_summary(
                logs,
                anomalies,
                contamination=contamination,
                threshold=threshold,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            counts = summary["severity_counts"]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Logs analyzed", summary["logs_analyzed"])
            col2.metric("Anomalies", summary["anomalies_detected"])
            col3.metric("Anomaly rate", f"{summary['anomaly_percentage']}%")
            col4.metric("High severity", counts["HIGH"])

            st.subheader("Flagged log entries")
            if anomalies:
                st.dataframe(
                    anomalies,
                    width="stretch",
                    hide_index=True,
                    column_order=["severity", "anomaly_score", "log_entry"],
                    column_config={
                        "severity": st.column_config.TextColumn(
                            "Severity",
                            width="small",
                        ),
                        "anomaly_score": st.column_config.NumberColumn(
                            "Anomaly score",
                            format="%.4f",
                            width="small",
                        ),
                        "log_entry": st.column_config.TextColumn(
                            "Log entry",
                            width="large",
                        ),
                    },
                )

                with st.expander("View full flagged log details"):
                    for index, anomaly in enumerate(anomalies, start=1):
                        detail_col1, detail_col2 = st.columns([1, 4])
                        detail_col1.markdown(
                            f"**{index}. {anomaly['severity']}**  \n"
                            f"Score: `{anomaly['anomaly_score']:.4f}`"
                        )
                        with detail_col2:
                            st.code(
                                anomaly["log_entry"],
                                language=None,
                                wrap_lines=True,
                                height="content",
                                width="stretch",
                            )
            else:
                st.success("No log entries fell below the selected decision threshold.")

            st.caption(
                "Severity is assigned after anomaly detection using keyword rules. "
                "Anomaly scores are Isolation Forest decision scores, not probabilities."
            )

            download_col1, download_col2 = st.columns(2)
            download_col1.download_button(
                "Download anomaly CSV",
                data=anomalies_to_csv(anomalies),
                file_name="anomalies.csv",
                mime="text/csv",
                use_container_width=True,
            )
            download_col2.download_button(
                "Download run summary",
                data=json.dumps(summary, indent=2) + "\n",
                file_name="summary.json",
                mime="application/json",
                use_container_width=True,
            )

    with st.expander("How the model works"):
        st.markdown(
            """
1. Each log entry is converted into six numeric features: length, digit ratio, uppercase ratio,
   alert-keyword count, equals-sign count, and slash count.
2. Isolation Forest learns the feature patterns in the submitted batch and assigns a decision score.
3. Entries below the selected decision threshold are flagged as anomalies.
4. A separate keyword rule assigns HIGH, MEDIUM, or LOW review priority.

The included sample is synthetic and unlabeled, so the demo reports detection statistics rather than accuracy metrics.
            """
        )


if __name__ == "__main__":
    main()
