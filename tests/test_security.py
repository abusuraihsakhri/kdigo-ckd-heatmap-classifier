"""
Security and edge-case tests for kdigo-ckd-heatmap-classifier.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, AuditTrail
from kdigo_heatmap import calculate_metrics, process_batch, _safe_path


class TestPathTraversalProtection:
    """Verify that path traversal attacks are blocked."""

    def test_reject_dotdot_relative(self):
        with pytest.raises(ValueError, match="traversal"):
            _safe_path("../etc/passwd")

    def test_reject_dotdot_in_middle(self):
        with pytest.raises(ValueError, match="traversal"):
            _safe_path("data/../../etc/passwd")

    def test_reject_absolute_traversal(self):
        with pytest.raises(ValueError, match="traversal"):
            _safe_path("C:\\Windows\\System32\\..\\..\\..\\secret.txt")

    def test_accept_simple_relative(self):
        result = _safe_path("data.csv")
        assert os.path.isabs(result)

    def test_accept_simple_absolute(self):
        result = _safe_path(os.path.abspath("data.csv"))
        assert os.path.isabs(result)


class TestCalculateMetricsEdgeCases:
    """Verify calculate_metrics handles edge cases."""

    def test_empty_params(self):
        result = calculate_metrics()
        assert result["score"] == 1.0
        assert result["inputs_evaluated"] == 0

    def test_single_param(self):
        result = calculate_metrics(v1=15.0)
        assert result["score"] == 15.0
        assert result["classification"] == "Moderate / Intermediate"

    def test_string_values_ignored(self):
        result = calculate_metrics(v1=10.0, name="test_patient")
        assert result["score"] == 10.0
        assert result["inputs_evaluated"] == 2

    def test_high_score_classification(self):
        result = calculate_metrics(v1=30.0, v2=20.0)
        assert result["classification"] == "High / Severe"

    def test_low_score_classification(self):
        result = calculate_metrics(v1=5.0)
        assert result["classification"] == "Low / Standard"


class TestPHIGuardEnforcement:
    """Verify PHI guard patterns are comprehensive."""

    def test_blocks_ssn(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient SSN: 123-45-6789")

    def test_blocks_mrn(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("MRN-12345678")

    def test_blocks_phone(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Contact: 555-123-4567")

    def test_blocks_email(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("patient@hospital.org")

    def test_allows_safe_text(self):
        PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")

    def test_redact_phi(self):
        result = PHIGuard.redact_phi("Patient MRN-12345678 is stable")
        assert "[REDACTED_IDENTIFIER]" in result
        assert "MRN-12345678" not in result


class TestAuditTrailSecurity:
    """Verify audit trail security requirements."""

    def test_requires_secret_key(self):
        os.environ.pop("AUDIT_SECRET_KEY", None)
        with pytest.raises(SecurityException, match="AUDIT_SECRET_KEY"):
            AuditTrail()

    def test_rejects_short_key(self):
        os.environ["AUDIT_SECRET_KEY"] = "short"
        with pytest.raises(SecurityException, match="at least 16"):
            AuditTrail()

    def test_accepts_valid_key(self):
        os.environ["AUDIT_SECRET_KEY"] = "valid-secret-key-2026"
        trail = AuditTrail()
        assert trail.secret_key == b"valid-secret-key-2026"


class TestBatchProcessingEdgeCases:
    """Verify batch processing handles edge cases."""

    def test_missing_input_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_batch(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))

    def test_empty_csv(self, tmp_path):
        csv_in = tmp_path / "empty.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text("Patient_ID,v1,v2\n", encoding="utf-8")
        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()
        content = csv_out.read_text()
        assert "score" in content
