# Troubleshooting Guide

## 1. Streamlit Does Not Open Automatically

WSL may display:

```text
gio: http://localhost:8501: Operation not supported
```

This does not necessarily mean Streamlit failed.

Open the browser manually:

```text
http://localhost:8501
```

## 2. Dashboard Appears Narrow

Confirm that `app.py` configures Streamlit with:

```python
st.set_page_config(
    layout="wide",
)
```

Also check that custom CSS does not restrict the Streamlit
`.block-container`.

## 3. Duplicate Streamlit Widget Error

Ensure:

```python
render_sidebar()
```

is called only once during application execution.

Use a unique widget key such as:

```python
key="management_view_navigation"
```

## 4. Python Syntax Error

Compile the affected file:

```bash
python -m py_compile path/to/file.py
```

Pay particular attention to multiline f-strings.

Prefer:

```python
value = float(result["value"])

st.metric(
    "Value",
    f"{value:.2f}",
)
```

rather than nesting a multiline expression inside an f-string.

## 5. Tests Fail

Run:

```bash
pytest -v
```

Correct the first meaningful failure before proceeding.

Do not commit a release while tests are failing.

## 6. Full Pipeline Failure

Run:

```bash
python -m src.pipeline.run_full_pipeline
```

Review:

```text
outputs/reports/full_pipeline_summary.json
```

Identify the failed pipeline stage before rerunning the complete system.

## 7. Scheduled Job Failure

Run:

```bash
python -m src.scheduling.run_scheduled_job
```

Review:

```text
outputs/reports/scheduled_job_summary.json
```

and:

```text
outputs/logs/
```

## 8. Scheduled Job Reports Another Job Is Running

Check:

```bash
ls -l outputs/reports/scheduled_job.lock
```

Do not immediately delete the lock.

First confirm that no legitimate scheduled job is still running.

## 9. Management Report Failure

Run:

```bash
python -m src.reporting.run_management_report
```

Confirm that the latest pipeline outputs and DuckDB tables are
available.

## 10. Production-Readiness Failure

Run:

```bash
python -m src.validation.run_production_readiness
```

Then inspect:

```text
outputs/reports/production_readiness_summary.json
```

The individual failed check should identify the area requiring
attention.

## 11. DuckDB Table Investigation

A quick table inspection can be performed with Python:

```bash
python - <<'PY'
import duckdb

with duckdb.connect(
    "database/aviation_spares.duckdb"
) as con:
    tables = con.execute(
        "SHOW TABLES"
    ).fetchall()

for table in tables:
    print(table[0])
PY
```

## 12. Final Recovery Check

After correcting a problem, run:

```bash
pytest -v
python -m src.scheduling.run_scheduled_job
python -m src.validation.run_production_readiness
```

The final readiness result should be:

```text
PRODUCTION READINESS: PASSED
```