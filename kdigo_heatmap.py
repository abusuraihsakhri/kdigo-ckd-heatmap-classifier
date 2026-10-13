#!/usr/bin/env python3
"""KDIGO 2024 CKD GFR–albuminuria risk heatmap.

Risk classification is not a diagnosis or a patient-specific treatment decision.
Source: KDIGO 2024 CKD Guideline, Figure 13 and Tables 2–3.
https://kdigo.org/guidelines/ckd-evaluation-and-management/
"""
import argparse
import csv
import json
import math
import os
from typing import Any, Dict

GFR_CATEGORIES = ("G1", "G2", "G3a", "G3b", "G4", "G5")
ALBUMINURIA_CATEGORIES = ("A1", "A2", "A3")
# KDIGO four-tier risk grid (GFR row, albuminuria column).
RISK_GRID = (
    ("low", "moderately increased", "high"),
    ("low", "moderately increased", "high"),
    ("moderately increased", "high", "very high"),
    ("high", "very high", "very high"),
    ("very high", "very high", "very high"),
    ("very high", "very high", "very high"),
)
CHRONICITY_NOTE = (
    "A single eGFR/ACR result cannot diagnose CKD. Abnormalities must persist "
    "for at least 3 months, or other qualifying evidence of chronic kidney disease "
    "must be established."
)


def _nonnegative_finite(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite, nonnegative number") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite, nonnegative number")
    return number


def classify_ckd(egfr: float, acr_mg_g: float) -> Dict[str, Any]:
    """Classify eGFR (mL/min/1.73 m²) and urine ACR (mg/g) by KDIGO 2024.

    ACR cutoffs follow KDIGO 2024 Figure 13: A1 <30, A2 30–<300,
    A3 >=300 mg/g. Table 3 differs at exactly 300 mg/g, listing
    A2 as 30–300 and A3 as >300. Figure 13 controls risk mapping.
    Do not interpret this risk group as confirmed CKD.
    """
    egfr = _nonnegative_finite(egfr, "egfr")
    acr_mg_g = _nonnegative_finite(acr_mg_g, "acr_mg_g")
    g = (0 if egfr >= 90 else 1 if egfr >= 60 else
         2 if egfr >= 45 else 3 if egfr >= 30 else
         4 if egfr >= 15 else 5)
    a = 0 if acr_mg_g < 30 else 1 if acr_mg_g < 300 else 2
    risk = RISK_GRID[g][a]
    return {
        "egfr": egfr,
        "acr_mg_g": acr_mg_g,
        "gfr_category": GFR_CATEGORIES[g],
        "albuminuria_category": ALBUMINURIA_CATEGORIES[a],
        "stage": f"{GFR_CATEGORIES[g]}{ALBUMINURIA_CATEGORIES[a]}",
        "risk_category": risk,
        "classification": risk,
        "ckd_confirmed": None,
        "clinical_note": CHRONICITY_NOTE + (
            " If no other markers of kidney damage are present, G1A1 and "
            "G2A1 do not meet CKD criteria."
            if g <= 1 and a == 0 else ""
        ),
        "guideline": "KDIGO 2024 CKD Guideline",
    }


def calculate_metrics(*, egfr: float, acr_mg_g: float) -> Dict[str, Any]:
    """Backward-compatible function name with corrected clinical inputs."""
    return classify_ckd(egfr, acr_mg_g)


def _safe_path(path: str) -> str:
    """Reject explicit .. path components (not a sandbox boundary)."""
    if ".." in path.replace("\\", "/").split("/"):
        raise ValueError("Path traversal detected")
    return os.path.abspath(os.path.normpath(path))


def process_batch(input_csv: str, output_csv: str) -> None:
    """Classify CSV rows locally; retain invalid rows with an error column."""
    src, dst = _safe_path(input_csv), _safe_path(output_csv)
    if os.path.samefile(src, dst) if os.path.isfile(src) and os.path.isfile(dst) else src == dst:
        raise ValueError("Input and output files must differ")
    if not os.path.isfile(src):
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")
    if os.path.getsize(src) > 10 * 1024 * 1024:
        raise ValueError("Input CSV exceeds 10 MiB limit")
    with open(src, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if len(set(columns)) != len(columns) or not {"egfr", "acr_mg_g"} <= set(columns):
            raise ValueError("CSV must include unique 'egfr' and 'acr_mg_g' headers")
        if any(c is None or not c for c in columns):
            raise ValueError("CSV column names cannot be empty")
        rows = list(reader)
    results = []
    for row in rows:
        if None in row:
            detail = "Unexpected extra CSV columns"
            stage = risk = ""
        else:
            try:
                result = classify_ckd(row["egfr"], row["acr_mg_g"])
                stage, risk, detail = result["stage"], result["risk_category"], ""
            except ValueError as exc:
                stage, risk, detail = "", "", str(exc)
        results.append({**{key: row.get(key, "") for key in columns},
                        "stage": stage, "risk_category": risk, "error": detail})
    fields = [c for c in columns if c not in ("stage", "risk_category", "error")]
    fields += ["stage", "risk_category", "error"]
    # Prevent formula execution if resulting CSV is opened in spreadsheet software.
    for record in results:
        for key, value in record.items():
            text = str(value) if value is not None else ""
            if text.lstrip().startswith(("=", "+", "-", "@")):
                record[key] = "'" + text
    with open(dst, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"Processed {len(results)} records -> {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="KDIGO 2024 CKD GFR–albuminuria classifier")
    sub = parser.add_subparsers(dest="command", required=True)
    single = sub.add_parser("single", help="Classify an eGFR and urine ACR")
    single.add_argument("--egfr", type=float, required=True, help="mL/min/1.73 m²")
    single.add_argument("--acr", type=float, required=True, help="Urine ACR in mg/g")
    batch = sub.add_parser("batch", help="Classify a CSV containing egfr,acr_mg_g")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            print(json.dumps(classify_ckd(args.egfr, args.acr), indent=2))
        else:
            process_batch(args.input, args.output)
    except (ValueError, FileNotFoundError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
