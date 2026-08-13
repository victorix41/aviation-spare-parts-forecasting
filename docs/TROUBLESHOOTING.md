# Troubleshooting Guide

This guide provides troubleshooting and recovery procedures for the
Aviation Spare Parts Forecasting and Agentic Decision-Support Platform.

The system is designed as governed decision support. Forecasts,
inventory-optimisation outputs, agent recommendations and management
analytics do not automatically create purchase orders, update inventory,
approve expenditure or trigger operational actions.

Human management review and approval remain required.

---

## 1. Streamlit Does Not Open Automatically

When running the application under WSL, Streamlit may display:

```text
gio: http://localhost:8501: Operation not supported
```

This does not necessarily mean that Streamlit has failed.

Start the application with:

```bash
streamlit run app.py
```

Then open the browser manually:

```text
http://localhost:8501
```

If the page still does not load, review the terminal for a Python
traceback or application error.

---

## 2. Dashboard Appears Narrow

Confirm that `app.py` configures Streamlit with a wide layout:

```python
st.set_page_config(
    layout="wide",
)
```

Also check that custom CSS does not unnecessarily restrict the
Streamlit `.block-container`.

Restart Streamlit after making changes:

```bash
streamlit run app.py
```

---

## 3. Duplicate Streamlit Widget Error

A duplicate widget error normally means that Streamlit has created two
widgets with the same internal identifier.

Ensure:

```python
render_sidebar()
```

is called only once during application execution.

Where necessary, provide explicit and unique widget keys, for example:

```python
key="management_view_navigation"
```

Reusable dashboard components should also use unique keys when the same
component may appear in more than one management view.

---

## 4. Python Syntax or Import Error

Compile an individual affected file with:

```bash
python -m py_compile path/to/file.py
```

To compile the application and all source modules:

```bash
python -m compileall -q app.py src
```

Pay particular attention to:

- indentation;
- unmatched brackets;
- malformed multiline strings;
- multiline f-strings;
- incorrect imports; and
- code accidentally placed outside a function.

Prefer:

```python
value = float(result["value"])

st.metric(
    "Value",
    f"{value:.2f}",
)
```

rather than nesting a complex multiline expression inside an f-string.

---

## 5. `NameError: repository is not defined`

A `NameError` involving `repository` may occur when dashboard rendering
code has accidentally been placed at module level instead of inside its
dashboard-rendering function.

For example, a call such as:

```python
render_management_drilldown(
    repository=repository,
)
```

must execute inside a function where `repository` has been supplied or
defined.

Inspect the relevant dashboard file and confirm that the call is
correctly indented inside its rendering function.

After correcting the file, run:

```bash
python -m compileall -q app.py src
pytest -q
```

---

## 6. Dashboard Function Argument Error

An error similar to:

```text
render_operations_dashboard() takes 2 positional arguments but 3 were given
```

means that the function definition and the call in `app.py` do not have
matching parameters.

Check the function definition, for example:

```bash
grep -n "^def render_.*dashboard" src/dashboards/*.py
```

Then compare it with the corresponding call in:

```text
app.py
```

Management dashboards that use the management decision audit capability
must receive the required audit database path consistently.

After correcting the function signature or call, run:

```bash
python -m compileall -q app.py src
pytest -q
```

---

## 7. Tests Fail

Run:

```bash
pytest -v
```

For a shorter result:

```bash
pytest -q
```

Correct the first meaningful failure before proceeding to later
failures.

A specific test module can be run independently, for example:

```bash
pytest -q tests/test_decision_audit.py
```

or:

```bash
pytest -q tests/test_production_readiness.py
```

Do not commit or release changes while tests are failing.

---

## 8. Full Pipeline Failure

Run:

```bash
python -m src.pipeline.run_full_pipeline
```

Review:

```text
outputs/reports/full_pipeline_summary.json
```

Identify the failed pipeline stage before rerunning the complete system.

The underlying DuckDB database can also be inspected if a pipeline stage
appears to have completed but its expected data is unavailable.

---

## 9. Scheduled Job Failure

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

Confirm which scheduled workflow stage failed before rerunning the job.

---

## 10. Scheduled Job Reports Another Job Is Running

Check the scheduled-job lock:

```bash
ls -l outputs/reports/scheduled_job.lock
```

Do not immediately delete the lock file.

First confirm that no legitimate scheduled job is still running.

If the lock is stale and no scheduled process is active, follow the
approved recovery procedure before removing it.

Production-readiness validation also checks that no active scheduled-job
lock remains.

---

## 11. Management Report Failure

Run:

```bash
python -m src.reporting.run_management_report
```

Confirm that:

- the latest pipeline run completed successfully;
- required DuckDB tables are available;
- the reporting output directory is writable; and
- the required analytics outputs contain records.

Review the generated report and associated pipeline status before
distributing it to management.

---

## 12. Production-Readiness or Governance-Assurance Failure

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

Production-readiness checks include system, pipeline and governance
controls.

The governance controls must continue to demonstrate that:

- human approval is required;
- automatic purchasing is disabled;
- inventory write-back is disabled; and
- the system remains decision support rather than an autonomous
  operational approval mechanism.

A successful result should report:

```text
PRODUCTION READINESS: PASSED
```

A passed readiness result authorises governed decision support only. It
does not authorise automatic purchasing, inventory changes, expenditure
approval or operational action.

---

## 13. Main DuckDB Database Investigation

A quick inspection of the main analytics database can be performed with
Python:

```bash
python - <<'PY'
import duckdb

with duckdb.connect(
    "database/aviation_spares.duckdb",
    read_only=True,
) as con:
    tables = con.execute(
        "SHOW TABLES"
    ).fetchall()

for table in tables:
    print(table[0])
PY
```

If an expected table is missing, investigate the pipeline stage
responsible for creating that table.

To inspect record counts, use an appropriate read-only query against the
required table.

Do not manually modify production analytics tables merely to make a
dashboard or readiness check pass.

---

## 14. Management Decision Audit Failure

If a management decision cannot be recorded, first confirm that the
management audit database exists:

```bash
ls -l database/management_audit.duckdb
```

Then confirm that the expected audit table is available:

```bash
python - <<'PY'
import duckdb

with duckdb.connect(
    "database/management_audit.duckdb",
    read_only=True,
) as con:
    print(
        con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchdf()
    )
PY
```

The expected table is:

```text
management_decision_audit
```

The management audit database is intentionally separate from the main
analytics database.

Management decision records are audit records only. Recording a
decision must not:

- create a purchase order;
- update inventory;
- approve expenditure; or
- trigger an operational action.

---

## 15. Inspect Recent Management Decision Audit Records

To confirm that management decisions are being recorded, run:

```bash
python - <<'PY'
import duckdb

with duckdb.connect(
    "database/management_audit.duckdb",
    read_only=True,
) as con:
    print(
        con.execute(
            """
            SELECT *
            FROM management_decision_audit
            ORDER BY recorded_at DESC
            LIMIT 5
            """
        ).fetchdf().to_string(index=False)
    )
PY
```

Confirm that the expected fields are populated, including the
recommendation identifier, part number, target management role,
management decision and reviewer information where supplied.

The audit trail should be treated as append-only management evidence.

---

## 16. Management Decision Analytics Appears Empty

Management Decision Analytics is derived from the management decision
audit database.

If the analytics section is empty, first confirm that audit records
exist:

```bash
python - <<'PY'
import duckdb

with duckdb.connect(
    "database/management_audit.duckdb",
    read_only=True,
) as con:
    count = con.execute(
        """
        SELECT COUNT(*)
        FROM management_decision_audit
        """
    ).fetchone()[0]

print(
    "Management decisions:",
    count,
)
PY
```

If the count is zero, the empty analytics view may be valid because no
management decisions have yet been recorded.

If records exist but analytics remain empty, inspect:

```text
src/audit/decision_analytics.py
```

and:

```text
src/dashboards/decision_analytics_dashboard.py
```

Then run the relevant tests:

```bash
pytest -q tests/test_decision_analytics.py
```

---

## 17. Data-Quality Monitoring Reports Findings

If Data Quality Monitoring reports an exception, do not suppress the
finding simply to obtain a passed dashboard status.

Review:

- the affected table;
- the affected field;
- the configured validation rule;
- the source workbook data; and
- the latest pipeline output.

Confirm that the configured data-quality rule is appropriate before
changing either source data or validation logic.

After correcting the underlying problem, rerun the pipeline and relevant
tests.

---

## 18. Management Alerts or Exceptions Appear Unexpectedly

Management alerts are decision-support indicators derived from validated
analytics and configured thresholds.

If an unexpected alert appears:

1. identify the affected part number;
2. identify the alert type and severity;
3. review the supporting evidence;
4. confirm the relevant source analytics;
5. confirm the configured alert threshold; and
6. determine whether the alert is valid before changing configuration.

Do not remove or weaken an alert rule solely to eliminate an
uncomfortable management result.

Alerts do not themselves trigger procurement, inventory or operational
actions.

---

## 19. Forecast Explainability Is Missing

If forecast explainability is unavailable for a selected spare part,
confirm that the part has:

- historical demand data;
- forecast backtest results;
- a selected forecast model; and
- a final forecast.

Inspect the relevant main database tables before changing dashboard
logic.

A lack of explainability evidence should be displayed as unavailable
rather than replaced with invented explanatory text.

---

## 20. Agent Advisory Traceability Is Missing

If agent advisory evidence is unavailable, confirm that the relevant
part has an agent recommendation and associated assurance information.

The dashboard should display only assured recommendations that satisfy
the configured management-display requirements.

Do not create substitute advisory evidence manually.

Agent recommendations remain decision-support outputs and require human
review.

---

## 21. Pipeline Monitor Shows Stale Results

A scheduled execution can have a successful status while its result is
still classified as stale.

Review:

```text
outputs/reports/scheduled_job_summary.json
```

and the recent scheduled-job logs under:

```text
outputs/logs/
```

Confirm the latest execution timestamp and configured freshness
requirements.

A stale result should not automatically be interpreted as a pipeline
failure; it means that the last successful result is older than the
configured freshness expectation.

Run a new scheduled execution when appropriate:

```bash
python -m src.scheduling.run_scheduled_job
```

---

## 22. `KeyError: 'paths'` or Similar Settings Error

An error such as:

```text
KeyError: 'paths'
```

normally indicates that a function has received only a subsection of
`config/settings.yaml` when it expects the complete settings mapping.

Check the function definition and its caller.

For example, distinguish between passing:

```python
settings
```

and:

```python
settings["dashboard"]
```

The correct argument depends on what the receiving function expects.

Do not solve the problem by duplicating unrelated settings into another
configuration section.

After correcting the settings argument, run:

```bash
python -m compileall -q app.py src
pytest -q
```

and perform a manual Streamlit check.

---

## 23. Streamlit Shows a File Save or Reload Conflict During Development

When a source file is changed externally while it is also open with
unsaved changes in VS Code, VS Code may report that the file is newer on
disk.

Do not immediately overwrite the file.

Use the VS Code comparison view to compare:

- the version currently on disk; and
- the unsaved editor version.

Preserve the intended changes, resolve the conflict and save the final
version.

Then verify:

```bash
git diff --check
python -m compileall -q app.py src
pytest -q
```

---

## 24. Git Reports Trailing Whitespace

Run:

```bash
git diff --check
```

If Git reports:

```text
trailing whitespace
```

open the identified file and remove the spaces or tabs at the end of the
reported line.

Run again:

```bash
git diff --check
```

A successful check produces no output.

---

## 25. Git Push Appears to Hang

First check repository status:

```bash
git status
```

Then confirm the configured remote:

```bash
git remote -v
```

Test remote connectivity:

```bash
git ls-remote origin
```

If the command also hangs, test connectivity to GitHub:

```bash
curl -I --connect-timeout 10 https://github.com
```

A connection timeout indicates a network or connectivity problem rather
than a Git commit problem.

Do not repeatedly recreate commits while the network is unavailable.

Once connectivity is restored, run:

```bash
git push origin main
```

Then verify:

```bash
git status
```

The expected result is:

```text
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

---

## 26. Final Recovery Check

After correcting a system problem, run the relevant validation sequence.

First check source formatting and compilation:

```bash
git diff --check
python -m compileall -q app.py src
```

Run the complete automated test suite:

```bash
pytest -q
```

Run the end-to-end pipeline when the correction affects data processing,
forecasting, optimisation, agents or downstream outputs:

```bash
python -m src.pipeline.run_full_pipeline
```

Run the scheduled workflow when the correction affects scheduled
execution or reporting:

```bash
python -m src.scheduling.run_scheduled_job
```

Finally run:

```bash
python -m src.validation.run_production_readiness
```

The final readiness result should be:

```text
PRODUCTION READINESS: PASSED
```

Also perform a manual Streamlit verification:

```bash
streamlit run app.py
```

Review the applicable management views, Pipeline Monitor, management
decision audit and analytics, alerts, data-quality monitoring and
production-readiness information.

---

## 27. Troubleshooting Principles

When troubleshooting this platform:

- correct the underlying problem rather than suppressing the symptom;
- preserve source-data traceability;
- preserve management decision audit records;
- do not fabricate missing forecast or advisory evidence;
- do not manually alter analytics merely to obtain a passed status;
- do not weaken governance controls to bypass a readiness failure;
- keep automatic purchasing disabled;
- keep inventory write-back disabled;
- retain mandatory human approval; and
- rerun the appropriate tests and assurance checks after every material
  correction.

The platform must remain a governed aviation spare-parts
decision-support system with human management accountability.