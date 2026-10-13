"""Basic identifier screening and an in-process HMAC-SHA256 audit ledger.

Regex screening is best-effort and must not be represented as HIPAA de-identification.
The ledger is process-local and is not durable after a restart.
"""
import hashlib
import hmac
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PHI_PATTERNS = [
    re.compile(r"\bMRN[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
    re.compile(r"\b(?:John\s+Doe|Jane\s+Smith|Alice\s+Johnson)\b", re.IGNORECASE),
]


class SecurityException(Exception):
    pass


class ResourceLimitExceededException(Exception):
    pass


def assert_no_phi(value: str) -> None:
    if value:
        for pattern in PHI_PATTERNS:
            if pattern.search(str(value)):
                raise SecurityException("Potential personal identifier detected")


class PHIGuard:
    assert_no_phi = staticmethod(assert_no_phi)

    @staticmethod
    def redact_phi(value: str) -> str:
        result = str(value)
        for pattern in PHI_PATTERNS:
            result = pattern.sub("[REDACTED_IDENTIFIER]", result)
        return result


class AuditTrail:
    """Process-local HMAC chain; does not provide immutable external storage."""

    def __init__(self, secret_key: Optional[str] = None):
        key = secret_key or os.getenv("AUDIT_SECRET_KEY")
        if not key:
            raise SecurityException("AUDIT_SECRET_KEY environment variable is required")
        if len(key) < 16:
            raise SecurityException("AUDIT_SECRET_KEY must be at least 16 characters long")
        self.secret_key = key.encode("utf-8")
        self.logs: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def _signature(self, entry: Dict[str, Any]) -> str:
        fields = ("audit_id", "timestamp", "actor", "actor_tier",
                  "event_type", "payload_hash", "prev_hash")
        message = "|".join(str(entry[key]) for key in fields)
        return hmac.new(self.secret_key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, actor: str, actor_tier: str, event_type: str,
            details: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(details, sort_keys=True, allow_nan=False)
        for value in (actor, actor_tier, event_type, data):
            assert_no_phi(value)
        digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
        with self._lock:
            entry = {
                "audit_id": f"AUDIT-{time.time_ns()}-{len(self.logs)+1}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "actor_tier": actor_tier,
                "event_type": event_type,
                "payload_hash": digest,
                "prev_hash": (self.logs[-1]["current_hash"] if self.logs
                              else "GENESIS_BLOCK_0000000000000000"),
            }
            entry["current_hash"] = self._signature(entry)
            self.logs.append(entry)
            return dict(entry)

    def verify_integrity(self) -> bool:
        with self._lock:
            previous = "GENESIS_BLOCK_0000000000000000"
            for entry in self.logs:
                try:
                    if entry["prev_hash"] != previous:
                        return False
                    signature = self._signature(entry)
                    if not hmac.compare_digest(signature, entry["current_hash"]):
                        return False
                    previous = entry["current_hash"]
                except (KeyError, TypeError, ValueError):
                    return False
            return True

    def get_trail(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(entry) for entry in self.logs]


_GLOBAL_AUDIT: Optional[AuditTrail] = None
_GLOBAL_LOCK = threading.Lock()


def _audit() -> AuditTrail:
    global _GLOBAL_AUDIT
    with _GLOBAL_LOCK:
        if _GLOBAL_AUDIT is None:
            _GLOBAL_AUDIT = AuditTrail()
        return _GLOBAL_AUDIT


class AuditLogger:
    @staticmethod
    def log(actor: str, actor_tier: str, event_type: str,
            details: Dict[str, Any]) -> Dict[str, Any]:
        return _audit().log(actor, actor_tier, event_type, details)

    @staticmethod
    def get_trail() -> List[Dict[str, Any]]:
        return [] if _GLOBAL_AUDIT is None else _GLOBAL_AUDIT.get_trail()

    @staticmethod
    def verify_integrity() -> bool:
        return True if _GLOBAL_AUDIT is None else _GLOBAL_AUDIT.verify_integrity()


class ActionExecutor:
    @staticmethod
    def execute_with_audit(actor: str, actor_tier: str, action_type: str, fn, *args, **kwargs):
        res = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return res
