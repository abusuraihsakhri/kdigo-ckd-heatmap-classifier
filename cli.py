"""
Command Line Interface for Kdigo Ckd Heatmap Classifier.
"""
import argparse
import csv
import json
import os
import sys
from kdigo_heatmap import classify_ckd, process_batch as classify_batch
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from agents.base import AuditLogger, SecurityException


def _safe_path(path: str) -> str:
    """Validate that a file path is safe (no directory traversal via ..)."""
    # Check raw path components before normalization
    parts = path.replace("\\", "/").split("/")
    if ".." in parts:
        raise ValueError(f"Path traversal detected: '{path}' contains '..' components.")
    return os.path.abspath(os.path.normpath(path))

supervisor = SystemSupervisor(model_provider="mock")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kdigo-ckd-heatmap-classifier", description="Kdigo Ckd Heatmap Classifier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # KDIGO clinical classification
    p_single = subparsers.add_parser("single", help="Classify an eGFR/urine ACR pair")
    p_single.add_argument("--egfr", type=float, required=True, help="mL/min/1.73 m²")
    p_single.add_argument("--acr", type=float, required=True, help="urine ACR in mg/g")
    p_ckd_batch = subparsers.add_parser("classify-batch", help="Classify CSV eGFR/ACR rows")
    p_ckd_batch.add_argument("-i", "--input", required=True)
    p_ckd_batch.add_argument("-o", "--output", default="results.csv")

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Verify Audit
    subparsers.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "single":
        try:
            print(json.dumps(classify_ckd(args.egfr, args.acr), indent=2))
            return 0
        except ValueError as error:
            parser.error(str(error))

    if args.command == "classify-batch":
        try:
            classify_batch(args.input, args.output)
            return 0
        except (ValueError, FileNotFoundError, OSError) as error:
            parser.error(str(error))

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print("=" * 80)
        print(f"  KDIGO CKD HEATMAP CLASSIFIER")
        print(f"  Reference: KDIGO 2024 CKD Guideline | Rule-based demonstration")
        print(f"  Dossier ID: {dossier.dossier_id} | Urgency: [{dossier.overall_urgency.value}]")
        print("=" * 80)
        for a in dossier.alerts:
            print(f"\n  [{a.urgency.value}] from {a.origin_worker}:")
            print(f"  Summary: {a.summary}")
            print(f"  Details: {a.technical_details}")
            print(f"  Action:  {a.actionable_remediation}")
        print(f"\n  Process-local HMAC-SHA256 Audit Hash: {dossier.audit_hash}")
        print("=" * 80)
        return 0

    if args.command == "chat":
        ans = supervisor.query_supervisory_chat(" ".join(args.query))
        print(f"\n[Kdigo Ckd Heatmap Classifier Supervisor]:\n{ans}\n")
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit Trail Blocks: {len(trail)} | Cryptographic Integrity Verified: {valid}")
        return 0

    if args.command == "batch":
        safe_input = _safe_path(args.input)
        safe_output = _safe_path(args.output)

        if not os.path.isfile(safe_input):
            print(f"Error: Input CSV not found: '{args.input}'", file=sys.stderr)
            return 1

        with open(safe_input, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        out_fields = fieldnames + ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]
        out_rows = []
        for r in rows:
            try:
                payload = SystemTaskPayload(
                    task_id=r.get("task_id", "TASK-01"),
                    target_identifier=r.get("target_identifier", "TARGET-01"),
                    primary_metric=float(r.get("primary_metric", 15.0)),
                    secondary_metric=float(r.get("secondary_metric", 5.0)),
                    status_descriptor=r.get("status_descriptor", "NOMINAL"),
                    is_critical_flag=str(r.get("is_critical_flag", "")).lower() in ("true", "1", "yes"),
                )
                dossier = supervisor.process_task(payload)
            except (ValueError, SecurityException) as e:
                print(f"Warning: Skipping row due to error: {e}", file=sys.stderr)
                continue
            row_dict = dict(r)
            row_dict["overall_urgency"] = dossier.overall_urgency.value
            row_dict["integrity_status"] = dossier.integrity_status.value
            row_dict["total_alerts"] = dossier.total_alerts
            row_dict["audit_hash"] = dossier.audit_hash
            out_rows.append(row_dict)

        with open(safe_output, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"Processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "serve":
        import uvicorn
        from agents.api import app
        print(f"Starting Kdigo Ckd Heatmap Classifier API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
