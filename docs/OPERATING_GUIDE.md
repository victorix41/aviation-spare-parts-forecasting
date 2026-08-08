# Aviation Spare Parts Forecasting — Operating Guide

## 1. Purpose

This guide provides the normal operating procedure for the Aviation
Spare Parts Demand Forecasting platform.

## 2. Start the Environment

Open the WSL terminal and activate the Conda environment:

```bash
conda activate spare-parts-ai
```

Navigate to the project:

```bash
cd ~/Personal\ Projects/aviation-spare-parts-forecasting
```

## 3. Recommended Operating Sequence

The recommended sequence is:

```text
Source Workbook
      ↓
Data Ingestion & Validation
      ↓
Demand Analytics
      ↓
Forecast Model Selection
      ↓
Inventory Optimisation
      ↓
Agentic Advisory
      ↓
DuckDB
      ↓
Management Dashboards
      ↓
Management Report
```

## 4. Run Automated Tests

```bash
pytest -v
```

Do not proceed with a release if tests fail.

## 5. Run the Complete Pipeline

```bash
python -m src.pipeline.run_full_pipeline
```

Expected result:

```text
Overall pipeline status: Passed
Successful stages: 5
Failed stages: 0
```

## 6. Run the Scheduled Workflow Manually

```bash
python -m src.scheduling.run_scheduled_job
```

Expected result:

```text
Overall status: Passed
Stages completed: 2
```

This runs the complete analytical pipeline followed by management-report
generation.

## 7. Concurrent Execution Protection

The scheduled workflow uses:

```text
outputs/reports/scheduled_job.lock
```

to prevent overlapping executions.

The lock is created when a scheduled job starts and removed when the
owning job finishes.

A process that does not own an existing lock must not remove it.

Never manually remove a lock until it has been confirmed that no
scheduled job is actually running.

## 8. Start Streamlit

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## 9. Dashboard Navigation

The sidebar provides:

- Accountable Manager
- Procurement Manager
- Finance Manager
- Engineering Manager
- Operations Manager
- Quality Manager
- Pipeline Monitor
- Management Report

Each management dashboard provides role-specific decision-support
information.

## 10. Pipeline Monitor

Use the Pipeline Monitor to review:

- latest pipeline status;
- pipeline run ID;
- successful and failed stages;
- pipeline duration;
- scheduled-job status;
- scheduled-job freshness;
- scheduled workflow stages;
- job-lock status;
- recent scheduled-job logs.

## 11. Management Report

The Management Report page allows an authorised user to generate and
download the latest management workbook.

The workbook is also available under:

```text
outputs/reports/
```

## 12. Production-Readiness Check

Before release or formal demonstration, run:

```bash
python -m src.validation.run_production_readiness
```

Required result:

```text
PRODUCTION READINESS: PASSED
```

## 13. Stop Streamlit

Use:

```text
Ctrl + C
```

in the terminal running Streamlit.

## 14. Source-Control Procedure

Check changes:

```bash
git status
git diff --stat
```

Commit approved changes:

```bash
git add .
git commit -m "Describe the approved change"
git push origin main
```

Verify:

```bash
git status
```

Expected:

```text
nothing to commit, working tree clean
```

## 15. Scheduling Deployment Status

The scheduling-ready application workflow has been implemented and
tested.

Automatic Windows Task Scheduler deployment is currently deferred.

The workflow can therefore be executed manually using:

```bash
python -m src.scheduling.run_scheduled_job
```