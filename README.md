# Aviation Spare Parts Demand Forecasting

A Python-based aviation spare-parts demand forecasting, inventory
optimisation, agentic advisory and management decision-support platform.

## 1. Project Purpose

The platform supports aviation spare-parts planning and management
decision-making through an integrated workflow covering:

- source-data ingestion and validation;
- historical demand analytics;
- intermittent-demand analysis;
- forecast model selection and backtesting;
- spare-parts demand forecasting;
- inventory optimisation;
- procurement prioritisation;
- role-based agentic AI advisory;
- management dashboards;
- pipeline monitoring;
- management reporting;
- scheduling-ready execution;
- data-quality monitoring;
- management alerts and exception monitoring;
- management decision audit trails;
- management decision analytics;
- governance and assurance monitoring;
- production-readiness validation.

The system is designed as a **decision-support platform**. It does not
replace authorised management, engineering, quality, procurement or
financial decision-making.

## 2. Governance Principles

The application operates under the following controls:

- no automatic purchase-order creation;
- no automatic inventory write-back;
- no automatic financial approval;
- human approval is mandatory;
- forecasts are advisory;
- agentic AI recommendations are advisory;
- evidence and assurance checks are required;
- operational decisions remain the responsibility of authorised personnel;
- management decisions recorded in the platform create audit records only;
- recording an Accepted, Deferred or Rejected decision does not execute
  an operational action;
- management decision records are retained separately for traceability;
- production-readiness assurance includes data-quality, agent-assurance
  and management decision-audit checks.

## 3. Technology Stack

The principal technologies include:

- Python 3.11
- pandas
- NumPy
- DuckDB
- Streamlit
- Plotly
- openpyxl
- PyYAML
- pytest

The development environment uses Conda and WSL Ubuntu.

## 4. Project Structure

```text
aviation-spare-parts-forecasting/
├── config/
│   ├── settings.yaml
│   └── workbook_mapping.yaml
├── data/
├── database/
├── docs/
├── outputs/
│   ├── exports/
│   ├── forecasts/
│   ├── logs/
│   └── reports/
├── scripts/
│   └── run_scheduled_job.sh
├── src/
│   ├── agents/
│   ├── analytics/
│   ├── audit/
│   ├── dashboards/
│   ├── data/
│   ├── forecasting/
│   ├── optimisation/
│   ├── pipeline/
│   ├── reporting/
│   ├── scheduling/
│   ├── utils/
│   └── validation/
├── tests/
├── app.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 5. Environment

Activate the project Conda environment:

```bash
conda activate spare-parts-ai
```

Move to the project directory:

```bash
cd ~/Personal\ Projects/aviation-spare-parts-forecasting
```

## 6. Run Automated Tests

Before operating or releasing the application:

```bash
pytest -v
```

All tests should pass.

## 7. Run the End-to-End Pipeline

```bash
python -m src.pipeline.run_full_pipeline
```

The pipeline performs:

1. Data ingestion and validation
2. Demand analytics
3. Forecast model selection
4. Inventory optimisation
5. Agentic advisory generation

A successful run reports:

```text
Overall pipeline status: Passed
Successful stages: 5
Failed stages: 0
```

## 8. Run the Management Dashboard

```bash
streamlit run app.py
```

Open the application in a browser at:

```text
http://localhost:8501
```

The application provides the following management views:

1. Accountable Manager
2. Procurement Manager
3. Finance Manager
4. Engineering Manager
5. Operations Manager
6. Quality Manager
7. Pipeline Monitor
8. Management Report

## 9. Generate the Management Report

```bash
python -m src.reporting.run_management_report
```

The generated Excel workbook is stored under:

```text
outputs/reports/
```

The report provides management-level forecasting, inventory,
procurement, engineering, operational, quality and pipeline information.

## 10. Run the Scheduling-Ready Workflow

```bash
python -m src.scheduling.run_scheduled_job
```

This executes:

1. the complete pipeline;
2. management-report generation;
3. scheduled-job audit logging;
4. JSON execution-summary generation; and
5. concurrent-execution protection.

A successful run reports:

```text
Overall status: Passed
Stages completed: 2
```

Windows Task Scheduler deployment is optional and is currently deferred.

## 11. Production-Readiness Validation

Run:

```bash
python -m src.validation.run_production_readiness
```

The expected result for a healthy system is:

```text
PRODUCTION READINESS: PASSED
```

The detailed result is written to:

```text
outputs/reports/production_readiness_summary.json
```

## 12. Management Decision Governance

The platform provides a controlled management decision-audit capability
for assured agent recommendations.

Authorised management users may record a recommendation as:

- Accepted
- Deferred
- Rejected

A decision reason is required.

Recorded management decisions are audit records only. Recording a
decision does not:

- create or approve a purchase order;
- update inventory;
- approve expenditure;
- execute an operational action; or
- replace an authorised engineering, quality, procurement, finance or
  operational approval.

Management decision records are retained in the management audit
database for traceability and decision analytics.

The management decision analytics capability provides visibility of:

- total recorded decisions;
- Accepted, Deferred and Rejected decisions;
- parts reviewed;
- recommendations reviewed;
- decisions by management role;
- decisions by recommendation priority; and
- recent management decisions.

## 13. Important Outputs

Key generated outputs include:

```text
database/aviation_spares.duckdb
database/management_audit.duckdb

outputs/reports/full_pipeline_summary.json
outputs/reports/scheduled_job_summary.json
outputs/reports/production_readiness_summary.json
outputs/reports/aviation_spare_parts_management_report.xlsx

outputs/logs/
```

Generated operational data, databases and reports should not be
committed to Git unless explicitly required.

## 14. Release Status

The application has completed:

- Phase 2 — Data ingestion and validation
- Phase 3.1 — Demand analytics
- Phase 3.2 — Forecast model development
- Phase 3.3 — Forecast model selection
- Phase 3.4 — Inventory optimisation
- Phase 3.5 — Agentic AI advisory
- Phase 3.6 — Management dashboards
- Phase 4.1 — End-to-end pipeline
- Phase 4.2 — Pipeline monitoring
- Phase 4.3 — Management reporting
- Phase 4.4 — Dashboard report download
- Phase 4.5 — Scheduling-ready execution
- Phase 4.6 — Scheduled-job monitoring and concurrency hardening
- Phase 4.7 — Production-readiness validation
- Phase 5 — Release documentation and handover
- Phase 6.1 — Management dashboard enhancement
- Phase 6.2 — Forecast explainability
- Phase 6.3 — Agent advisory traceability
- Phase 6.4 — Configurable management alerts and exceptions
- Phase 6.5 — Data-quality monitoring
- Phase 6.6 — Management decision audit trail
- Phase 6.7 — Management decision analytics
- Phase 6.8 — Production readiness and governance assurance
- Phase 6.9 — Final documentation and project closure

## 15. Release

Target release:

```text
v1.0.0
```

This release represents the production-readiness-validated version of
the aviation spare-parts forecasting, agentic advisory and governed
management decision-support platform.

The platform provides forecasting, inventory optimisation, agentic
advisory, management alerts, decision auditing, decision analytics,
data-quality monitoring and production-readiness assurance while
maintaining mandatory human oversight.

The platform does not perform automatic purchasing, inventory
write-back, financial approval or operational execution.