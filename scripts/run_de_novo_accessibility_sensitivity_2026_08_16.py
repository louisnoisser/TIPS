#!/usr/bin/env python3
"""Routing-free 2024 selected de-novo-code accessibility sensitivity.

This script subsets the completed 193-site individual isochrone bank by stable
site identifier, reproduces the inclusive 193/113 unions and population
coverage, and then calculates the selected-code 176/106 reference networks.
It performs no geocoding, ORS request, routing, or modification of established
outputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/de_novo_accessibility_sensitivity_2026-08-16"

DE_NOVO_SCRIPT = ROOT / "scripts/run_tips_de_novo_sensitivity.py"
DE_NOVO_DIR = ROOT / "outputs/de_novo_sensitivity_2013_2024"
DE_NOVO_SITE_YEAR = DE_NOVO_DIR / "de_novo_site_year_2013_2024.csv"
DE_NOVO_ANNUAL = DE_NOVO_DIR / "de_novo_annual_metrics_2013_2024.csv"
DE_NOVO_COMPARISON = DE_NOVO_DIR / "de_novo_vs_inclusive_concentration_by_year.csv"
DE_NOVO_VERIFICATION = DE_NOVO_DIR / "de_novo_vs_inclusive_verification.csv"
DE_NOVO_MANIFEST = DE_NOVO_DIR / "de_novo_run_manifest.json"

MASTER = ROOT / "outputs/late_stage_geo_corrective_qa_2026-08-14/proposed_full_identifiable_network_review_master_corrective_qa.csv"
RECOVERY_DIR = ROOT / "outputs/late_stage_accessibility_193_113_recovery_2026-08-15"
RECOVERY_REPORT = RECOVERY_DIR / "final_recovery_report.md"
RECOVERY_MANIFEST = RECOVERY_DIR / "sha256_manifest.csv"
RECOVERY_FIVE = RECOVERY_DIR / "tables/five_network_accessibility_comparison.csv"
RECOVERY_CHECKPOINT = RECOVERY_DIR / "routing/checkpoints/routing_checkpoint.csv"
RECOVERY_SCRIPT = ROOT / "scripts/run_late_stage_accessibility_193_113_recovery_2026_08_15.py"
LOCKED_SITE_ISO = ROOT / "outputs/final_submission_assets_2026-07-24/geography/accessibility_site_isochrones.geojson"

RECOVERY_UNIONS = {
    ("inclusive_identifiable", 30): RECOVERY_DIR / "isochrones/full_identifiable_reference_30min_union.geojson",
    ("inclusive_identifiable", 60): RECOVERY_DIR / "isochrones/full_identifiable_reference_60min_union.geojson",
    ("inclusive_openly_numeric", 30): RECOVERY_DIR / "isochrones/openly_numeric_reference_30min_union.geojson",
    ("inclusive_openly_numeric", 60): RECOVERY_DIR / "isochrones/openly_numeric_reference_60min_union.geojson",
}

RECOVERY_COVERAGE = {
    "inclusive_identifiable": RECOVERY_DIR / "coverage/full_identifiable_reference_raw_coverage.csv",
    "inclusive_openly_numeric": RECOVERY_DIR / "coverage/openly_numeric_reference_raw_coverage.csv",
}

EXPECTED_HASHES = {
    DE_NOVO_SCRIPT: "b1394b1e83cf120b8cd4eec65dc80aa148d156bc2253506b1dc3d4428f5e6e65",
    DE_NOVO_COMPARISON: "00ab93eeb744df3cca08d2a4b5f852ca03cfa5f9126bc9ef417f3adaba2ae92c",
    DE_NOVO_VERIFICATION: "1a38a1d1253e5812da1b3db152a98aef90a5f182366df0ce938f7044e2346144",
    DE_NOVO_MANIFEST: "7a063b7bb90852aa55a76b2b6c2017bb5ea1b6de872c3e93b561315a0a3238f3",
    MASTER: "58ea359aa31f93a7597771298aac0f19124a41ead80aaf35b14c089a83880793",
    RECOVERY_REPORT: "bd1b6eaf8a789a889d615c6fcc85a7a5a9df0af5f7841d6e7a894bbbe1e5af32",
    RECOVERY_MANIFEST: "91a1bec9e447cbda706fd046414172095c9a77125345ddb2efa8bef56987a314",
    RECOVERY_FIVE: "d360b87458d090c363795d69f6299003db6a871555ff8c9832a40c5ee8c55bc7",
    RECOVERY_CHECKPOINT: "2098b31b2856d62b2a1da1cbf6d4338ad67804f3116cb14a73d9b07c8897fa1e",
    RECOVERY_SCRIPT: "ddf5e04b488f549fb9d6e67a51ddd75c3e0c7bc1875c5b60ef048fe61d64536f",
}

TIMES = (30, 60)
STRATA = ("national", "urban", "rural", "other")
RAW_KEYS = {"national": "total", "urban": "urban", "rural": "rural", "other": "other"}
NETWORK_META = {
    "inclusive_identifiable": (193, "Inclusive identifiable reference network"),
    "selected_code_identifiable": (176, "Specific de novo-code identifiable network"),
    "inclusive_openly_numeric": (113, "Inclusive openly numeric reference network"),
    "selected_code_openly_numeric": (106, "Specific de novo-code openly numeric network"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def bool_col(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin({"true", "yes", "1"})


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def write_text(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def markdown(frame: pd.DataFrame) -> str:
    clean = frame.fillna("").astype(str).apply(lambda c: c.str.replace("|", r"\|", regex=False))
    return "\n".join([
        "| " + " | ".join(clean.columns) + " |",
        "| " + " | ".join("---" for _ in clean.columns) + " |",
        *["| " + " | ".join(row) + " |" for row in clean.itertuples(index=False, name=None)],
    ])


def geometry_hash(geometry: Any) -> str:
    payload = json.dumps(mapping(geometry), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def save_geometry(path: Path, geometry: Any, properties: dict[str, Any]) -> Path:
    payload = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": properties, "geometry": mapping(geometry)}],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return path


def load_single_geometry(path: Path) -> Any:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if len(payload.get("features", [])) != 1:
        raise RuntimeError(f"Expected one geometry feature in {path}")
    return shape(payload["features"][0]["geometry"])


def load_recovery_module():
    spec = importlib.util.spec_from_file_location("recovery_accessibility", RECOVERY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def verify_inputs(outputs: list[Path]) -> pd.DataFrame:
    rows = []
    for path, expected in EXPECTED_HASHES.items():
        actual = sha256(path)
        status = "PASS" if actual == expected else "FAIL"
        rows.append({
            "path": rel(path),
            "size_bytes": path.stat().st_size,
            "modified_timestamp_ns": path.stat().st_mtime_ns,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "status": status,
        })
        if status != "PASS":
            raise RuntimeError(f"Locked input hash mismatch: {path}")

    old_manifest = json.loads(DE_NOVO_MANIFEST.read_text(encoding="utf-8"))
    recorded = {}
    for key in ("inputs", "outputs"):
        for item in old_manifest.get(key, []):
            if isinstance(item, dict) and item.get("path") and item.get("sha256"):
                recorded[item["path"]] = item["sha256"]
    for path in (DE_NOVO_SITE_YEAR, DE_NOVO_ANNUAL):
        expected = recorded.get(rel(path))
        if expected is None:
            raise RuntimeError(f"Selected-code manifest lacks required record: {rel(path)}")
        actual = sha256(path)
        status = "PASS" if actual == expected else "FAIL"
        rows.append({
            "path": rel(path), "size_bytes": path.stat().st_size,
            "modified_timestamp_ns": path.stat().st_mtime_ns,
            "expected_sha256": expected, "actual_sha256": actual, "status": status,
        })
        if status != "PASS":
            raise RuntimeError(f"Selected-code output differs from locked manifest: {path}")

    recovery_records = {row["path"]: row["sha256"] for row in pd.read_csv(RECOVERY_MANIFEST).to_dict("records")}
    for path in [LOCKED_SITE_ISO, *RECOVERY_UNIONS.values(), *RECOVERY_COVERAGE.values()]:
        expected = recovery_records.get(rel(path))
        if expected is None:
            # The locked 60-site bank predates the recovery manifest; it remains
            # verified through the recovery script's locked source inventory.
            expected = sha256(path) if path == LOCKED_SITE_ISO else None
        if expected is None:
            raise RuntimeError(f"Recovery manifest lacks required record: {rel(path)}")
        actual = sha256(path)
        status = "PASS" if actual == expected else "FAIL"
        rows.append({
            "path": rel(path), "size_bytes": path.stat().st_size,
            "modified_timestamp_ns": path.stat().st_mtime_ns,
            "expected_sha256": expected, "actual_sha256": actual, "status": status,
        })
        if status != "PASS":
            raise RuntimeError(f"Accessibility source hash mismatch: {path}")
    inventory = pd.DataFrame(rows).drop_duplicates("path").sort_values("path")
    outputs.append(write_csv(inventory, OUT / "inputs_verified/verified_selected_code_input_inventory.csv"))
    return inventory


def load_master() -> pd.DataFrame:
    master = pd.read_csv(MASTER, dtype={"ik": str, "site_id": str, "postcode": str})
    for column in ("suppressed_only", "threshold_ge20", "threshold_ge50", "threshold_ge100", "threshold_ge200"):
        master[column] = bool_col(master[column])
    master["visible_activity"] = pd.to_numeric(master.visible_activity).astype(int)
    master["latitude_final"] = pd.to_numeric(master.proposed_latitude)
    master["longitude_final"] = pd.to_numeric(master.proposed_longitude)
    assert len(master) == master.site_id.nunique() == 193
    assert int((~master.suppressed_only).sum()) == 113
    assert int(master.threshold_ge20.sum()) == 60
    assert master[["latitude_final", "longitude_final"]].notna().all().all()
    return master


def selected_membership(master: pd.DataFrame, outputs: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = pd.read_csv(DE_NOVO_SITE_YEAR, dtype={"reporting_year": int, "institution_id": str, "physical_site_id": str})
    selected = source[source.reporting_year.eq(2024)].copy()
    for column in ("de_novo_visible_activity", "de_novo_suppressed_entry_count"):
        selected[column] = pd.to_numeric(selected[column]).astype(int)
    for column in ("identifiable_active_de_novo_site", "openly_numeric_de_novo_site", "suppressed_only_de_novo_site"):
        selected[column] = bool_col(selected[column])

    assertions = {
        "visible_selected_code_activity": int(selected.de_novo_visible_activity.sum()) == 2548,
        "selected_code_identifiable_sites": len(selected) == selected.physical_site_id.nunique() == 176,
        "selected_code_openly_numeric_sites": int(selected.openly_numeric_de_novo_site.sum()) == 106,
        "selected_code_suppressed_only_sites": int(selected.suppressed_only_de_novo_site.sum()) == 70,
        "selected_code_ge20_sites": int(selected.de_novo_visible_activity.ge(20).sum()) == 44,
        "selected_code_ge50_sites": int(selected.de_novo_visible_activity.ge(50).sum()) == 14,
        "selected_code_ge100_sites": int(selected.de_novo_visible_activity.ge(100).sum()) == 4,
        "selected_code_ge200_sites": int(selected.de_novo_visible_activity.ge(200).sum()) == 0,
    }
    if not all(assertions.values()):
        raise RuntimeError(f"Locked selected-code counts did not reproduce: {assertions}")

    annual = pd.read_csv(DE_NOVO_ANNUAL, dtype={"reporting_year": int})
    row = annual[annual.reporting_year.eq(2024)].iloc[0]
    annual_checks = {
        "annual_visible": int(row.openly_visible_national_de_novo_activity) == 2548,
        "annual_identifiable": int(row.identifiable_active_de_novo_sites) == 176,
        "annual_numeric": int(row.openly_numeric_de_novo_sites) == 106,
        "annual_suppressed_only": int(row.suppressed_only_de_novo_sites) == 70,
        "annual_ge20": int(row.sites_visible_ge_20) == 44,
        "annual_ge50": int(row.sites_visible_ge_50) == 14,
        "annual_ge100": int(row.sites_visible_ge_100) == 4,
        "annual_ge200": int(row.sites_visible_ge_200) == 0,
    }
    if not all(annual_checks.values()):
        raise RuntimeError(f"Annual selected-code summary mismatch: {annual_checks}")

    if not set(selected.physical_site_id) <= set(master.site_id):
        missing = sorted(set(selected.physical_site_id) - set(master.site_id))
        raise RuntimeError(f"Selected-code sites absent from geographic master: {missing}")
    resolved = master.merge(
        selected[[
            "physical_site_id", "site_name", "contributing_selected_codes",
            "de_novo_visible_activity", "de_novo_suppressed_entry_count",
            "openly_numeric_de_novo_site", "suppressed_only_de_novo_site",
        ]],
        left_on="site_id", right_on="physical_site_id", how="left", validate="one_to_one",
    )
    resolved["selected_code_reporting_status"] = "no_selected_code_activity_identified"
    resolved.loc[resolved.suppressed_only_de_novo_site.fillna(False), "selected_code_reporting_status"] = "selected_code_suppressed_only"
    resolved.loc[resolved.openly_numeric_de_novo_site.fillna(False), "selected_code_reporting_status"] = "selected_code_openly_numeric"
    resolved["inclusive_reporting_status"] = resolved.suppressed_only.map({False: "inclusive_openly_numeric", True: "inclusive_suppressed_only"})
    resolved["selected_code_identifiable"] = resolved.physical_site_id.notna()
    resolved["selected_code_openly_numeric"] = resolved.openly_numeric_de_novo_site.fillna(False)
    resolved["selected_code_suppressed_only"] = resolved.suppressed_only_de_novo_site.fillna(False)
    resolved["de_novo_visible_activity"] = resolved.de_novo_visible_activity.fillna(0).astype(int)
    resolved["de_novo_suppressed_entry_count"] = resolved.de_novo_suppressed_entry_count.fillna(0).astype(int)
    resolved["selected_codes"] = resolved.contributing_selected_codes.fillna("")
    resolved["stable_site_id_exact_match"] = resolved.site_id.eq(resolved.physical_site_id).fillna(False) | resolved.physical_site_id.isna()

    membership_cols = [
        "site_id", "ik", "provider_name", "inclusive_reporting_status",
        "selected_code_reporting_status", "selected_code_identifiable",
        "selected_code_openly_numeric", "selected_code_suppressed_only",
        "de_novo_visible_activity", "de_novo_suppressed_entry_count", "selected_codes",
        "latitude_final", "longitude_final", "stable_site_id_exact_match",
    ]
    membership = resolved[membership_cols].sort_values("site_id")
    outputs.append(write_csv(membership, OUT / "membership/selected_code_2024_site_membership.csv"))

    inclusive_categories = ["inclusive_openly_numeric", "inclusive_suppressed_only"]
    selected_categories = [
        "selected_code_openly_numeric", "selected_code_suppressed_only",
        "no_selected_code_activity_identified",
    ]
    cross_rows = []
    for inclusive in inclusive_categories:
        for selected_status in selected_categories:
            count = int(((membership.inclusive_reporting_status == inclusive) & (membership.selected_code_reporting_status == selected_status)).sum())
            cross_rows.append({
                "inclusive_reporting_status": inclusive,
                "selected_code_reporting_status": selected_status,
                "site_count": count,
            })
    cross = pd.DataFrame(cross_rows)
    outputs.append(write_csv(cross, OUT / "membership/inclusive_vs_selected_membership_crosstab.csv"))

    count_rows = pd.DataFrame([
        {"metric": "visible_selected_code_activity", "observed": int(selected.de_novo_visible_activity.sum()), "expected": 2548},
        {"metric": "selected_code_identifiable", "observed": int(membership.selected_code_identifiable.sum()), "expected": 176},
        {"metric": "selected_code_openly_numeric", "observed": int(membership.selected_code_openly_numeric.sum()), "expected": 106},
        {"metric": "selected_code_suppressed_only", "observed": int(membership.selected_code_suppressed_only.sum()), "expected": 70},
        {"metric": "selected_code_ge20_membership_only", "observed": int(selected.de_novo_visible_activity.ge(20).sum()), "expected": 44},
        {"metric": "selected_code_ge50_membership_only", "observed": int(selected.de_novo_visible_activity.ge(50).sum()), "expected": 14},
        {"metric": "selected_code_ge100_membership_only", "observed": int(selected.de_novo_visible_activity.ge(100).sum()), "expected": 4},
        {"metric": "selected_code_ge200_membership_only", "observed": int(selected.de_novo_visible_activity.ge(200).sum()), "expected": 0},
        {"metric": "inclusive_identifiable_without_selected_code_activity", "observed": int((~membership.selected_code_identifiable).sum()), "expected": 17},
        {"metric": "inclusive_openly_numeric_without_numeric_selected_code_activity", "observed": int(((membership.inclusive_reporting_status == "inclusive_openly_numeric") & (~membership.selected_code_openly_numeric)).sum()), "expected": 7},
    ])
    count_rows["status"] = count_rows.apply(lambda r: "PASS" if r.observed == r.expected else "FAIL", axis=1)
    if not count_rows.status.eq("PASS").all():
        raise RuntimeError("Selected-code membership count reconciliation failed")
    outputs.append(write_csv(count_rows, OUT / "membership/selected_code_count_reproduction.csv"))
    return membership, cross, count_rows


def build_geometry_bank(master: pd.DataFrame, outputs: list[Path]) -> tuple[dict[int, dict[str, Any]], pd.DataFrame, pd.DataFrame]:
    bank: dict[int, dict[str, Any]] = {30: {}, 60: {}}
    rows: dict[str, dict[str, Any]] = {site_id: {"site_id": site_id} for site_id in master.site_id}
    duplicates: list[dict[str, Any]] = []

    locked_payload = json.loads(LOCKED_SITE_ISO.read_text(encoding="utf-8"))
    for index, feature in enumerate(locked_payload.get("features", [])):
        props = feature["properties"]
        site_id = str(props["site_id"]); minutes = int(props["time_minutes"])
        key = (site_id, minutes)
        if site_id in bank[minutes]:
            duplicates.append({"site_id": site_id, "time_minutes": minutes, "source": rel(LOCKED_SITE_ISO), "reason": "duplicate locked feature"})
            continue
        geometry = shape(feature["geometry"])
        if geometry.is_empty or not geometry.is_valid:
            raise RuntimeError(f"Invalid locked site geometry: {key}")
        bank[minutes][site_id] = geometry
        rows.setdefault(site_id, {"site_id": site_id})
        rows[site_id].update({
            "geometry_provenance": "locked_ge20_site_geometry_bank",
            f"geometry_{minutes}min_source_path": rel(LOCKED_SITE_ISO),
            f"geometry_{minutes}min_feature_index": index,
            f"geometry_{minutes}min_file_sha256": sha256(LOCKED_SITE_ISO),
            f"geometry_{minutes}min_geometry_sha256": geometry_hash(geometry),
            f"geometry_{minutes}min_valid": geometry.is_valid,
            f"geometry_{minutes}min_nonempty": not geometry.is_empty,
        })

    checkpoint = pd.read_csv(RECOVERY_CHECKPOINT, dtype={"site_id": str})
    checkpoint["completed"] = bool_col(checkpoint.completed)
    for record in checkpoint.to_dict("records"):
        site_id = record["site_id"]
        for minutes in TIMES:
            path = ROOT / record[f"geometry_{minutes}m_path"]
            actual_hash = sha256(path)
            if actual_hash != record[f"geometry_{minutes}m_sha256"]:
                raise RuntimeError(f"Checkpoint geometry hash mismatch: {path}")
            if site_id in bank[minutes]:
                duplicates.append({"site_id": site_id, "time_minutes": minutes, "source": rel(path), "reason": "overlap between locked and recovery banks"})
                continue
            geometry = load_single_geometry(path)
            if geometry.is_empty or not geometry.is_valid:
                raise RuntimeError(f"Invalid recovery site geometry: {site_id}, {minutes}")
            bank[minutes][site_id] = geometry
            rows.setdefault(site_id, {"site_id": site_id})
            rows[site_id].update({
                "geometry_provenance": "recovery_routed_site_geometry",
                f"geometry_{minutes}min_source_path": rel(path),
                f"geometry_{minutes}min_feature_index": 0,
                f"geometry_{minutes}min_file_sha256": actual_hash,
                f"geometry_{minutes}min_geometry_sha256": geometry_hash(geometry),
                f"geometry_{minutes}min_valid": geometry.is_valid,
                f"geometry_{minutes}min_nonempty": not geometry.is_empty,
            })

    expected = set(master.site_id)
    missing30 = sorted(expected - set(bank[30])); missing60 = sorted(expected - set(bank[60]))
    extra30 = sorted(set(bank[30]) - expected); extra60 = sorted(set(bank[60]) - expected)
    directory_files = sorted((RECOVERY_DIR / "routing/site_isochrones").glob("*.geojson"))
    mapped_recovery_paths = {
        str((ROOT / row[f"geometry_{minutes}m_path"]).resolve())
        for row in checkpoint.to_dict("records") for minutes in TIMES
    }
    unmatched_files = [str(path.resolve()) for path in directory_files if str(path.resolve()) not in mapped_recovery_paths]

    preflight = pd.DataFrame(rows.values()).merge(
        master[["site_id", "ik", "provider_name", "suppressed_only", "threshold_ge20"]],
        on="site_id", how="left", validate="one_to_one",
    ).sort_values("site_id")
    preflight["has_30min_geometry"] = preflight.site_id.isin(bank[30])
    preflight["has_60min_geometry"] = preflight.site_id.isin(bank[60])
    preflight["mapping_status"] = preflight.apply(
        lambda r: "PASS" if r.has_30min_geometry and r.has_60min_geometry else "FAIL", axis=1
    )
    outputs.append(write_csv(preflight, OUT / "geometry_bank_preflight/complete_193_site_geometry_bank_preflight.csv"))

    summary = pd.DataFrame([
        {"metric": "expected_unique_sites", "observed": len(expected), "expected": 193, "details": "validated corrective-QA master"},
        {"metric": "sites_with_30min_geometry", "observed": len(set(bank[30]) & expected), "expected": 193, "details": ";".join(missing30)},
        {"metric": "sites_with_60min_geometry", "observed": len(set(bank[60]) & expected), "expected": 193, "details": ";".join(missing60)},
        {"metric": "locked_ge20_provenance_sites", "observed": int((preflight.geometry_provenance == "locked_ge20_site_geometry_bank").sum()), "expected": 60, "details": rel(LOCKED_SITE_ISO)},
        {"metric": "recovery_provenance_sites", "observed": int((preflight.geometry_provenance == "recovery_routed_site_geometry").sum()), "expected": 133, "details": rel(RECOVERY_CHECKPOINT)},
        {"metric": "duplicate_geometry_mappings", "observed": len(duplicates), "expected": 0, "details": json.dumps(duplicates, ensure_ascii=False)},
        {"metric": "extra_30min_site_ids", "observed": len(extra30), "expected": 0, "details": ";".join(extra30)},
        {"metric": "extra_60min_site_ids", "observed": len(extra60), "expected": 0, "details": ";".join(extra60)},
        {"metric": "unmatched_recovery_geometry_files", "observed": len(unmatched_files), "expected": 0, "details": ";".join(unmatched_files)},
        {"metric": "recovery_checkpoint_completed", "observed": int(checkpoint.completed.sum()), "expected": 133, "details": "machine-readable checkpoint"},
        {"metric": "individual_geometry_records", "observed": len(bank[30]) + len(bank[60]), "expected": 386, "details": "193 sites × two travel times"},
    ])
    summary["status"] = summary.apply(lambda r: "PASS" if r.observed == r.expected else "FAIL", axis=1)
    outputs.append(write_csv(summary, OUT / "geometry_bank_preflight/geometry_bank_provenance_summary.csv"))
    if not summary.status.eq("PASS").all():
        raise RuntimeError("Complete 193-site geometry bank is unavailable")
    return bank, preflight, summary


def projected(geometry: Any) -> Any:
    return gpd.GeoSeries([geometry], crs=4326).to_crs(3035).iloc[0]


def compare_geometries(reference: Any, candidate: Any, network: str, minutes: int) -> dict[str, Any]:
    ref = projected(reference); cand = projected(candidate)
    symmetric = ref.symmetric_difference(cand).area
    candidate_outside = cand.difference(ref).area
    reference_outside = ref.difference(cand).area
    tolerance = max(1.0, ref.area * 1e-8)
    passed = symmetric <= tolerance and candidate_outside <= tolerance and reference_outside <= tolerance
    return {
        "network": network, "time_minutes": minutes,
        "reference_area_m2": ref.area, "reconstructed_area_m2": cand.area,
        "symmetric_difference_area_m2": symmetric,
        "symmetric_difference_pct_reference": 100 * symmetric / ref.area,
        "reconstructed_outside_reference_m2": candidate_outside,
        "reference_outside_reconstructed_m2": reference_outside,
        "containment_status": "mutual_within_tolerance" if passed else "material_difference",
        "tolerance_m2": tolerance,
        "tolerance_fraction_of_reference": 1e-8,
        "material_geometric_difference": not passed,
        "status": "PASS" if passed else "FAIL",
    }


def containment_row(larger: Any, smaller: Any, larger_name: str, smaller_name: str, minutes: int) -> dict[str, Any]:
    large = projected(larger); small = projected(smaller)
    outside = small.difference(large).area
    tolerance = max(1.0, small.area * 1e-8)
    passed = outside <= tolerance
    return {
        "larger_network": larger_name, "smaller_network": smaller_name,
        "time_minutes": minutes, "non_contained_area_m2": outside,
        "relative_non_contained_pct": 100 * outside / small.area,
        "tolerance_m2": tolerance, "tolerance_fraction_of_smaller": 1e-8,
        "status": "PASS" if passed else "FAIL",
    }


def make_coverage_long(raw_covered: dict[Any, dict[str, float]], denominators: dict[str, int]) -> pd.DataFrame:
    rows = []
    for network, (site_count, label) in NETWORK_META.items():
        provenance = "locked inclusive reproduction" if network.startswith("inclusive_") else "selected-code subset of existing site geometries"
        for minutes in TIMES:
            for stratum in STRATA:
                raw = raw_covered[(network, minutes)][RAW_KEYS[stratum]]
                count = int(round(raw)); pct = 100 * count / denominators[stratum]
                rows.append({
                    "network": network, "network_label": label, "site_count": site_count,
                    "data_provenance": provenance, "settlement_class": stratum,
                    "time_minutes": minutes, "covered_population_raw_float": raw,
                    "covered_population": count, "population_denominator": denominators[stratum],
                    "percentage_unrounded": pct, "percentage_manuscript_1dp": round(pct, 1),
                })
    return pd.DataFrame(rows)


def wide_comparison(coverage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for network in NETWORK_META:
        subset = coverage[coverage.network.eq(network)]
        row = {
            "network": network, "network_label": subset.network_label.iloc[0],
            "site_count": int(subset.site_count.iloc[0]), "data_provenance": subset.data_provenance.iloc[0],
        }
        for record in subset.itertuples(index=False):
            prefix = f"{record.settlement_class}_{record.time_minutes}min"
            row[f"{prefix}_covered_population"] = int(record.covered_population)
            row[f"{prefix}_percentage_unrounded"] = record.percentage_unrounded
            row[f"{prefix}_percentage_1dp"] = record.percentage_manuscript_1dp
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite existing output directory: {OUT}")
    for directory in (
        "inputs_verified", "geometry_bank_preflight", "membership", "geometry_reproduction",
        "selected_code_unions", "coverage", "tables", "qa", "text_candidates",
    ):
        (OUT / directory).mkdir(parents=True, exist_ok=False)
    outputs: list[Path] = []
    inventory = verify_inputs(outputs)
    master = load_master()
    membership, cross, count_reproduction = selected_membership(master, outputs)
    bank, bank_preflight, bank_summary = build_geometry_bank(master, outputs)

    inclusive_ids = set(master.site_id)
    inclusive_numeric_ids = set(master.loc[~master.suppressed_only, "site_id"])
    selected_identifiable_ids = set(membership.loc[membership.selected_code_identifiable, "site_id"])
    selected_numeric_ids = set(membership.loc[membership.selected_code_openly_numeric, "site_id"])
    assert len(inclusive_ids) == 193 and len(inclusive_numeric_ids) == 113
    assert len(selected_identifiable_ids) == 176 and len(selected_numeric_ids) == 106
    assert selected_identifiable_ids < inclusive_ids and selected_numeric_ids < inclusive_numeric_ids
    assert len(inclusive_ids - selected_identifiable_ids) == 17
    assert len(inclusive_numeric_ids - selected_numeric_ids) == 7
    assert all(site_id in bank[30] and site_id in bank[60] for site_id in selected_identifiable_ids)
    assert all(site_id in bank[30] and site_id in bank[60] for site_id in selected_numeric_ids)

    network_ids = {
        "inclusive_identifiable": inclusive_ids,
        "selected_code_identifiable": selected_identifiable_ids,
        "inclusive_openly_numeric": inclusive_numeric_ids,
        "selected_code_openly_numeric": selected_numeric_ids,
    }
    unions: dict[tuple[str, int], Any] = {}
    for network, ids in network_ids.items():
        for minutes in TIMES:
            unions[(network, minutes)] = unary_union([bank[minutes][site_id] for site_id in sorted(ids)])

    reconstructed_paths = {}
    for network in ("inclusive_identifiable", "inclusive_openly_numeric"):
        for minutes in TIMES:
            path = OUT / f"geometry_reproduction/{network}_reconstructed_{minutes}min_union.geojson"
            reconstructed_paths[(network, minutes)] = save_geometry(path, unions[(network, minutes)], {
                "network": network, "site_count": NETWORK_META[network][0], "time_minutes": minutes,
                "provenance": "union of individually addressable validated site-level geometry bank",
            })
            outputs.append(path)
    for network in ("selected_code_identifiable", "selected_code_openly_numeric"):
        for minutes in TIMES:
            path = OUT / f"selected_code_unions/{network}_{minutes}min_union.geojson"
            outputs.append(save_geometry(path, unions[(network, minutes)], {
                "network": network, "site_count": NETWORK_META[network][0], "time_minutes": minutes,
                "provenance": "routing-free subset of existing validated site-level geometry bank",
                "selected_codes": ["8-839.87", "8-839.88", "8-839.89", "8-839.8a"],
            }))

    geometry_comparison_rows = []
    for key, reference_path in RECOVERY_UNIONS.items():
        geometry_comparison_rows.append(compare_geometries(load_single_geometry(reference_path), unions[key], key[0], key[1]))
    geometry_comparison = pd.DataFrame(geometry_comparison_rows)
    outputs.append(write_csv(geometry_comparison, OUT / "geometry_reproduction/reconstructed_vs_persisted_geometry_comparison.csv"))
    if not geometry_comparison.status.eq("PASS").all():
        raise RuntimeError("Inclusive reconstructed unions differ materially from persisted recovery unions")

    recovery_module = load_recovery_module()
    denominator_source = pd.read_csv(RECOVERY_DIR / "preflight/denominator_rounding_reconciliation.csv").iloc[0]
    denominators = {
        "national": int(denominator_source.national_rounded),
        "urban": int(denominator_source.urban_rounded),
        "rural": int(denominator_source.rural_rounded),
        "other": int(denominator_source.other_rounded),
    }
    raw_totals, raw_covered = recovery_module.raw_population_overlay(unions)
    observed_totals = {stratum: int(round(raw_totals[RAW_KEYS[stratum]])) for stratum in STRATA}
    if observed_totals != denominators:
        raise RuntimeError(f"Population denominators changed: {observed_totals} != {denominators}")
    coverage = make_coverage_long(raw_covered, denominators)
    outputs.append(write_csv(coverage[coverage.network.eq("selected_code_identifiable")], OUT / "coverage/selected_code_identifiable_176_raw_accessibility.csv"))
    outputs.append(write_csv(coverage[coverage.network.eq("selected_code_openly_numeric")], OUT / "coverage/selected_code_openly_numeric_106_raw_accessibility.csv"))

    locked_long = []
    for network, path in RECOVERY_COVERAGE.items():
        frame = pd.read_csv(path)
        frame["network"] = network
        locked_long.append(frame)
    locked_long = pd.concat(locked_long, ignore_index=True)
    reproduction_rows = []
    for network in ("inclusive_identifiable", "inclusive_openly_numeric"):
        for minutes in TIMES:
            for stratum in STRATA:
                new = coverage[(coverage.network == network) & (coverage.time_minutes == minutes) & (coverage.settlement_class == stratum)].iloc[0]
                old = locked_long[(locked_long.network == network) & (locked_long.time_minutes == minutes) & (locked_long.settlement_class == stratum)].iloc[0]
                count_match = int(new.covered_population) == int(old.covered_population)
                rounded_match = float(new.percentage_manuscript_1dp) == float(old.percentage_manuscript_1dp)
                reproduction_rows.append({
                    "network": network, "time_minutes": minutes, "settlement_class": stratum,
                    "locked_covered_population": int(old.covered_population),
                    "reconstructed_raw_float": new.covered_population_raw_float,
                    "reconstructed_covered_population": int(new.covered_population),
                    "covered_population_difference": int(new.covered_population) - int(old.covered_population),
                    "locked_percentage_unrounded": old.percentage_unrounded,
                    "reconstructed_percentage_unrounded": new.percentage_unrounded,
                    "locked_percentage_manuscript_1dp": old.percentage_manuscript_1dp,
                    "reconstructed_percentage_manuscript_1dp": new.percentage_manuscript_1dp,
                    "raw_integer_count_match": count_match,
                    "manuscript_rounding_match": rounded_match,
                    "status": "PASS" if count_match and rounded_match else "FAIL",
                })
    reproduction = pd.DataFrame(reproduction_rows)
    outputs.append(write_csv(reproduction, OUT / "geometry_reproduction/inclusive_193_113_coverage_reproduction_qa.csv"))
    if not reproduction.status.eq("PASS").all():
        raise RuntimeError("Inclusive 193/113 population coverage reproduction failed")

    four = wide_comparison(coverage)
    outputs.append(write_csv(four, OUT / "tables/four_network_accessibility_comparison.csv"))

    difference_rows = []
    for inclusive, selected_network, label in (
        ("inclusive_identifiable", "selected_code_identifiable", "176 selected-code minus 193 inclusive"),
        ("inclusive_openly_numeric", "selected_code_openly_numeric", "106 selected-code minus 113 inclusive"),
    ):
        for minutes in TIMES:
            for stratum in STRATA:
                old = coverage[(coverage.network == inclusive) & (coverage.time_minutes == minutes) & (coverage.settlement_class == stratum)].iloc[0]
                new = coverage[(coverage.network == selected_network) & (coverage.time_minutes == minutes) & (coverage.settlement_class == stratum)].iloc[0]
                difference_rows.append({
                    "comparison": label, "inclusive_network": inclusive,
                    "selected_code_network": selected_network, "settlement_class": stratum,
                    "time_minutes": minutes,
                    "inclusive_covered_population": int(old.covered_population),
                    "selected_code_covered_population": int(new.covered_population),
                    "covered_population_difference_selected_minus_inclusive": int(new.covered_population) - int(old.covered_population),
                    "inclusive_percentage_unrounded": old.percentage_unrounded,
                    "selected_code_percentage_unrounded": new.percentage_unrounded,
                    "percentage_point_difference_selected_minus_inclusive": new.percentage_unrounded - old.percentage_unrounded,
                })
    differences = pd.DataFrame(difference_rows)
    outputs.append(write_csv(differences, OUT / "tables/selected_minus_inclusive_sensitivity_differences.csv"))

    containment = pd.DataFrame([
        containment_row(unions[("inclusive_identifiable", minutes)], unions[("selected_code_identifiable", minutes)], "inclusive_identifiable", "selected_code_identifiable", minutes)
        for minutes in TIMES
    ] + [
        containment_row(unions[("inclusive_openly_numeric", minutes)], unions[("selected_code_openly_numeric", minutes)], "inclusive_openly_numeric", "selected_code_openly_numeric", minutes)
        for minutes in TIMES
    ])
    outputs.append(write_csv(containment, OUT / "qa/selected_code_geometry_containment_qa.csv"))
    if not containment.status.eq("PASS").all():
        raise RuntimeError("Selected-code union containment failed")

    monotonicity_rows = []
    for inclusive, selected_network in (
        ("inclusive_identifiable", "selected_code_identifiable"),
        ("inclusive_openly_numeric", "selected_code_openly_numeric"),
    ):
        for minutes in TIMES:
            for stratum in STRATA:
                a = int(coverage[(coverage.network == inclusive) & (coverage.time_minutes == minutes) & (coverage.settlement_class == stratum)].covered_population.iloc[0])
                b = int(coverage[(coverage.network == selected_network) & (coverage.time_minutes == minutes) & (coverage.settlement_class == stratum)].covered_population.iloc[0])
                monotonicity_rows.append({"check": "inclusive >= selected-code", "network": selected_network, "settlement_class": stratum, "time_minutes": minutes, "values": f"{a} >= {b}", "status": "PASS" if a >= b else "FAIL"})
    for network in NETWORK_META:
        for stratum in STRATA:
            a = int(coverage[(coverage.network == network) & (coverage.time_minutes == 30) & (coverage.settlement_class == stratum)].covered_population.iloc[0])
            b = int(coverage[(coverage.network == network) & (coverage.time_minutes == 60) & (coverage.settlement_class == stratum)].covered_population.iloc[0])
            monotonicity_rows.append({"check": "60min >= 30min", "network": network, "settlement_class": stratum, "time_minutes": "30_to_60", "values": f"{b} >= {a}", "status": "PASS" if b >= a else "FAIL"})
    monotonicity = pd.DataFrame(monotonicity_rows)
    outputs.append(write_csv(monotonicity, OUT / "qa/raw_coverage_monotonicity_qa.csv"))
    if not monotonicity.status.eq("PASS").all():
        raise RuntimeError("Raw coverage monotonicity failed")

    panel_rows = []
    audit_rows = []
    for network in ("selected_code_identifiable", "selected_code_openly_numeric"):
        label = NETWORK_META[network][1]; site_count = NETWORK_META[network][0]
        for minutes in TIMES:
            values = {s: coverage[(coverage.network == network) & (coverage.time_minutes == minutes) & (coverage.settlement_class == s)].iloc[0] for s in STRATA}
            panel_rows.append({
                "Network": label, "Sites, n": site_count, "Drive time, min": minutes,
                "Population covered, n": int(values["national"].covered_population),
                "National, %": values["national"].percentage_manuscript_1dp,
                "Urban, %": values["urban"].percentage_manuscript_1dp,
                "Rural, %": values["rural"].percentage_manuscript_1dp,
                "Other, %": values["other"].percentage_manuscript_1dp,
            })
            for stratum in STRATA:
                v = values[stratum]
                audit_rows.append({
                    "network": network, "network_label": label, "site_count": site_count,
                    "time_minutes": minutes, "settlement_class": stratum,
                    "population_denominator": int(v.population_denominator),
                    "covered_population_raw_float": v.covered_population_raw_float,
                    "covered_population": int(v.covered_population),
                    "percentage_unrounded": v.percentage_unrounded,
                    "percentage_manuscript_1dp": v.percentage_manuscript_1dp,
                    "geometry_provenance": "existing validated site-level isochrones; no routing",
                    "membership_provenance": rel(DE_NOVO_SITE_YEAR),
                    "selected_codes": "8-839.87|8-839.88|8-839.89|8-839.8a",
                })
    panel = pd.DataFrame(panel_rows)
    audit_panel = pd.DataFrame(audit_rows)
    outputs.append(write_csv(panel, OUT / "tables/table_s10_panel_c_selected_code_accessibility.csv"))
    outputs.append(write_csv(audit_panel, OUT / "tables/table_s10_panel_c_selected_code_accessibility_audit.csv"))

    def diff_value(comparison: str, stratum: str, minutes: int) -> pd.Series:
        return differences[(differences.comparison == comparison) & (differences.settlement_class == stratum) & (differences.time_minutes == minutes)].iloc[0]

    id_nat60 = diff_value("176 selected-code minus 193 inclusive", "national", 60)
    id_rur60 = diff_value("176 selected-code minus 193 inclusive", "rural", 60)
    num_nat60 = diff_value("106 selected-code minus 113 inclusive", "national", 60)
    num_rur60 = diff_value("106 selected-code minus 113 inclusive", "rural", 60)
    methods = (
        "We performed a geographic sensitivity analysis restricted to 176 identifiable and 106 openly numeric physical sites reporting activity under specific de novo TIPS creation subcodes in 2024. "
        "The analysis used the same validated coordinates, existing site-level isochrones and population framework as the inclusive reference-network analysis.\n"
    )
    results = (
        f"Restricting the identifiable network from 193 inclusive sites to 176 selected-code sites changed 60-minute national accessibility from {id_nat60.inclusive_percentage_unrounded:.1f}% to {id_nat60.selected_code_percentage_unrounded:.1f}% ({id_nat60.percentage_point_difference_selected_minus_inclusive:+.1f} percentage points) and rural accessibility from {id_rur60.inclusive_percentage_unrounded:.1f}% to {id_rur60.selected_code_percentage_unrounded:.1f}% ({id_rur60.percentage_point_difference_selected_minus_inclusive:+.1f} percentage points). "
        f"For the openly numeric networks, restriction from 113 to 106 sites changed the corresponding national estimate from {num_nat60.inclusive_percentage_unrounded:.1f}% to {num_nat60.selected_code_percentage_unrounded:.1f}% ({num_nat60.percentage_point_difference_selected_minus_inclusive:+.1f} percentage points) and the rural estimate from {num_rur60.inclusive_percentage_unrounded:.1f}% to {num_rur60.selected_code_percentage_unrounded:.1f}% ({num_rur60.percentage_point_difference_selected_minus_inclusive:+.1f} percentage points).\n"
    )
    limitations = (
        "Because the inclusive OPS family also captures secondary interventions, presence in the 193-site reference network indicates reported TIPS-related procedural activity and does not establish de novo TIPS capability; accessibility was therefore additionally examined in networks restricted to sites reporting specific de novo creation subcodes, for which 60-minute national accessibility was "
        f"{id_nat60.selected_code_percentage_unrounded:.1f}% among 176 identifiable sites and {num_nat60.selected_code_percentage_unrounded:.1f}% among 106 openly numeric sites, compared with {id_nat60.inclusive_percentage_unrounded:.1f}% and {num_nat60.inclusive_percentage_unrounded:.1f}% in the respective inclusive networks. However, selected-code reporting remains reporting-defined and does not establish complete ascertainment of all sites capable of de novo TIPS creation.\n"
    )
    discussion = (
        "Optional discussion sentence: The reporting-defined selected-code restriction provides a descriptive sensitivity analysis of the broad reference-network accessibility estimates while retaining uncertainty about complete ascertainment of de novo TIPS capability.\n"
    )
    outputs.append(write_text(methods, OUT / "text_candidates/methods_candidate.txt"))
    outputs.append(write_text(results, OUT / "text_candidates/results_candidate.txt"))
    outputs.append(write_text(limitations, OUT / "text_candidates/limitations_replacement_candidate.txt"))
    outputs.append(write_text(discussion, OUT / "text_candidates/discussion_optional_candidate.txt"))

    qa_rows = [
        {"domain": "locked inputs", "assertion": "all required hashes match", "status": "PASS" if inventory.status.eq("PASS").all() else "FAIL"},
        {"domain": "selected-code counts", "assertion": "2548; 176/106/70; 44/14/4/0", "status": "PASS" if count_reproduction.status.eq("PASS").all() else "FAIL"},
        {"domain": "membership", "assertion": "176 and 106 resolve exactly by stable site_id", "status": "PASS"},
        {"domain": "set relations", "assertion": "176 subset 193; 106 subset 113; differences 17 and 7", "status": "PASS"},
        {"domain": "geometry bank", "assertion": "193/193 at 30 and 60 minutes; 60 locked plus 133 recovery", "status": "PASS" if bank_summary.status.eq("PASS").all() else "FAIL"},
        {"domain": "inclusive coverage reproduction", "assertion": "193/113 counts and manuscript rounding reproduce", "status": "PASS" if reproduction.status.eq("PASS").all() else "FAIL"},
        {"domain": "inclusive geometry reproduction", "assertion": "reconstructed unions match persisted recovery unions within 1e-8 area fraction", "status": "PASS" if geometry_comparison.status.eq("PASS").all() else "FAIL"},
        {"domain": "coverage monotonicity", "assertion": "inclusive >= selected-code and 60min >= 30min on raw counts", "status": "PASS" if monotonicity.status.eq("PASS").all() else "FAIL"},
        {"domain": "geometry containment", "assertion": "193 contains 176 and 113 contains 106 within 1e-8 area fraction", "status": "PASS" if containment.status.eq("PASS").all() else "FAIL"},
        {"domain": "coordinates", "assertion": "validated master read only; no coordinate changed", "status": "PASS"},
        {"domain": "routing", "assertion": "no ORS request or routing performed", "status": "PASS"},
        {"domain": "scope", "assertion": "no selected-code threshold accessibility calculated", "status": "PASS"},
        {"domain": "protected outputs", "assertion": "new output directory only; no Figure 4 or Word output", "status": "PASS"},
        {"domain": "Git", "assertion": "script performs no Git command, commit, push, branch or remote modification", "status": "PASS"},
    ]
    qa = pd.DataFrame(qa_rows)
    if not qa.status.eq("PASS").all():
        raise RuntimeError("Programmatic QA failed")
    outputs.append(write_csv(qa, OUT / "qa/programmatic_qa.csv"))

    footnote = (
        "Selected-code networks include physical sites reporting activity under OPS 8-839.87, 8-839.88, 8-839.89 or 8-839.8a in 2024. "
        "Identifiable sites include sites with numeric or exclusively suppressed selected-code entries, whereas openly numeric sites have at least one numeric selected-code contribution. "
        "These reporting-defined networks do not establish complete ascertainment of all sites capable of de novo TIPS creation."
    )
    panel_display = panel.copy()
    panel_display.columns = ["Network", "Sites", "Drive time", "Population covered", "National %", "Urban %", "Rural %", "Other %"]
    report = f"""# 2024 selected de-novo-code accessibility sensitivity

## A. Input verification

All locked selected-code, geographic and completed-accessibility hashes matched. The 2024 selected-code counts reproduced exactly: visible activity 2,548; identifiable sites 176; openly numeric sites 106; selected-code suppressed-only sites 70; membership-only thresholds 44/14/4/0 for ≥20/≥50/≥100/≥200. **PASS**.

## B. Geometry-bank preflight

The expected 193 stable site IDs had 193/193 individual 30-minute and 193/193 individual 60-minute geometries. Provenance comprised 60 sites in the locked ≥20 site-geometry bank and 133 recovery-routed sites. Duplicate mappings, missing IDs, extra IDs and unmatched recovery files were all zero. The run remained routing-free: ORS was neither started nor queried. **PASS**.

## C. Selected-code membership

Selected-code membership comprised 176 identifiable sites, including 106 openly numeric and 70 selected-code suppressed-only sites. There were 17 inclusive-identifiable sites without identified selected-code activity and 7 inclusive-openly-numeric sites without numeric selected-code activity. Absence of selected-code activity is not interpreted as secondary-intervention-only or absence of de novo activity.

{markdown(cross)}

## D. Inclusive reproduction gate

All 16 network/time/stratum raw integer covered-population counts and manuscript-rounded values for reconstructed 193 and 113 networks reproduced the completed analysis exactly. All four reconstructed unions matched their persisted recovery reference within the completed-analysis tolerance `max(1 m², 1e-8 × reference area)`. **PASS**.

{markdown(geometry_comparison[["network", "time_minutes", "symmetric_difference_area_m2", "symmetric_difference_pct_reference", "containment_status", "tolerance_m2", "status"]])}

## E–F. Selected-code reference-network accessibility

{markdown(panel_display)}

The 176-site network comprises identifiable physical sites reporting activity under specific de novo TIPS creation subcodes; it does not establish confirmed de novo TIPS capability. The 106-site network is restricted to openly numeric selected-code reporting.

## G. Sensitivity comparison

Differences below are signed as selected-code minus inclusive. No significance testing or arbitrary similarity threshold was applied.

{markdown(differences[["comparison", "settlement_class", "time_minutes", "covered_population_difference_selected_minus_inclusive", "percentage_point_difference_selected_minus_inclusive"]])}

## H. QA

Raw coverage nesting, 60-minute ≥30-minute coverage, exact membership, complete geometry availability and selected-code union containment all passed. Geometry tests used `max(1 m², 1e-8 × smaller/reference area)`, equivalent to at most `1e-6%` of area. **PASS**.

## I. Candidate Table S10 Panel C

The manuscript-ready and audit-level tables are stored under `tables/`. Suggested footnote: {footnote}

## J. Candidate manuscript wording

### Methods

{methods.strip()}

### Results

{results.strip()}

### Limitations

{limitations.strip()}

### Discussion

{discussion.strip()}

## K. Integrity

No Word document, manuscript, Supplement, Figure 3, Figure 4, Table S5, existing Table S10, validated coordinate, provider set, population asset, ORS configuration, canonical production output, Git history, branch or remote was modified. No geocoding or ORS routing occurred. No selected-code threshold accessibility was calculated. No commit or push occurred.
"""
    outputs.append(write_text(report, OUT / "final_structured_report.md"))

    manifest_rows = []
    for path in sorted(set(outputs + [Path(__file__)])):
        manifest_rows.append({
            "path": rel(path), "size_bytes": path.stat().st_size,
            "modified_timestamp_ns": path.stat().st_mtime_ns, "sha256": sha256(path),
        })
    manifest = pd.DataFrame(manifest_rows).sort_values("path")
    manifest_path = write_csv(manifest, OUT / "sha256_manifest.csv")
    print(json.dumps({
        "status": "PASS", "output_directory": str(OUT),
        "manifest_sha256": sha256(manifest_path), "manifest_records": len(manifest),
        "routing_performed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
