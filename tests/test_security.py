"""Regression tests for path validation, input validation and HMAC integrity."""
import os
import pytest
from agents.base import PHIGuard, AuditTrail, SecurityException, AuditLogger
from kdigo_heatmap import classify_ckd, process_batch, _safe_path


@pytest.mark.parametrize("path", ["../etc/passwd", "data/../../secret", r"C:\\data\\..\\secret"])
def test_path_traversal_rejected(path):
    with pytest.raises(ValueError, match="traversal"):
        _safe_path(path)


def test_valid_absolute_path(tmp_path):
    assert os.path.isabs(_safe_path(str(tmp_path / "data.csv")))


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), "abc", None, ""])
def test_invalid_egfr_rejected(bad):
    with pytest.raises(ValueError):
        classify_ckd(bad, 30)


@pytest.mark.parametrize("bad", [-1, float("nan"), float("-inf"), "abc", None, ""])
def test_invalid_acr_rejected(bad):
    with pytest.raises(ValueError):
        classify_ckd(45, bad)


@pytest.mark.parametrize("identifier", ["SSN: 123-45-6789", "MRN-12345678", "555-123-4567", "patient@hospital.org"])
def test_identifier_guard(identifier):
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi(identifier)


def test_identifier_redaction():
    assert "MRN-12345678" not in PHIGuard.redact_phi("MRN-12345678")


def test_audit_requires_secret(monkeypatch):
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    with pytest.raises(SecurityException, match="AUDIT_SECRET_KEY"):
        AuditTrail()
    monkeypatch.setenv("AUDIT_SECRET_KEY", "short")
    with pytest.raises(SecurityException, match="at least 16"):
        AuditTrail()


def test_audit_hmac_verification_detects_modified_fields():
    trail = AuditTrail(secret_key="unique-integration-test-key")
    first = trail.log("system", "supervisor", "TEST", {"item": 1})
    trail.log("system", "supervisor", "TEST", {"item": 2})
    assert len(first["current_hash"]) == 64
    assert trail.verify_integrity()
    exported = trail.get_trail()
    exported[0]["actor"] = "modified outside"
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "modified inside"
    assert not trail.verify_integrity()


def test_batch_empty_csv(tmp_path):
    source, target = tmp_path / "in.csv", tmp_path / "out.csv"
    source.write_text("egfr,acr_mg_g\n")
    process_batch(str(source), str(target))
    assert "stage,risk_category,error" in target.read_text()


def test_batch_rejects_bad_headers(tmp_path):
    source, target = tmp_path / "in.csv", tmp_path / "out.csv"
    source.write_text("v1,v2\n12,3\n")
    with pytest.raises(ValueError, match="headers"):
        process_batch(str(source), str(target))


def test_batch_rejects_same_file(tmp_path):
    file = tmp_path / "data.csv"
    file.write_text("egfr,acr_mg_g\n52,125\n")
    with pytest.raises(ValueError, match="differ"):
        process_batch(str(file), str(file))
