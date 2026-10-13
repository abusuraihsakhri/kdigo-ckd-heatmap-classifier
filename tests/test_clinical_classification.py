"""KDIGO 2024 G1–G5 × A1–A3 decision matrix and clinical boundaries."""
import itertools
import pytest
from kdigo_heatmap import classify_ckd, GFR_CATEGORIES, RISK_GRID


@pytest.mark.parametrize("egfr,gfr", [(90, "G1"), (89.999, "G2"), (60, "G2"),
  (59.999, "G3a"), (45, "G3a"), (44.999, "G3b"), (30, "G3b"),
  (29.999, "G4"), (15, "G4"), (14.999, "G5"), (0, "G5")])
def test_gfr_boundaries(egfr, gfr):
    assert classify_ckd(egfr, 0)["gfr_category"] == gfr


@pytest.mark.parametrize("acr,stage", [(0, "A1"), (29.999, "A1"), (30, "A2"),
  (300, "A3"), (299.999, "A2"), (300.001, "A3")])
def test_acr_boundaries(acr, stage):
    assert classify_ckd(90, acr)["albuminuria_category"] == stage


def test_all_18_risk_cells():
    representative_egfr = [100, 75, 52, 38, 22, 10]
    representative_acr = [10, 100, 500]
    for i, j in itertools.product(range(6), range(3)):
        output = classify_ckd(representative_egfr[i], representative_acr[j])
        assert output["gfr_category"] == GFR_CATEGORIES[i]
        assert output["albuminuria_category"] == ("A1", "A2", "A3")[j]
        assert output["risk_category"] == RISK_GRID[i][j]


def test_ckd_not_diagnosed_by_single_reading():
    output = classify_ckd(91, 5)
    assert output["risk_category"] == "low"
    assert output["ckd_confirmed"] is None
    assert "do not meet CKD criteria" in output["clinical_note"]
