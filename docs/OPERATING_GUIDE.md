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
- recent scheduled-job logs;
- production-readiness and governance-assurance status;
- data-quality monitoring status;
- required-table availability;
- human-approval governance status;
- automatic-purchasing control status; and
- inventory write-back control status.

## 11. Management Report

The Management Report page allows an authorised user to generate and
download the latest management workbook.

The workbook is also available under:

```text
outputs/reports/
```

## 12. Management Decision Review

Management dashboards provide governed decision-support capabilities for
assured agent recommendations.

Where a management decision audit is available, authorised personnel may
record a recommendation as:

- Accepted
- Deferred
- Rejected

A decision reason must be recorded.

The optional reviewer reference may be used to record a name, initials,
role or internal review reference.

Recording a management decision creates an audit record only.

It does not:

- create or approve a purchase order;
- update inventory;
- approve expenditure;
- execute an operational action; or
- replace required engineering, quality, procurement, finance or
  operational approval.

Management decisions remain subject to authorised human review.

## 13. Management Decision Analytics

Management decision analytics are available within the applicable
management dashboards.

The analytics provide visibility of:

- total recorded decisions;
- Accepted decisions;
- Deferred decisions;
- Rejected decisions;
- parts reviewed;
- recommendations reviewed;
- decision breakdown by management role;
- decision breakdown by recommendation priority; and
- recent management decisions.

The analytics are derived from the management decision audit database.

They are provided for management oversight and traceability only and do
not update any operational system.

## 14. Management Alerts and Exceptions

Management dashboards may display configurable alerts and exceptions
derived from validated analytical and advisory outputs.

Alerts support management attention and prioritisation. They do not
constitute automatic operational instructions.

Critical or high-priority alerts should be reviewed by the appropriate
authorised manager together with the supporting evidence before any
management action is taken.

## 15. Production-Readiness Check

Before release or formal demonstration, run:

```bash
python -m src.validation.run_production_readiness
```

Required result:

```text
PRODUCTION READINESS: PASSED
```

## 16. Stop Streamlit

Use:

```text
Ctrl + C
```

in the terminal running Streamlit.

## 17. Source-Control Procedure

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

## 18. Scheduling Deployment Status

The scheduling-ready application workflow has been implemented and
tested.

Automatic Windows Task Scheduler deployment is currently deferred.

The workflow can therefore be executed manually using:

```bash
python -m src.scheduling.run_scheduled_job
```