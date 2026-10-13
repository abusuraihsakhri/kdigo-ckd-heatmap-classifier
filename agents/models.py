"""
Pydantic v2 schemas and data definitions for Kdigo Ckd Heatmap Classifier.
Domain: Clinical & Biomedical AI
Scope: KDIGO 2024 and caller-defined audit workflow
"""
import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class UrgencyLevel(str, Enum):
    ROUTINE = "ROUTINE"
    ELEVATED = "ELEVATED_RISK"
    CRITICAL_STAT = "CRITICAL_STAT_PANIC"


class SystemIntegrityStatus(str, Enum):
    VALIDATED = "VALIDATED_OPTIMAL"
    DISCORDANT = "DISCORDANT_ANOMALY"
    RECALIBRATION_REQUIRED = "RECALIBRATION_REQUIRED"


class SystemTaskPayload(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=120, description="Unique task / case identifier")
    target_identifier: str = Field(..., min_length=1, max_length=120, description="Entity, patient key, or genomic/cryptographic target")
    primary_metric: float = Field(..., ge=0, allow_inf_nan=False, description="eGFR in mL/min/1.73 m²")
    secondary_metric: float = Field(default=0.0, ge=0, allow_inf_nan=False, description="urine ACR in mg/g")
    status_descriptor: str = Field(default="NOMINAL", max_length=200, description="Status code or phenotype descriptor")
    is_critical_flag: bool = Field(default=False, description="Emergency escalation or high priority trigger")
    attributes: Dict[str, Any] = Field(default_factory=dict, max_length=32, description="Metadata key-value pairs")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class AgentAlert(BaseModel):
    alert_id: str
    origin_worker: str
    urgency: UrgencyLevel
    summary: str
    technical_details: str
    actionable_remediation: str
    standard_reference: str = "KDIGO 2024 CKD Guideline / caller-defined audit workflow"
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ConsensusDossier(BaseModel):
    dossier_id: str
    system_slug: str = "kdigo-ckd-heatmap-classifier"
    domain: str = "Clinical & Biomedical AI"
    task_id: str
    target_identifier: str
    overall_urgency: UrgencyLevel
    integrity_status: SystemIntegrityStatus
    total_alerts: int
    critical_alerts_count: int
    alerts: List[AgentAlert]
    standard_reference: str = "KDIGO 2024 CKD Guideline / caller-defined audit workflow"
    consensus_summary: str
    audit_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
