# OpenFDA Device Event Counter

A small Python command-line utility for retrieving FDA Open Data (OpenFDA) medical device adverse event records and exporting them to CSV for exploratory analysis.

This repository contains a straightforward script designed to make OpenFDA queries transparent and auditable, with verbose logging so users can clearly see what is being requested from the API.

---

## Overview

The script supports two primary workflows:

- **Recall-based search**  
  Look up an FDA recall number, resolve associated 510(k) (K numbers) when available, and retrieve linked device event records.

- **Direct K number search**  
  Query medical device event records directly using a 510(k) identifier.

Results are flattened and exported as CSV files for use in Excel, R, Python, or other analysis tools.

---

## Features

- Resolves recall numbers to associated `k_numbers` via OpenFDA device recall data
- Queries OpenFDA device event data for each K number
- Handles OpenFDA pagination limits automatically
- Optional filtering by `date_received`
- Flattens nested JSON into a single-row, analysis-friendly CSV format
- Verbose logging for transparency and traceability

---

## Data Sources

This tool retrieves data from the FDA Open Data (OpenFDA) APIs:

- [Device Recall API](https://open.fda.gov/apis/device/recall/)
- [Device Event API](https://open.fda.gov/apis/device/event/)

**No source data is altered** beyond flattening fields for CSV output.

---

## Requirements

- Python 3.8+
- `requests`

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

Run the script from the command line:

```bash
python Device_Event_Counter.py
```

You will be prompted to choose one of the following:

1. Search by recall number (example format: `Z-1234-2023`)
2. Search directly by K number (example format: `K123456`)

### Optional Date Filtering

You may optionally provide a date range for filtering device events by `date_received`.

**Supported formats:**

- Full date range: `yyyymmdd-yyyymmdd` (e.g., `20200101-20231231`)
- Year shorthand: `yyyy-yyyy` (e.g., `2020-2023`)

When used, the selected date range is reflected in the output filename.

---

## Output

The script writes a CSV file to the current working directory.

**Example output filenames:**

- `fda_events_for_Z-1234-2023.csv`
- `fda_events_for_K123456_20200101_to_20231231.csv`

Nested JSON fields are flattened into individual columns to support spreadsheet review and downstream analysis.

---

## API Key (Optional)

An OpenFDA API key is optional but recommended to increase rate limits.

**To use an API key:**

1. Obtain an API key from the [OpenFDA website](https://open.fda.gov/apis/authentication/)
2. Set the `API_KEY` value at the top of the script

If no key is provided, default public rate limits apply.

---

## Limitations and Interpretation

- Device event reporting is subject to under-reporting, duplicates, and variable data quality.
- Event counts from OpenFDA should **not** be interpreted as incidence or prevalence.
- This tool does not perform deduplication, clinical adjudication, or causality assessment.

---

## Disclaimer

This repository is provided for **research and informational purposes only**.

It is not intended for clinical decision-making, diagnostic use, or regulatory submission.

Use responsibly and interpret results within the known limitations of OpenFDA data.
