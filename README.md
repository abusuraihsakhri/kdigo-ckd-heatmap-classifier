# KDIGO CKD Risk Heatmap & Progression Classifier

> **Domain:** Nephrology & Renal Replacement Protocols
> **Reference Guidelines:** KDIGO & KDOQI Clinical Practice Guidelines

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg?logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-28%20Passed-brightgreen.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

Cross-tabulates eGFR (G1-G5) and Albuminuria (A1-A3) stages into KDIGO 4-tier risk categories (Low, Moderate, High, Very High). Provides a zero-dependency core implementation with CLI, batch CSV processing, FastAPI REST API, and HMAC-SHA256 tamper-evident audit logging.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Features

- **Single Evaluation:** Compute risk classification for individual patient metrics
- **Batch Processing:** Process CSV files with multiple records
- **REST API:** FastAPI-based OpenAPI 3.1 endpoints with Prometheus metrics
- **Tamper-Evident Audit Trail:** HMAC-SHA256 chained cryptographic ledger
- **Zero-PHI Guard:** Regex-based outbound PHI detection and redaction
- **Path Traversal Protection:** Input validation on all file operations
- **Enterprise Agent Framework:** Multi-worker evaluation with consensus scoring

---

## Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/kdigo-ckd-heatmap-classifier.git
cd kdigo-ckd-heatmap-classifier

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[test]"

# Set up environment variables
cp .env.example .env
# Edit .env and set a secure AUDIT_SECRET_KEY (min 16 characters)
```

### Docker

```bash
# Create .env file first
cp .env.example .env
# Edit .env with secure values

# Build and run
docker compose up --build
```

---

## Usage

### CLI Commands

```bash
# Single evaluation
python cli.py single --v1 14.5 --v2 4.2 --v3 1.8

# Batch processing
python cli.py batch -i sample.csv -o results.csv

# Enterprise agent audit (with HMAC audit trail)
python cli.py audit --task-id PT-101 --target SPECIMEN-01 --primary 28.5 --secondary 14.2

# Verify audit integrity
python cli.py verify-audit

# Launch REST API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Direct Module Usage

```bash
# Single evaluation via module
python kdigo_heatmap.py single --v1 12.0 --v2 4.0

# Batch processing via module
python kdigo_heatmap.py batch -i sample.csv -o output.csv
```

### Python API

```python
from kdigo_heatmap import calculate_metrics

result = calculate_metrics(v1=14.5, v2=4.2, v3=1.8)
print(result["score"])           # 17.37
print(result["classification"]) # "Moderate / Intermediate"
```

---

## REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and service metadata |
| `/metrics` | GET | Prometheus operational metrics |
| `/api/audit` | POST | Submit task for multi-worker evaluation |
| `/api/chat` | POST | Supervisory chat query |
| `/api/audit/logs` | GET | Retrieve and verify HMAC audit trail |

### Example API Request

```bash
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "PT-101",
    "target_identifier": "SPECIMEN-01",
    "primary_metric": 28.5,
    "secondary_metric": 14.2,
    "status_descriptor": "DISCORDANT_ANOMALY"
  }'
```

---

## Testing

```bash
# Run full test suite (28 tests)
pytest -v

# Run with coverage
pytest -v --cov=.

# Run high-throughput simulation benchmark
python simulator.py 1000
```

---

## Security

- **Audit Trail Key:** The `AUDIT_SECRET_KEY` environment variable is **required**. Must be at least 16 characters. No default is provided.
- **PHI Protection:** Outbound data is scanned for SSNs, MRNs, phone numbers, emails, and patient names.
- **Path Traversal:** All file operations validate against `..` directory traversal attacks.
- **Input Validation:** API endpoints enforce maximum query length and payload validation via Pydantic v2.

---

## Project Structure

```
kdigo-ckd-heatmap-classifier/
├── agents/                  # Enterprise agent framework
│   ├── api.py              # FastAPI REST server
│   ├── base.py             # Security, PHI guard, HMAC audit
│   ├── models.py           # Pydantic v2 data models
│   ├── supervisor.py       # Orchestrator & consensus engine
│   ├── workers.py          # Specialized evaluation workers
│   ├── llm_factory.py      # LLM provider abstraction
│   ├── metrics.py          # Prometheus metrics collector
│   ├── learning.py         # Bayesian calibration engine
│   └── streamer.py         # WebSocket telemetry
├── tests/                  # Test suite
│   ├── test_security.py    # Security & edge-case tests
│   ├── test_enrichment.py  # Enrichment module tests
│   └── test_kdigo_ckd_heatmap_classifier.py  # Core agent tests
├── web/index.html          # Operations dashboard
├── kdigo_heatmap.py        # Core classification algorithm
├── cli.py                  # CLI entry point
├── enrichment.py           # Domain enrichment engines
├── simulator.py            # Stress testing simulator
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
├── pyproject.toml          # Project metadata & dependencies
└── .env.example            # Environment variable template
```

---

## Algorithm

The core scoring algorithm computes a weighted sum of input metrics:

```python
score = primary_val + Σ(numeric_vals[i] * (1.0 / (i+1)))
```

Classification tiers:
- **< 10.0:** Low / Standard risk
- **10.0 - 24.99:** Moderate / Intermediate risk
- **≥ 25.0:** High / Severe risk
