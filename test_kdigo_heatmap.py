import csv
from kdigo_heatmap import calculate_metrics, process_batch


def test_kdigo_heatmap_single():
    result = calculate_metrics(egfr=52.0, acr_mg_g=125.0)
    assert result["stage"] == "G3aA2"
    assert result["risk_category"] == "high"
    assert result["ckd_confirmed"] is None


def test_kdigo_heatmap_batch(tmp_path):
    source, target = tmp_path / "in.csv", tmp_path / "out.csv"
    source.write_text("patient_id,egfr,acr_mg_g\nP001,52,125\nP002,90,0\nP003,error,30\n")
    process_batch(str(source), str(target))
    with target.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["stage"] for row in rows] == ["G3aA2", "G1A1", ""]
    assert rows[2]["error"]
    assert rows[0]["patient_id"] == "P001"
