# AI Log Anomaly Detector

A lightweight Python machine learning project that analyzes system log entries and detects unusual activity using IsolationForest.

The project also assigns a severity level to detected anomalies so unusual events can be prioritized for review.

## Features

- Detects unusual log activity using IsolationForest
- Extracts numeric features from raw log entries
- Assigns HIGH, MEDIUM, or LOW severity levels
- Generates an anomaly score for each detected event
- Saves detected anomalies to a CSV file
- Uses a small, easy-to-understand Python codebase

## Technologies

- Python
- NumPy
- scikit-learn
- IsolationForest
- CSV

## How It Works

The project uses two separate steps.

### 1. Anomaly Detection

Each log entry is converted into numeric features such as:

- Log entry length
- Ratio of numbers
- Ratio of uppercase characters
- Number of alert-related keywords
- Number of structured fields
- Number of URL or file path characters

IsolationForest analyzes these features and identifies log entries whose patterns differ from the majority of the data.

### 2. Severity Scoring

After an anomaly is detected, a rule-based function assigns a severity level.

- HIGH: Error, failed, denied, unauthorized, or critical activity
- MEDIUM: Warning or timeout activity
- LOW: Other unusual activity

The machine learning model determines whether an event is unusual.

The severity logic determines how the detected event should be prioritized.

## Project Structure

```text
ai-log-anomaly-detector/
│
├── detect.py
├── sample_logs.txt
├── requirements.txt
├── .gitignore
├── anomalies.csv
└── README.md
```

`anomalies.csv` is included as sample generated output so the results can be reviewed without running the project first. Running `detect.py` regenerates the file.

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Run the Project

Run:

```bash
python detect.py
```

If multiple Python versions are installed on Windows, you can run the tested version directly:

```powershell
py -3.13 detect.py
```

Example output:

```text
Scanned 20 log entries.
Detected 4 anomalies.

[MEDIUM] Score: -0.03 | 2026-10-03 09:15:17 WARNING High CPU usage detected host=app-02 cpu=91%
[HIGH] Score: -0.0173 | 2026-10-03 09:16:23 ERROR Failed login attempt user=admin ip=203.0.113.77
[HIGH] Score: -0.0726 | 2026-10-03 09:17:41 CRITICAL Unauthorized access denied resource=/admin source=198.51.100.8
[MEDIUM] Score: -0.0585 | 2026-10-03 09:18:55 WARNING Request timeout endpoint=/api/orders duration=12000ms

Results saved to anomalies.csv
```

The exact anomaly scores may vary slightly depending on the installed library version.

## Output

Detected anomalies are saved to `anomalies.csv`.

The CSV contains:

- Severity
- Anomaly score
- Original log entry

## Why This Project

This project demonstrates a practical machine learning workflow using Python while keeping the implementation lightweight and easy to understand.

It combines anomaly detection with rule-based prioritization, similar to approaches used in system monitoring, security analysis, operational alerting, and log processing.

## Possible Future Improvements

- Timestamp parsing
- Additional log features
- Configurable severity rules
- Training and testing with larger datasets
- Visualization of detected anomalies
- Processing real application or server logs
