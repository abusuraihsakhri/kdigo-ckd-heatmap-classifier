"""
FastAPI REST API Server for Kdigo Ckd Heatmap Classifier.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor
from kdigo_heatmap import classify_ckd

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Kdigo Ckd Heatmap Classifier API",
    description="KDIGO 2024 eGFR/ACR risk classification and optional unvalidated audit demonstration",
    version="3.1.0",
)

MAX_QUERY_LENGTH = 1000


class ClassificationRequest(BaseModel):
    egfr: float = Field(..., ge=0, allow_inf_nan=False, description="eGFR in mL/min/1.73 m²")
    acr_mg_g: float = Field(..., ge=0, allow_inf_nan=False, description="Urine albumin-to-creatinine ratio in mg/g")


class ChatRequest(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_LENGTH, description="Supervisory query string")


@app.exception_handler(SecurityException)
async def security_exception_handler(request: Request, exc: SecurityException):
    return JSONResponse(status_code=400, content={"error": "Security violation", "detail": str(exc)})


@app.post("/api/classify")
def api_classify(payload: ClassificationRequest):
    """KDIGO 2024 risk category; never an automated CKD diagnosis."""
    return classify_ckd(payload.egfr, payload.acr_mg_g)


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "kdigo-ckd-heatmap-classifier", "domain": "nephrology", "standard": "KDIGO 2024", "version": "3.1.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "RUNNING"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    if len(req.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    ans = supervisor.query_supervisory_chat(req.query)
    return {"response": ans}


@app.get("/api/audit/logs")
def api_audit_logs():
    trail = AuditLogger.get_trail()
    return {"audit_trail": trail, "verified": bool(trail) and AuditLogger.verify_integrity(), "durability": "process-local"}
