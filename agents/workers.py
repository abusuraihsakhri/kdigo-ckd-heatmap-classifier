"""Rule-based KDIGO 2024 risk and manual workflow alerts.

These workers are deterministic and do not infer clinical emergencies.
"""
import uuid
from typing import List
from kdigo_heatmap import classify_ckd
from .models import SystemTaskPayload, AgentAlert, UrgencyLevel


class InvariantQCWorker:
    """Identify high/very-high KDIGO heatmap categories."""

    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        result = classify_ckd(payload.primary_metric, payload.secondary_metric)
        if result["risk_category"] not in ("high", "very high"):
            return []
        return [AgentAlert(
            alert_id=f"KDIGO-{uuid.uuid4().hex[:6]}",
            origin_worker="InvariantQCWorker",
            urgency=UrgencyLevel.ELEVATED,
            summary=f"KDIGO {result['stage']}: {result['risk_category']} risk category",
            technical_details="Classification is based on eGFR and urine ACR only. "
                              "CKD requires chronicity or other qualifying evidence.",
            actionable_remediation="Review results in clinical context; confirm chronicity "
                                   "and follow applicable KDIGO recommendations.",
            standard_reference="KDIGO 2024 CKD Guideline",
        )]


class SafetyEscalationWorker:
    """Record explicit external critical flags; never derive urgency from the ACR."""

    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        if not payload.is_critical_flag:
            return []
        return [AgentAlert(
            alert_id=f"FLAG-{uuid.uuid4().hex[:6]}",
            origin_worker="SafetyEscalationWorker",
            urgency=UrgencyLevel.CRITICAL_STAT,
            summary="Externally supplied critical flag",
            technical_details="This flag was entered by the caller; it was not derived "
                              "from the KDIGO risk matrix.",
            actionable_remediation="Review the flag and assess the individual case.",
            standard_reference="Caller-defined workflow flag",
        )]


class ProtocolConformanceWorker:
    """Highlight caller-provided discordance markers for human review."""

    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        descriptor = payload.status_descriptor.upper()
        if not any(word in descriptor for word in ("DISCORDANT", "ANOMALY", "VIOLATION", "FAIL", "REJECT")):
            return []
        return [AgentAlert(
            alert_id=f"REVIEW-{uuid.uuid4().hex[:6]}",
            origin_worker="ProtocolConformanceWorker",
            urgency=UrgencyLevel.ELEVATED,
            summary="Caller-marked data discordance",
            technical_details="The supplied status descriptor requested review.",
            actionable_remediation="Review the source data before interpretation.",
            standard_reference="Caller-defined quality-control workflow",
        )]
