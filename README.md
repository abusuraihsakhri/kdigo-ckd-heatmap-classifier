# KDIGO CKD Risk Heatmap Classifier

A deterministic KDIGO 2024 eGFR–albuminuria classification tool for research, education, and clinical-reference workflows. The browser application processes inputs locally and does not require a server.

## Features

- Individual classification across all 18 KDIGO G1–G5 × A1–A3 cells and four prognosis risk groups.
- Accessible, responsive, interactive heatmap with the selected risk cell highlighted.
- Local CSV processing with row-level error reporting and CSV export (browser maximum: 5 MiB, 10,000 records).
- Python CLI, CSV batch classification, and a FastAPI `POST /api/classify` endpoint.
- Separate, optional rule-based audit workflow with an **in-memory**, HMAC-SHA256 integrity-checked ledger.

**Clinical interpretation:** This classifies two measurements, not chronic kidney disease itself. CKD generally requires persistent abnormalities for at least three months; G1A1 and G2A1 do not establish CKD in the absence of other kidney damage. Individual prognosis and management require broader clinical assessment. This tool is not a medical device.

## Open the application

Open `web/index.html` in a modern browser; no installation, network access, or Python is required. The static app can also be hosted on GitHub Pages using the repository's Pages workflow once Pages is enabled and a deployment is confirmed.

The interface runs on ordinary JavaScript, not browser Python or a backend. There are no external scripts or analytics. Uploaded CSV data and results remain in local browser memory, and the CSV download is generated locally. Avoid including patient identifiers; local processing alone does not confer regulatory compliance.

## Python usage

Python 3.10+:

```bash
python -m pip install -e ".[test]"
python kdigo_heatmap.py single --egfr 52 --acr 125
python kdigo_heatmap.py batch -i sample.csv -o results.csv
python cli.py single --egfr 52 --acr 125
python cli.py classify-batch -i sample.csv -o results.csv
```

Python API:

```python
from kdigo_heatmap import classify_ckd
result = classify_ckd(52, 125)
assert result["stage"] == "G3aA2"
assert result["risk_category"] == "high"
```

Batch CSV requires columns named `egfr` (mL/min/1.73 m²) and `acr_mg_g` (mg/g). Additional columns are retained; invalid rows contain an `error` value. Python batch imports are capped at 10 MiB.

The 2024 KDIGO thresholds are:

| Measure | Categories |
| --- | --- |
| eGFR, mL/min/1.73 m² | G1 ≥90; G2 60–<90; G3a 45–<60; G3b 30–<45; G4 15–<30; G5 <15 |
| Urine ACR, mg/g | A1 <30; A2 30–<300; A3 ≥300 |

The risk matrix follows KDIGO 2024 **Figure 13**. At exactly **ACR = 300 mg/g**, Figure 13 labels the value **A3**, while Table 3 lists A2 as 30–300 mg/g and A3 as >300 mg/g. This tool follows Figure 13 for risk mapping and documents that inconsistency; verify local laboratory/reporting conventions at the boundary.

## Optional API and legacy audit utilities

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(40))')"
python cli.py serve
```

`POST /api/classify` accepts JSON `{"egfr":52,"acr_mg_g":125}`; `GET /health` exposes service status. Other available endpoints are `POST /api/audit`, `POST /api/chat`, `GET /api/audit/logs`, and `GET /metrics`. These support an optional deterministic audit demonstration, not validated clinical triage. The chat response is **mock only**, with no external LLM.

The audit endpoint's `primary_metric` means eGFR (mL/min/1.73 m²), and `secondary_metric` means urine ACR (mg/g). The explicit `is_critical_flag` is a caller-supplied workflow flag, not a KDIGO-derived emergency indication. The ledger is process-local, not persistent or externally notarized. A strong `AUDIT_SECRET_KEY` is required when signing entries. The identifier regex is **best-effort**, not a full PHI detection or de-identification solution. Do not expose the demonstration audit API publicly without authentication, authorization, storage, and privacy controls.

For Docker, copy `.env.example` to `.env`, set a newly generated secret key, then run `docker compose up --build`.

## Tests

```bash
python -m pytest -q
node --test web/test_classifier.cjs
node --check web/app.js
```

Python tests require `AUDIT_SECRET_KEY` for audit actions (the CI workflow generates one). CI tests Python 3.10–3.12 and Node 22. The live browser/Pages deployment must be checked independently of local unit tests.

The optional `enrichment.py` engines use synthetic thresholds and are retained only for demonstration; they are not validated models for AKI staging, drug interactions, or clinical recommendations.

## Technical notes

- Python standard library for core risk classification; optional FastAPI/Pydantic for audit API.
- Browser uses plain HTML, CSS, and JavaScript; works with current Chromium, Firefox, and Safari.
- No Pyodide required; no server-side Python can run on GitHub Pages.
- This is not a medical device, and no certification to CAP, CLSI, ISO, HIPAA, or equivalent regulations is claimed.

**Reference:** [KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease](https://kdigo.org/guidelines/ckd-evaluation-and-management/), Figure 13, Tables 2–3.

**License:** MIT (see [LICENSE](LICENSE)).
