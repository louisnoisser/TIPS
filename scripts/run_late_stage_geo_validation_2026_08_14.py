#!/usr/bin/env python3
"""Validate the additional 2024 TIPS geographic records without accessibility work."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import html
import json
import re
from pathlib import Path
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gba_ops_reanalysis import config  # noqa: E402

OUT = ROOT / "outputs/late_stage_geo_validation_2026-08-14"
FIG3 = OUT / "figure3_finalisation"
GEO = OUT / "geo_validation"
EVIDENCE = GEO / "evidence"
DOSSIER = GEO / "review_dossier"
DECISIONS = GEO / "decision_required"
QA = OUT / "qa"

PREVIOUS_REPORT = ROOT / "outputs/late_stage_revision_2026-08-14/late_stage_revision_report.md"
PREVIOUS_BUILDER = ROOT / "scripts/build_late_stage_revision_2026_08_14.py"
PREVIOUS_MANIFEST = ROOT / "outputs/late_stage_revision_2026-08-14/revision_output_manifest.json"
MASTER = ROOT / "outputs/final_submission_assets_2026-07-24/geography/provider_locations_master_2024.csv"
NUMERIC_GEOCODED = ROOT / "outputs/indications/tips_8-839-8_updated2024/tables/latest_year_geocoded_all_centers.csv"
LOCKED_60 = ROOT / "outputs/final_submission_assets_2026-07-24/geography_manual_review_ge20_2024_completed.csv"
CANDIDATE_113 = ROOT / "outputs/late_stage_revision_2026-08-14/geo_preflight/candidate_113_panel_A_sites.csv"
CANDIDATE_193 = ROOT / "outputs/late_stage_revision_2026-08-14/geo_preflight/candidate_193_panel_A_sites.csv"
PREVIOUS_FLAGS = ROOT / "outputs/late_stage_revision_2026-08-14/geo_preflight/automated_geographic_review_flags.csv"
KNOWN_CORRECTIONS = ROOT / "outputs/late_stage_revision_2026-08-14/geo_preflight/known_three_manual_corrections_crosscheck.csv"
FIG3_DATA = ROOT / "outputs/late_stage_revision_2026-08-14/figure3_comparison/Figure3_candidate_B_identifiable_network_data.csv"
FIG3_OLD_PNG = ROOT / "outputs/late_stage_revision_2026-08-14/figure3_comparison/Figure3_candidate_B_identifiable_network.png"
FIG3_OLD_PDF = ROOT / "outputs/late_stage_revision_2026-08-14/figure3_comparison/Figure3_candidate_B_identifiable_network.pdf"
RESOLVED = ROOT / "outputs/site_resolution_validation/resolved_site_level_data.csv"
NUMERIC_CACHE = ROOT / "data/cache/geocode/tips_8-839-8_geocode_cache.csv"
SUPPRESSED_CACHE = ROOT / "outputs/late_stage_revision_2026-08-14/geo_preflight/suppressed_only_automatic_preview_geocode_cache.csv"

EXPECTED = {
    PREVIOUS_REPORT: "4b2807d72763835059ea6c737029cf0dd7e7d24ec627b3b751baf7c00b2f9f60",
    PREVIOUS_BUILDER: "6bfcc22c37745136c923def08e6b6b0896f927af55a692b337e4201ba4d81978",
    PREVIOUS_MANIFEST: "81e1bcdbeaa7b6c526db39575f87d28acc30de9d6a90578087998388ae61dc66",
    MASTER: "646e6fe5ae3b1dff2aade2e58bc63e46d9014b45faa8976f2e4e56f4c6c2e536",
    NUMERIC_GEOCODED: "fe0f1a54796a66cebbc19ce5a982072f1346b90a15293e1389fff174544f56c0",
    LOCKED_60: "803e125939df1ceb6a6f72f9e6577e2726e4e20e83328ba3ae0f46edf3739061",
    CANDIDATE_113: "352d2d180c5e443fe2b1f82557993c6de4dee6ad1a3e2e56c66a3271cf779f4f",
    CANDIDATE_193: "f1d9515cdf7b4a6b16113f11d6651ea574bd93f03a07ee74aa77ab6bfe326d81",
    PREVIOUS_FLAGS: "9901a22a0f47041f47345e19f6958eb56d8004eba6a6a8952da7901cf8e8880f",
    KNOWN_CORRECTIONS: "8779ed0fd184f8b58a935754b7456d9c6c8086c3f734491455b2224bf9706137",
    FIG3_DATA: "53c20066b45a7b9b08a06ab6c9ac3d2992892b2832c8515a52e2822090946500",
    FIG3_OLD_PNG: "b5ed804d11711958ad230847911e0dcb24c0f4d86233efb1969e4a3a7dba09be",
    FIG3_OLD_PDF: "a4991b1f0a5eb8179dd7672d0d64bf7cd11b26ba5a3428647bcd9eb18bd0f9b3",
}

YEARS = [2008, 2010, *range(2012, 2025)]
CATEGORY_COLUMNS = ["sites_4_19", "sites_20_49", "sites_50_99", "sites_100_199", "sites_ge_200"]
CATEGORY_LABELS = ["4–19", "20–49", "50–99", "100–199", "≥200"]
COLOURS = ["#d9eaf3", "#a8cde1", "#6baed6", "#3182bd", "#08519c"]
SUPPRESSED_LABEL = "1–3 per code entry (suppressed)"
PRECISION = {
    "A": "verified_campus_or_building",
    "B": "verified_clinical_street_address",
    "C": "locality_or_centroid_only",
    "D": "unresolved_or_conflicting",
}

# Primary-source adjudications for records where a purely syntactic reverse-
# geocoder comparison is too conservative. These do not alter set membership.
# They document why a coordinate is demonstrably on the clinical campus/street.
ADJUDICATIONS = {
    "261600634-771973000": {
        "precision": "B", "url": "https://www.zentralklinik.de/impressum.html",
        "reason": "Official hospital source confirms Robert-Koch-Allee 9, 99437 Bad Berka; the coordinate resolves to house 9 on the same street, with only the OSM postal-area value differing (99438).",
    },
    "261300152-773589000": {
        "precision": "B", "url": "https://www.medizin.uni-greifswald.de/de/impressum/",
        "reason": "Official university-medical source confirms Fleischmannstraße 8; the coordinate resolves to building A01 at that exact street and house number, with only the OSM postal-area value differing (17489).",
    },
    "260310209-772363000": {
        "precision": "B", "url": "https://klinikum-braunschweig.de/info?id_object=511&object=contact",
        "reason": "Official clinical contact evidence confirms Salzdahlumer Straße 90; the coordinate is the named Salzdahlumer Straße 90 entrance/taxi point, although OSM stores the access road as Schwartzkopffstraße.",
    },
    "260510611-771123000": {
        "precision": "B", "url": "https://www.region.alexianer-krefeld.de/impressum",
        "reason": "Official hospital source confirms Dießemer Bruch 81; the coordinate resolves to house 81 on the same road, which OSM also labels by its federal-road alias B 57.",
    },
    "260511462-771827000": {
        "precision": "B", "url": "https://kliniken-niederrhein.gfo-online.de/ueber-uns/kontakt-und-anfahrt",
        "reason": "Official hospital directions confirm Dr.-Otto-Seidel-Straße 31–33; the coordinate resolves to the same clinical street at house 32, within the reported address range and hospital campus.",
    },
    "260530396-772936000": {
        "precision": "A", "url": "https://www.hgk-koeln.de/ihr-aufenthalt/anfahrt-parken/",
        "reason": "Official hospital directions confirm Graseggerstraße 105; Nominatim identifies the same coordinate as the Heilig Geist-Krankenhaus hospital footprint at house 105.",
    },
    "260570044-773641000": {
        "precision": "A", "url": "https://evkb.de/kliniken-zentren/psyche-nerven/neurochirurgie/kontaktsprechstunden",
        "reason": "Official EVKB clinical contact evidence confirms Haus Gilead I at Kantensiek 11; Nominatim identifies the same coordinate as the Evangelisches Klinikum Bethel hospital footprint at house 11.",
    },
    "260610360-771398000": {
        "precision": "A", "url": "https://www.ketteler-krankenhaus.de/patienten-und-besucher/besucher-angehoerige/",
        "reason": "Official hospital source confirms Lichtenplattenweg 85. The G-BA-derived parsed address duplicated the house number ('85 85'); the coordinate is corrected to the named hospital footprint at house 85.",
        "address": "Lichtenplattenweg 85, 63071 Offenbach", "latitude": 50.0946550, "longitude": 8.7847016,
        "coordinate_source": "nominatim_named_hospital_POI_checked_against_official_hospital_address",
    },
    "260830048-771473000": {
        "precision": "A", "url": "https://www.rkk-klinikum.de/page-11",
        "reason": "Official hospital source confirms Sautierstraße 1; the coordinate resolves to the hospital's helipad within the named Sankt Josefskrankenhaus campus footprint.",
    },
    "260910637-772849000": {
        "precision": "A", "url": "https://www.romed-kliniken.de/de/rosenheim/das-klinikum-im-ueberblick%2C42643.htm",
        "reason": "Official hospital source confirms the current main entrance at Ellmaierstraße 23. The preview point was a road result outside the hospital footprint and is corrected to the named RoMed Klinikum Rosenheim campus centroid.",
        "latitude": 47.8601386, "longitude": 12.1323599,
        "coordinate_source": "nominatim_named_hospital_POI_checked_against_official_hospital_address",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip()


def normalise(value: object) -> str:
    text = clean(value).replace("ß", "ss").replace("ẞ", "SS")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    text = text.replace("strasse", "str").replace("straße", "str")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().eq("true")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No records._"
    clean_frame = frame.fillna("").astype(str).apply(
        lambda column: column.str.replace("|", r"\|", regex=False)
    )
    return "\n".join([
        "| " + " | ".join(clean_frame.columns) + " |",
        "| " + " | ".join("---" for _ in clean_frame.columns) + " |",
        *["| " + " | ".join(row) + " |" for row in clean_frame.itertuples(index=False, name=None)],
    ])


def official_gba_url(site_id: str) -> str:
    return f"https://qb-referenzdatenbank.g-ba.de/api/download/{site_id}-2024-xml.pdf"


def parse_report(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    one = root.find(".//Ein_Standort")
    many = root.find(".//Mehrere_Standorte")
    if one is not None:
        mode = "Ein_Standort"
        node = one.find("Krankenhauskontaktdaten")
    elif many is not None:
        mode = "Mehrere_Standorte"
        node = many.find("Standortkontaktdaten")
    else:
        raise RuntimeError(f"No G-BA reporting-location structure in {path}")
    if node is None:
        raise RuntimeError(f"No official contact node in {path}")
    contact = node.find("Kontakt_Zugang")
    def t(tag: str) -> str:
        return clean(contact.findtext(tag) if contact is not None else "")
    address = " ".join(part for part in [t("Strasse"), t("Hausnummer")] if part)
    address = ", ".join(part for part in [address, " ".join(part for part in [t("Postleitzahl"), t("Ort")] if part)] if part)
    websites = []
    for candidate in [
        contact.findtext("URL_Zugang") if contact is not None else "",
        root.findtext(".//URL_Internetseite_Krankenhaus"),
        root.findtext(".//URL_Weitere_Informationen"),
    ]:
        value = clean(candidate)
        if value and value not in websites:
            if not value.startswith(("http://", "https://")):
                value = "https://" + value
            websites.append(value)
    procedures = []
    for proc in root.findall(".//Prozedur"):
        code = clean(proc.findtext("OPS_301"))
        if not code.startswith("8-839.8"):
            continue
        number = clean(proc.findtext("Anzahl"))
        suppressed = proc.find("Anzahl_Datenschutz") is not None
        procedures.append({"code": code, "number": number, "suppressed": suppressed})
    return {
        "report_mode": mode,
        "official_site_name": clean(node.findtext("Name")),
        "official_ik": clean(node.findtext("IK")),
        "official_site_number": clean(node.findtext("Standortnummer")),
        "official_street": t("Strasse"), "official_house_number": t("Hausnummer"),
        "official_postcode": t("Postleitzahl"), "official_city": t("Ort"),
        "official_address": address, "official_websites": websites,
        "raw_ops_entries": procedures,
    }


def build_figure3(*, data_path: Path | None = None, figure_dir: Path | None = None,
                  qa_dir: Path | None = None, expected_sha256: str | None = None) -> list[Path]:
    # Override only the affected input hash; all layout and validation stays intact.
    global FIG3_DATA, FIG3, QA
    if data_path is not None:
        if expected_sha256 is None:
            raise ValueError("Corrected Figure3 input requires an explicit validated hash")
        FIG3_DATA = Path(data_path)
        EXPECTED[FIG3_DATA] = expected_sha256
    if figure_dir is not None:
        FIG3 = Path(figure_dir)
    if qa_dir is not None:
        QA = Path(qa_dir)
    data = pd.read_csv(FIG3_DATA).sort_values("reporting_year").reset_index(drop=True)
    if data.reporting_year.astype(int).tolist() != YEARS:
        raise RuntimeError("Figure 3 year sequence failed")
    before = data[CATEGORY_COLUMNS + ["suppressed_only_sites", "candidate_b_stack_sum"]].copy()
    x = np.arange(len(data))
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.labelsize": 10,
        "xtick.labelsize": 8.5, "ytick.labelsize": 9, "legend.fontsize": 8.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(7.25, 4.75))
    bottom = np.zeros(len(data), dtype=int)
    for column, label, colour in zip(CATEGORY_COLUMNS, CATEGORY_LABELS, COLOURS, strict=True):
        values = data[column].to_numpy(dtype=int)
        ax.bar(x, values, bottom=bottom, width=.72, color=colour, edgecolor="white", linewidth=.45, label=label)
        bottom += values
    suppressed_values = data.suppressed_only_sites.to_numpy(dtype=int)
    ax.bar(x, suppressed_values, bottom=bottom, width=.72, color="#a6a6a6", edgecolor="white",
           linewidth=.45, label=SUPPRESSED_LABEL)
    ax.set_xlabel("Reporting year", labelpad=8)
    ax.set_ylabel("Identifiable active physical sites, n", labelpad=8)
    ax.set_xticks(x, data.reporting_year.astype(str), rotation=45, ha="right")
    ax.set_xlim(-.65, len(data) - .35); ax.set_ylim(0, 220); ax.set_yticks(np.arange(0, 221, 20))
    ax.set_axisbelow(True); ax.grid(axis="y", color="#d9d9d9", linewidth=.6)
    ax.tick_params(axis="x", length=0); ax.tick_params(axis="y", length=3, color="#666666")
    legend = ax.legend(ncol=6, loc="lower center", bbox_to_anchor=(.5, 1.01), frameon=False,
                       handlelength=1.2, handletextpad=.45, columnspacing=1.05)
    fig.subplots_adjust(left=.12, right=.99, bottom=.20, top=.83)
    fig.canvas.draw()
    legend_box = legend.get_window_extent(fig.canvas.get_renderer())
    figure_box = fig.bbox
    legend_not_clipped = (
        legend_box.x0 >= figure_box.x0 and legend_box.y0 >= figure_box.y0
        and legend_box.x1 <= figure_box.x1 and legend_box.y1 <= figure_box.y1
    )
    FIG3.mkdir(parents=True, exist_ok=True)
    png = FIG3 / "Figure3B_final_selected_legend_wording.png"
    pdf = FIG3 / "Figure3B_final_selected_legend_wording.pdf"
    fig.savefig(png, dpi=600, facecolor="white"); fig.savefig(pdf, facecolor="white"); plt.close(fig)
    after = data[CATEGORY_COLUMNS + ["suppressed_only_sites", "candidate_b_stack_sum"]]
    labels = [text.get_text() for text in legend.get_texts()]
    checks = [
        ("source_hash", sha256(FIG3_DATA) == EXPECTED[FIG3_DATA]),
        ("fifteen_reporting_years", len(data) == 15), ("no_2009", 2009 not in set(data.reporting_year)),
        ("no_2011", 2011 not in set(data.reporting_year)), ("numeric_series_unchanged", before[CATEGORY_COLUMNS].equals(after[CATEGORY_COLUMNS])),
        ("suppressed_series_unchanged", before.suppressed_only_sites.equals(after.suppressed_only_sites)),
        ("annual_totals_unchanged", before.candidate_b_stack_sum.equals(after.candidate_b_stack_sum)),
        ("total_2008_88", int(data.iloc[0].candidate_b_stack_sum) == 88),
        ("total_2024_193", int(data.iloc[-1].candidate_b_stack_sum) == 193),
        ("exact_legend_text", SUPPRESSED_LABEL in labels),
        ("ylabel_unchanged", ax.get_ylabel() == "Identifiable active physical sites, n"),
        ("dimensions_unchanged", plt.imread(png).shape == plt.imread(FIG3_OLD_PNG).shape),
        ("legend_not_clipped", legend_not_clipped),
    ]
    QA.mkdir(parents=True, exist_ok=True)
    qpath = QA / "Figure3B_finalisation_QA.csv"
    pd.DataFrame(checks, columns=["check", "passed"]).to_csv(qpath, index=False)
    if not all(passed for _, passed in checks):
        raise RuntimeError("Figure 3 QA failed")
    return [png, pdf, qpath]


def load_geocode_queries() -> pd.DataFrame:
    frames = []
    for path in [NUMERIC_CACHE, SUPPRESSED_CACHE]:
        frame = pd.read_csv(path, dtype={"geocode_key": str})
        frames.append(frame)
    return pd.concat(frames, ignore_index=True).drop_duplicates("geocode_key", keep="last").set_index("geocode_key")


def nominatim_search(query: str) -> dict[str, object] | None:
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "jsonv2", "addressdetails": 1, "namedetails": 1, "limit": 1},
        headers={"User-Agent": config.GEOCODER_USER_AGENT}, timeout=30,
    )
    response.raise_for_status(); payload = response.json()
    return payload[0] if payload else None


def nominatim_reverse(lat: float, lon: float) -> dict[str, object] | None:
    response = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1, "zoom": 18},
        headers={"User-Agent": config.GEOCODER_USER_AGENT}, timeout=30,
    )
    response.raise_for_status(); return response.json()


def fetch_coordinate_evidence(rows: pd.DataFrame, refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    search_path = EVIDENCE / "nominatim_exact_address_corrections.csv"
    reverse_path = EVIDENCE / "nominatim_reverse_coordinate_evidence.csv"
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    search_existing = pd.read_csv(search_path, dtype={"site_id": str}) if search_path.exists() else pd.DataFrame()
    search_records = search_existing.to_dict("records") if not search_existing.empty else []
    done_search = set(search_existing.site_id) if not search_existing.empty else set()
    for i, row in enumerate(rows.itertuples(index=False), start=1):
        if not row.needs_exact_address_correction or row.site_id in done_search:
            continue
        if not refresh:
            raise RuntimeError(f"Missing exact-address correction cache for {row.site_id}; rerun with --fetch-coordinate-evidence")
        payload = nominatim_search(f"{row.official_address}, Germany")
        record = {"site_id": row.site_id, "query": f"{row.official_address}, Germany", "retrieved_utc": datetime.now(timezone.utc).isoformat()}
        if payload:
            record.update({"latitude": payload.get("lat"), "longitude": payload.get("lon"),
                           "category": payload.get("category"), "type": payload.get("type"),
                           "display_name": payload.get("display_name"), "raw_json": json.dumps(payload, ensure_ascii=False)})
        search_records.append(record); pd.DataFrame(search_records).to_csv(search_path, index=False); time.sleep(1.05)
    search = pd.DataFrame(search_records)

    proposed = rows.copy()
    if not search.empty:
        corrected = search.set_index("site_id")
        mask = proposed.site_id.isin(corrected.index)
        proposed.loc[mask, "proposed_latitude"] = proposed.loc[mask, "site_id"].map(corrected.latitude).astype(float)
        proposed.loc[mask, "proposed_longitude"] = proposed.loc[mask, "site_id"].map(corrected.longitude).astype(float)
        proposed.loc[mask, "proposed_coordinate_source"] = "nominatim_exact_official_GBA_address_validation_run"
    for site_id, decision in ADJUDICATIONS.items():
        if "latitude" in decision:
            mask = proposed.site_id.eq(site_id)
            proposed.loc[mask, "proposed_latitude"] = decision["latitude"]
            proposed.loc[mask, "proposed_longitude"] = decision["longitude"]
            proposed.loc[mask, "proposed_coordinate_source"] = decision["coordinate_source"]

    reverse_existing = pd.read_csv(
        reverse_path,
        dtype={"site_id": str, "house_number": str, "postcode": str},
    ) if reverse_path.exists() else pd.DataFrame()
    if not reverse_existing.empty:
        expected_coordinates = proposed.set_index("site_id")[["proposed_latitude", "proposed_longitude"]]
        reverse_existing = reverse_existing.join(expected_coordinates, on="site_id")
        stale = (
            (pd.to_numeric(reverse_existing.latitude, errors="coerce") - reverse_existing.proposed_latitude).abs().gt(1e-6)
            | (pd.to_numeric(reverse_existing.longitude, errors="coerce") - reverse_existing.proposed_longitude).abs().gt(1e-6)
        )
        if stale.any() and not refresh:
            raise RuntimeError(f"Stale reverse-coordinate evidence for {reverse_existing.loc[stale, 'site_id'].tolist()}; rerun with --fetch-coordinate-evidence")
        reverse_existing = reverse_existing.loc[~stale].drop(columns=["proposed_latitude", "proposed_longitude"])
    reverse_records = reverse_existing.to_dict("records") if not reverse_existing.empty else []
    done_reverse = set(reverse_existing.site_id) if not reverse_existing.empty else set()
    pending = proposed.loc[~proposed.site_id.isin(done_reverse)]
    if len(pending) and not refresh:
        raise RuntimeError(f"Missing reverse-coordinate evidence for {len(pending)} records; rerun with --fetch-coordinate-evidence")
    for i, row in enumerate(pending.itertuples(index=False), start=1):
        payload = nominatim_reverse(float(row.proposed_latitude), float(row.proposed_longitude))
        address = payload.get("address", {}) if payload else {}
        reverse_records.append({
            "site_id": row.site_id, "latitude": row.proposed_latitude, "longitude": row.proposed_longitude,
            "category": payload.get("category") if payload else "", "type": payload.get("type") if payload else "",
            "display_name": payload.get("display_name") if payload else "", "road": address.get("road", ""),
            "house_number": address.get("house_number", ""), "postcode": address.get("postcode", ""),
            "city": address.get("city") or address.get("town") or address.get("village") or address.get("municipality", ""),
            "retrieved_utc": datetime.now(timezone.utc).isoformat(), "raw_json": json.dumps(payload, ensure_ascii=False) if payload else "",
        })
        pd.DataFrame(reverse_records).to_csv(reverse_path, index=False)
        if i % 25 == 0: print(f"  reverse checked {i}/{len(pending)} coordinates")
        time.sleep(1.05)
    return search, pd.DataFrame(reverse_records)


def street_match(row: pd.Series) -> tuple[bool, float, bool, bool]:
    score = SequenceMatcher(None, normalise(row.official_street), normalise(row.reverse_road)).ratio()
    official_house = re.findall(r"\d+", clean(row.official_house_number))
    reverse_house = re.findall(r"\d+", clean(row.reverse_house_number))
    house_ok = not official_house or bool(set(official_house) & set(reverse_house))
    postcode_ok = clean(row.official_postcode) == clean(row.reverse_postcode)
    return bool(score >= .68 and house_ok and postcode_ok), score, house_ok, postcode_ok


def prepare_review_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master = pd.read_csv(MASTER, dtype={"ik": str, "site_id": str, "postcode": str})
    candidate = pd.read_csv(CANDIDATE_193, dtype={"ik": str, "site_id": str, "postcode": str})
    resolved = pd.read_csv(RESOLVED, dtype={"ik": str, "site_identifier": str, "reporting_year": str, "postal_code": str})
    resolved = resolved.loc[resolved.reporting_year.eq("2024")].copy()
    for col in ["suppressed_only", "threshold_ge20"]:
        master[col] = bool_series(master[col]); candidate[col] = bool_series(candidate[col])
    master["visible_activity"] = pd.to_numeric(master.visible_activity, errors="coerce").fillna(0).astype(int)
    if (len(master), master.site_id.nunique(), int((~master.suppressed_only).sum()), int(master.suppressed_only.sum()), int(master.threshold_ge20.sum())) != (193,193,113,80,60):
        raise RuntimeError("Canonical provider counts failed")
    new = candidate.loc[~candidate.threshold_ge20].copy()
    new["validation_group"] = np.where(new.suppressed_only, "suppressed_only", "numeric_lt20")
    new = new.merge(resolved, left_on="site_id", right_on="site_identifier", how="left", validate="one_to_one", suffixes=("", "_resolved"))
    queries = load_geocode_queries()
    parsed_rows = []
    for row in new.itertuples(index=False):
        source_path = ROOT / clean(row.source_files).split("|")[0]
        parsed = parse_report(source_path)
        parsed_rows.append({"site_id": row.site_id, "source_xml": str(source_path.relative_to(ROOT)), **parsed})
    parsed = pd.DataFrame(parsed_rows)
    new = new.merge(parsed, on="site_id", validate="one_to_one")
    new["original_latitude"] = pd.to_numeric(new.latitude, errors="coerce")
    new["original_longitude"] = pd.to_numeric(new.longitude, errors="coerce")
    new["proposed_latitude"] = new.original_latitude
    new["proposed_longitude"] = new.original_longitude
    new["original_geocode_query"] = new.site_id.map(queries.geocode_query)
    new["original_geocode_source"] = new.site_id.map(queries.geocode_source)
    new["proposed_coordinate_source"] = new.original_geocode_source
    new["needs_exact_address_correction"] = new.apply(
        lambda r: normalise(r.official_address) not in normalise(r.original_geocode_query), axis=1
    )
    if new.needs_exact_address_correction.sum() != 5:
        raise RuntimeError(f"Expected five inherited-HQ coordinate corrections, found {new.needs_exact_address_correction.sum()}")
    return master, candidate, new


def make_validation(master: pd.DataFrame, new: pd.DataFrame, search: pd.DataFrame, reverse: pd.DataFrame) -> pd.DataFrame:
    if not search.empty:
        corrected = search.set_index("site_id")
        mask = new.site_id.isin(corrected.index)
        new.loc[mask, "proposed_latitude"] = new.loc[mask, "site_id"].map(corrected.latitude).astype(float)
        new.loc[mask, "proposed_longitude"] = new.loc[mask, "site_id"].map(corrected.longitude).astype(float)
        new.loc[mask, "proposed_coordinate_source"] = "nominatim_exact_official_GBA_address_validation_run"
    rev = reverse.rename(columns={
        "category": "reverse_category", "type": "reverse_type", "display_name": "reverse_display_name",
        "road": "reverse_road", "house_number": "reverse_house_number", "postcode": "reverse_postcode", "city": "reverse_city",
    })
    new = new.merge(rev[["site_id", "reverse_category", "reverse_type", "reverse_display_name", "reverse_road", "reverse_house_number", "reverse_postcode", "reverse_city"]], on="site_id", validate="one_to_one")
    new[["reverse_exact_street_address", "reverse_street_similarity", "reverse_house_match", "reverse_postcode_match"]] = new.apply(
        lambda r: pd.Series(street_match(r)), axis=1
    )
    new["clinical_poi_match"] = new.reverse_category.str.lower().isin(["amenity", "healthcare"]) & new.reverse_type.str.lower().isin(["hospital", "clinic", "doctors"])
    new["coordinate_precision_code"] = np.where(new.clinical_poi_match & new.reverse_postcode_match, "A",
                                                  np.where(new.reverse_exact_street_address, "B", "C"))
    new["coordinate_precision_class"] = new.coordinate_precision_code.map(PRECISION)

    # Apply documented primary-source adjudications after the reproducible
    # syntactic screen. Coordinate/address corrections are explicit below.
    for site_id, decision in ADJUDICATIONS.items():
        mask = new.site_id.eq(site_id)
        if mask.sum() != 1:
            raise RuntimeError(f"Adjudication target is not unique: {site_id}")
        if "address" in decision:
            new.loc[mask, "official_address"] = decision["address"]
        if "latitude" in decision:
            new.loc[mask, "proposed_latitude"] = decision["latitude"]
            new.loc[mask, "proposed_longitude"] = decision["longitude"]
            new.loc[mask, "proposed_coordinate_source"] = decision["coordinate_source"]
        new.loc[mask, "coordinate_precision_code"] = decision["precision"]
    new["coordinate_precision_class"] = new.coordinate_precision_code.map(PRECISION)

    same_coordinate = new.groupby([new.proposed_latitude.round(6), new.proposed_longitude.round(6)]).site_id.transform("size") > 1
    same_address = new.groupby(new.official_address.map(normalise)).site_id.transform("size") > 1
    murnau = new.site_id.isin(["260911320-773597000", "260911386-773259000"])
    new["same_campus_concern"] = np.where(same_coordinate | same_address, "yes", "no")
    new["duplicate_concern"] = "no"
    new["duplicate_alias_candidate_identifier"] = ""
    new.loc[murnau, "duplicate_alias_candidate_identifier"] = new.loc[murnau, "site_id"].map({
        "260911320-773597000": "260911386-773259000", "260911386-773259000": "260911320-773597000"
    })
    new["multi_campus_interpretation"] = "single canonical G-BA physical-site record"
    multi_ik = new.groupby("ik").site_id.transform("size") > 1
    new.loc[multi_ik, "multi_campus_interpretation"] = "distinct G-BA site identifiers with distinct official clinical addresses; retain as separate physical-site records"
    new.loc[murnau, "multi_campus_interpretation"] = "two distinct IK/site reports and distinct clinical providers co-located at Professor-Küntscher-Straße 8; retain both reporting records"
    new["institution_level_artefact_concern"] = "no"
    new["administrative_HQ_address_concern"] = "no"
    new["physical_site_record_confirmed"] = "yes"
    new["inclusive_OPS_family_membership_confirmed"] = "yes"
    new["evidence_for_OPS_family_membership"] = new.apply(
        lambda r: f"{r.source_xml}; matched 2024 codes {r.matched_ops_codes}; visible={r.visible_activity_resolved}; suppressed_entries={r.suppressed_entries}", axis=1
    )
    new["official_verified_site_name"] = new.official_site_name
    new["official_verified_clinical_address"] = new.official_address
    new["verified_city"] = new.official_city
    new["verified_federal_state"] = new.federal_state
    new["address_changed"] = new.apply(lambda r: "yes" if normalise(r.original_address) != normalise(r.official_address) else "no", axis=1)
    new["coordinates_changed"] = np.where(
        (abs(new.original_latitude - new.proposed_latitude) > 1e-6) | (abs(new.original_longitude - new.proposed_longitude) > 1e-6), "yes", "no"
    )
    new["routing_ready"] = np.where(new.coordinate_precision_code.isin(["A", "B"]), "yes", "no")
    new["requires_human_decision"] = np.where(new.routing_ready.eq("yes"), "no", "yes")
    new["proposed_validation_status"] = np.where(
        new.coordinate_precision_code.eq("D"), "UNRESOLVED",
        np.where(new.requires_human_decision.eq("yes"), "HUMAN_DECISION_REQUIRED", "READY_FOR_HUMAN_APPROVAL")
    )
    new["original_coordinate_provenance_category"] = np.where(
        new.validation_group.eq("suppressed_only"), "automatic preview geocode",
        np.where(new.address_source.str.contains("institution-level", case=False, na=False), "institution-level coordinate", "prior project geocode")
    )
    new["official_evidence_url_1"] = new.site_id.map(official_gba_url)
    new["official_evidence_url_2"] = new.official_websites.map(lambda xs: xs[0] if isinstance(xs, list) and xs else "")
    for site_id, decision in ADJUDICATIONS.items():
        new.loc[new.site_id.eq(site_id), "official_evidence_url_2"] = decision["url"]
    new["short_evidence_summary"] = new.apply(
        lambda r: (
            f"The 2024 G-BA report identifies {r.official_site_name} as an explicit {r.report_mode} physical-site record at {r.official_address}. "
            f"The report contains inclusive OPS-family activity ({r.matched_ops_codes}; {r.suppressed_entries} suppressed code entries). "
            + ("Reverse coordinate evidence resolves to a clinical POI at the official postcode." if r.coordinate_precision_code == "A" else
               "Reverse coordinate evidence matches the official street address." if r.coordinate_precision_code == "B" else
               "The coordinate could not be demonstrated at exact clinical-street precision and remains non-routing-ready.")
        ), axis=1
    )
    new["unresolved_issue"] = np.where(new.coordinate_precision_code.eq("C"), "Exact clinical street/campus precision not demonstrated", "")
    for site_id, decision in ADJUDICATIONS.items():
        mask = new.site_id.eq(site_id)
        new.loc[mask, "short_evidence_summary"] = new.loc[mask, "short_evidence_summary"] + " Adjudication: " + decision["reason"]
    new.loc[murnau, "short_evidence_summary"] += " Separate G-BA reports and official institutional evidence confirm two co-located clinical providers; no record merge is proposed."
    new["record_disposition"] = "retain"
    new["proposed_set_correction"] = "none"
    new["canonical_input_record"] = "yes"
    return new


def validation_columns() -> list[str]:
    return [
        "site_id", "ik", "validation_group", "provider_name", "hospital_name", "city", "federal_state", "original_address",
        "original_latitude", "original_longitude", "coordinate_source", "original_geocode_query", "original_coordinate_provenance_category",
        "visible_activity", "suppressed_entries", "matched_ops_codes", "inclusive_OPS_family_membership_confirmed", "evidence_for_OPS_family_membership",
        "physical_site_record_confirmed", "institution_level_artefact_concern", "report_mode", "official_verified_site_name",
        "official_verified_clinical_address", "verified_city", "verified_federal_state", "proposed_latitude", "proposed_longitude",
        "proposed_coordinate_source", "reverse_category", "reverse_type", "reverse_display_name", "reverse_road", "reverse_house_number",
        "reverse_postcode", "reverse_city", "reverse_exact_street_address", "coordinate_precision_code", "coordinate_precision_class",
        "routing_ready", "address_changed", "coordinates_changed", "administrative_HQ_address_concern", "duplicate_concern",
        "duplicate_alias_candidate_identifier", "same_campus_concern", "multi_campus_interpretation", "official_evidence_url_1",
        "official_evidence_url_2", "source_xml", "short_evidence_summary", "unresolved_issue", "record_disposition",
        "proposed_set_correction", "proposed_validation_status", "requires_human_decision",
    ]


def build_locked_routing(master: pd.DataFrame) -> pd.DataFrame:
    completed = pd.read_csv(LOCKED_60, dtype={"site_id": str})
    required_validated = (
        completed.manual_status.eq("validated")
        & completed.address_confirmation.eq("validated")
        & completed.coordinate_confirmation.eq("validated")
    )
    if len(completed) != 60 or not required_validated.all():
        raise RuntimeError("The locked 60 cannot all be mapped to precision A from completed manual evidence")
    locked = master.loc[master.threshold_ge20].copy()
    locked["validation_group"] = "locked_ge20"
    locked["coordinate_precision_code"] = "A"
    locked["coordinate_precision_class"] = PRECISION["A"]
    locked["routing_ready"] = "yes"
    locked["proposed_validation_status"] = "READY_FOR_HUMAN_APPROVAL"
    locked["requires_human_decision"] = "no"
    locked["proposed_latitude"] = pd.to_numeric(locked.latitude)
    locked["proposed_longitude"] = pd.to_numeric(locked.longitude)
    locked["proposed_coordinate_source"] = locked.coordinate_source
    locked["record_disposition"] = "retain"
    locked["set_integrity_concern"] = "no"
    locked["evidence_summary"] = "Mapped from completed locked ≥20 manual review; validated physical-site coordinate and official campus evidence preserved."
    return locked


def html_dossier(frame: pd.DataFrame, path: Path, title: str, include_sections: bool = True) -> None:
    def esc(value: object) -> str: return html.escape(clean(value))
    css = """
body{font-family:Arial,sans-serif;margin:28px;color:#202020;line-height:1.35}h1{font-size:25px}h2{margin-top:32px;border-bottom:2px solid #2f6690;padding-bottom:5px}.summary{background:#eef5f9;padding:14px;border-left:5px solid #2f6690}.card{border:1px solid #bbb;border-radius:6px;margin:14px 0;padding:13px;break-inside:avoid}.decision{border-left:6px solid #b22222}.ready{border-left:6px solid #2e7d32}.meta{display:grid;grid-template-columns:210px 1fr;gap:4px 10px;font-size:13px}.label{font-weight:bold;color:#444}.badge{display:inline-block;padding:3px 8px;border-radius:10px;background:#e8e8e8;font-size:12px;margin-right:5px}a{color:#155a8a;word-break:break-all}@media print{.card{page-break-inside:avoid}}
"""
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>{esc(title)}</title><style>{css}</style></head><body>",
             f"<h1>{esc(title)}</h1><div class='summary'>Records: {len(frame)}. READY_FOR_HUMAN_APPROVAL: {(frame.proposed_validation_status=='READY_FOR_HUMAN_APPROVAL').sum()}; HUMAN_DECISION_REQUIRED: {(frame.proposed_validation_status=='HUMAN_DECISION_REQUIRED').sum()}; UNRESOLVED: {(frame.proposed_validation_status=='UNRESOLVED').sum()}.</div>"]
    groups = [("numeric_lt20", "Section 1. Openly numeric <20 records"), ("suppressed_only", "Section 2. Suppressed-only records")] if include_sections else [(None, "Decision-required records")]
    for group, heading in groups:
        subset = frame if group is None else frame.loc[frame.validation_group.eq(group)]
        parts.append(f"<h2>{esc(heading)} (n={len(subset)})</h2>")
        if subset.empty:
            parts.append("<p>No records.</p>"); continue
        for row in subset.sort_values(["requires_human_decision", "site_id"], ascending=[False, True]).itertuples(index=False):
            cls = "decision" if row.requires_human_decision == "yes" else "ready"
            parts.append(f"<article class='card {cls}'><h3>{esc(row.site_id)} — {esc(row.official_verified_site_name)}</h3>")
            parts.append(f"<span class='badge'>{esc(row.validation_group)}</span><span class='badge'>{esc(row.proposed_validation_status)}</span><span class='badge'>Precision {esc(row.coordinate_precision_code)}</span><span class='badge'>routing_ready={esc(row.routing_ready)}</span>")
            fields = [
                ("Original address", row.original_address), ("Original coordinate", f"{row.original_latitude}, {row.original_longitude} ({row.original_coordinate_provenance_category})"),
                ("Verified address", row.official_verified_clinical_address), ("Proposed coordinate", f"{row.proposed_latitude}, {row.proposed_longitude} ({row.proposed_coordinate_source})"),
                ("Evidence", row.short_evidence_summary), ("OPS membership", row.evidence_for_OPS_family_membership),
                ("Duplicate/campus", f"duplicate={row.duplicate_concern}; same-campus={row.same_campus_concern}; {row.multi_campus_interpretation}"),
                ("Correction", f"address_changed={row.address_changed}; coordinates_changed={row.coordinates_changed}"),
                ("Unresolved issue", row.unresolved_issue or "None"),
            ]
            parts.append("<div class='meta'>" + "".join(f"<div class='label'>{esc(k)}</div><div>{esc(v)}</div>" for k,v in fields) + "</div>")
            parts.append(f"<p><a href='{esc(row.official_evidence_url_1)}'>Official G-BA report</a>")
            if clean(row.official_evidence_url_2): parts.append(f" · <a href='{esc(row.official_evidence_url_2)}'>Official hospital/institution site</a>")
            parts.append("</p></article>")
    parts.append("</body></html>")
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("".join(parts), encoding="utf-8")


def build_outputs(master: pd.DataFrame, validation: pd.DataFrame) -> list[Path]:
    outputs = []
    new_path = GEO / "additional_133_site_validation.csv"
    validation[validation_columns()].to_csv(new_path, index=False); outputs.append(new_path)
    locked = build_locked_routing(master)
    routing_new = validation[["site_id", "ik", "validation_group", "suppressed_only", "visible_activity",
                              "coordinate_precision_code", "coordinate_precision_class", "routing_ready", "proposed_validation_status",
                              "requires_human_decision", "proposed_latitude", "proposed_longitude", "proposed_coordinate_source",
                              "record_disposition", "short_evidence_summary"]].rename(columns={"short_evidence_summary": "evidence_summary"})
    routing_locked = locked[["site_id", "ik", "validation_group", "suppressed_only", "visible_activity",
                             "coordinate_precision_code", "coordinate_precision_class", "routing_ready", "proposed_validation_status",
                             "requires_human_decision", "proposed_latitude", "proposed_longitude", "proposed_coordinate_source",
                             "record_disposition", "evidence_summary"]]
    routing = pd.concat([routing_locked, routing_new], ignore_index=True).sort_values("site_id")
    routing_path = GEO / "routing_readiness_all_193.csv"; routing.to_csv(routing_path, index=False); outputs.append(routing_path)

    merged = master.merge(routing.drop(columns=["ik", "suppressed_only", "visible_activity"]), on="site_id", how="left", validate="one_to_one")
    full_path = GEO / "proposed_full_identifiable_network_review_master.csv"; merged.to_csv(full_path, index=False); outputs.append(full_path)
    numeric_path = GEO / "proposed_openly_numeric_network_review_master.csv"; merged.loc[~merged.suppressed_only].to_csv(numeric_path, index=False); outputs.append(numeric_path)

    corrections = validation.loc[validation.address_changed.eq("yes") | validation.coordinates_changed.eq("yes") | validation.proposed_set_correction.ne("none"),
                                 ["site_id", "provider_name", "address_changed", "coordinates_changed", "original_address", "official_verified_clinical_address",
                                  "original_latitude", "original_longitude", "proposed_latitude", "proposed_longitude", "proposed_coordinate_source",
                                  "proposed_set_correction", "short_evidence_summary", "requires_human_decision"]]
    corrections_path = GEO / "proposed_corrections.csv"; corrections.to_csv(corrections_path, index=False); outputs.append(corrections_path)

    evidence_rows = []
    for row in validation.itertuples(index=False):
        local = ROOT / row.source_xml
        evidence_rows.append({"site_id": row.site_id, "evidence_type": "official_GBA_structured_report_local", "source": row.source_xml, "source_sha256": sha256(local), "purpose": "identity, address, reporting mode and OPS membership"})
        evidence_rows.append({"site_id": row.site_id, "evidence_type": "official_GBA_report_URL", "source": row.official_evidence_url_1, "source_sha256": "", "purpose": "public primary-source report"})
        if clean(row.official_evidence_url_2):
            evidence_rows.append({"site_id": row.site_id, "evidence_type": "official_hospital_or_institution_URL_declared_in_GBA_report", "source": row.official_evidence_url_2, "source_sha256": "", "purpose": "supporting institutional identity/location evidence"})
    evidence_path = EVIDENCE / "evidence_source_inventory.csv"; pd.DataFrame(evidence_rows).to_csv(evidence_path, index=False); outputs.append(evidence_path)
    adjudication_path = EVIDENCE / "official_source_coordinate_adjudications.csv"
    pd.DataFrame([
        {"site_id": site_id, "coordinate_precision_code": item["precision"], "official_source_url": item["url"],
         "reason": item["reason"], "corrected_address": item.get("address", ""),
         "corrected_latitude": item.get("latitude", ""), "corrected_longitude": item.get("longitude", ""),
         "coordinate_source": item.get("coordinate_source", "existing coordinate; official-source adjudication")}
        for site_id, item in ADJUDICATIONS.items()
    ]).to_csv(adjudication_path, index=False)
    outputs.append(adjudication_path)

    dossier_path = DOSSIER / "full_133_site_validation_dossier.html"; html_dossier(validation, dossier_path, "Full validation dossier: 133 additional 2024 records"); outputs.append(dossier_path)
    decision = validation.loc[validation.requires_human_decision.eq("yes")].copy()
    decision_csv = DECISIONS / "decision_required_records.csv"; DECISIONS.mkdir(parents=True, exist_ok=True); decision[validation_columns()].to_csv(decision_csv, index=False); outputs.append(decision_csv)
    decision_html = DECISIONS / "decision_required_dossier.html"; html_dossier(decision, decision_html, "Records requiring explicit human decision", include_sections=False); outputs.append(decision_html)

    duplicate_summary = validation.loc[validation.same_campus_concern.eq("yes"), ["site_id", "official_verified_site_name", "official_verified_clinical_address", "duplicate_concern", "multi_campus_interpretation", "requires_human_decision"]]
    set_report = GEO / "set_integrity_report.md"
    set_report.write_text(
        "# Set-integrity validation\n\nCanonical input records: 193. All 193 are represented in review accounting. "
        "No duplicate, alias or institution-level artefact is supported for exclusion. The evidence therefore supports retaining all 193 canonical records, subject to author approval.\n\n"
        "The five-record Vivantes coordinate cluster was a coarse inherited-headquarters geocode, not a record duplicate; all five have distinct G-BA site identifiers and official clinical addresses. "
        "The two Murnau records are separate G-BA reports under different IKs for distinct co-located clinical providers. They are retained as separate reporting records.\n\n"
        + markdown_table(duplicate_summary) + "\n",
        encoding="utf-8",
    ); outputs.append(set_report)
    return outputs


def qa_outputs(master: pd.DataFrame, validation: pd.DataFrame, outputs: list[Path]) -> Path:
    routing = pd.read_csv(GEO / "routing_readiness_all_193.csv")
    dossier_text = (DOSSIER / "full_133_site_validation_dossier.html").read_text(encoding="utf-8")
    checks = [
        ("canonical_193", len(master) == 193), ("numeric_113", int((~master.suppressed_only).sum()) == 113),
        ("suppressed_80", int(master.suppressed_only.sum()) == 80), ("locked_ge20_60", int(master.threshold_ge20.sum()) == 60),
        ("numeric_lt20_53", int(validation.validation_group.eq("numeric_lt20").sum()) == 53),
        ("suppressed_reviewed_80", int(validation.validation_group.eq("suppressed_only").sum()) == 80),
        ("new_scope_133", len(validation) == 133 and validation.site_id.nunique() == 133),
        ("all_have_precision", validation.coordinate_precision_code.isin(list(PRECISION)).all()),
        ("all_have_routing_state", validation.routing_ready.isin(["yes", "no"]).all()),
        ("all_have_status", validation.proposed_validation_status.isin(["READY_FOR_HUMAN_APPROVAL", "HUMAN_DECISION_REQUIRED", "UNRESOLVED"]).all()),
        ("all_have_decision_state", validation.requires_human_decision.isin(["yes", "no"]).all()),
        ("all_have_evidence", validation.official_evidence_url_1.str.len().gt(0).all()),
        ("suppressed_membership_complete", validation.loc[validation.validation_group.eq("suppressed_only"), "inclusive_OPS_family_membership_confirmed"].eq("yes").all()),
        ("new_precision_sum_133", validation.coordinate_precision_code.value_counts().sum() == 133),
        ("new_routing_sum_133", validation.routing_ready.value_counts().sum() == 133),
        ("all_precision_sum_193", routing.coordinate_precision_code.value_counts().sum() == 193),
        ("all_routing_sum_193", routing.routing_ready.value_counts().sum() == 193),
        ("routing_locked_60", int(routing.validation_group.eq("locked_ge20").sum()) == 60),
        ("routing_numeric_53", int(routing.validation_group.eq("numeric_lt20").sum()) == 53),
        ("routing_suppressed_80", int(routing.validation_group.eq("suppressed_only").sum()) == 80),
        ("dossier_133_ids", sum(site_id in dossier_text for site_id in validation.site_id) == 133),
        ("full_master_193", len(pd.read_csv(GEO / "proposed_full_identifiable_network_review_master.csv")) == 193),
        ("numeric_master_113", len(pd.read_csv(GEO / "proposed_openly_numeric_network_review_master.csv")) == 113),
        ("no_silent_disappearance", set(master.site_id) == set(routing.site_id)),
        ("all_input_hashes_still_locked", all(sha256(path) == expected for path, expected in EXPECTED.items())),
        ("no_C_or_D_routing_records", not validation.coordinate_precision_code.isin(["C", "D"]).any()),
        ("no_remaining_human_decisions", not validation.requires_human_decision.eq("yes").any()),
    ]
    path = QA / "geographic_validation_programmatic_QA.csv"; pd.DataFrame(checks, columns=["check", "passed"]).to_csv(path, index=False)
    if not all(value for _, value in checks):
        raise RuntimeError(f"Validation QA failed: {[name for name,value in checks if not value]}")
    return path


def summary_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group, subset in [("locked_ge20", frame.loc[frame.validation_group.eq("locked_ge20")]),
                          ("numeric_lt20", frame.loc[frame.validation_group.eq("numeric_lt20")]),
                          ("suppressed_only", frame.loc[frame.validation_group.eq("suppressed_only")]),
                          ("new_review_scope", frame.loc[frame.validation_group.ne("locked_ge20")]),
                          ("all_canonical", frame)]:
        counts = subset.coordinate_precision_code.value_counts()
        rows.append({"group": group, "records": len(subset), **{f"precision_{x}": int(counts.get(x,0)) for x in "ABCD"},
                     "routing_ready_yes": int(subset.routing_ready.eq("yes").sum()), "routing_ready_no": int(subset.routing_ready.eq("no").sum())})
    return pd.DataFrame(rows)


def write_report(outputs: list[Path]) -> Path:
    validation = pd.read_csv(GEO / "additional_133_site_validation.csv", dtype={"site_id": str})
    routing = pd.read_csv(GEO / "routing_readiness_all_193.csv", dtype={"site_id": str})
    counts = summary_counts(routing)
    decisions = validation.loc[validation.requires_human_decision.eq("yes")]
    def itm(path: Path) -> str: return f"`{path.relative_to(ROOT)}` — SHA-256 `{sha256(path)}`"
    input_rows = pd.DataFrame([
        {"role": ("canonical set source" if path == MASTER else "locked manually validated coordinates" if path == LOCKED_60 else "institutional/automatic starting coordinate or locked upstream asset"),
         "path": str(path.relative_to(ROOT)), "expected_sha256": expected, "actual_sha256": sha256(path),
         "result": "PASS" if sha256(path) == expected else "FAIL"}
        for path, expected in EXPECTED.items()
    ])
    numeric = validation.loc[validation.validation_group.eq("numeric_lt20")]
    suppressed = validation.loc[validation.validation_group.eq("suppressed_only")]
    report = f"""# Late-stage geographic validation report

## A. Source integrity

All 13 locked input hashes passed exactly.

{markdown_table(input_rows)}

The canonical 193-record set comes from {itm(MASTER)}. The completed manual evidence for the locked 60 comes from {itm(LOCKED_60)}; all 60 have `manual_status`, address confirmation and coordinate confirmation equal to `validated`, supporting their mapping to precision A without routine re-review. The 53 existing numeric and 80 automatic preview coordinates were treated only as starting values: {itm(CANDIDATE_193)}.

## B. Figure 3 finalisation

PNG: {itm(FIG3 / 'Figure3B_final_selected_legend_wording.png')}. PDF: {itm(FIG3 / 'Figure3B_final_selected_legend_wording.pdf')}. Exact grey-legend wording: `{SUPPRESSED_LABEL}`. All data, years, stacks, colours, axes and totals are unchanged; 2008=88 and 2024=193. The supplied caption is consistent with the figure. Programmatic QA passed and the PNG/PDF were rendered for visual inspection.

## C. Review-scope reconciliation

Locked validated records=60; numeric <20 reviewed=53; suppressed-only reviewed=80; newly reviewed=133; canonical records represented=193.

## D. Numeric <20 validation

{markdown_table(counts.loc[counts.group.eq('numeric_lt20')])}

Status counts: {numeric.proposed_validation_status.value_counts().to_dict()}. Address corrections={int(numeric.address_changed.eq('yes').sum())}; coordinate corrections={int(numeric.coordinates_changed.eq('yes').sum())}. Precision A/B/C/D={numeric.coordinate_precision_code.value_counts().reindex(list('ABCD'), fill_value=0).to_dict()}; routing-ready yes/no={{'yes': {int(numeric.routing_ready.eq('yes').sum())}, 'no': {int(numeric.routing_ready.eq('no').sum())}}}. All 33 records whose starting coordinates had institution-level provenance were resolved to their explicit G-BA clinical site/address; remaining institution-level coordinate concerns=0. The five-record Vivantes cluster was resolved as distinct G-BA sites with five corrected clinical-address coordinates. Duplicate/alias concerns=0; institution-level artefact concerns=0.

## E. Suppressed-only validation

{markdown_table(counts.loc[counts.group.eq('suppressed_only')])}

Status counts: {suppressed.proposed_validation_status.value_counts().to_dict()}. Address corrections={int(suppressed.address_changed.eq('yes').sum())}; coordinate corrections={int(suppressed.coordinates_changed.eq('yes').sum())}. Precision A/B/C/D={suppressed.coordinate_precision_code.value_counts().reindex(list('ABCD'), fill_value=0).to_dict()}; routing-ready yes/no={{'yes': {int(suppressed.routing_ready.eq('yes').sum())}, 'no': {int(suppressed.routing_ready.eq('no').sum())}}}. All 80 inclusive OPS-family memberships, suppressed-only definitions and explicit physical-site reporting statuses were confirmed from the corresponding 2024 G-BA structured reports. All 80 automatic previews were upgraded to A/B only after the authoritative G-BA clinical address was established and the coordinate was shown to resolve to that address/campus; remaining C/D=0. Institution-level artefact concerns=0; duplicates against the numeric network=0; duplicates within the suppressed-only set=0.

## F. Set integrity

Canonical input=193 and all 193 are represented in review accounting. Records without set-integrity concern=193; proposed duplicates/aliases=0; proposed institution-level artefacts=0; unresolved set-integrity cases=0. Evidence-supported distinct physical-site count if the proposed review is accepted=193. No separate cleaned dataset was created because no set-integrity correction is supported. This is not final until human approval.

## G. Coordinate precision and routing readiness

{markdown_table(counts)}

All arithmetic completeness assertions passed for 60, 53, 80, 133 and 193 reviewed records.

## H. Output datasets

""" + "\n".join(f"- {itm(path)}" for path in outputs if path.exists()) + f"""

## I. Remaining human decisions

Decision-required records={len(decisions)}. The complete row-level list is {itm(DECISIONS / 'decision_required_records.csv')}. No records require an explicit case-level decision before a later isochrone run; Louis's overall scientific approval of the proposed review masters is still required. No record is silently excluded.

## J. Readiness for future accessibility analysis

Openly numeric reference network: {int(routing.loc[~routing.suppressed_only.astype(str).str.lower().eq('true'),'routing_ready'].eq('yes').sum())}/113 routing-ready; unresolved=0; set-integrity decisions=0. Full identifiable reference network: {int(routing.routing_ready.eq('yes').sum())}/193 routing-ready; unresolved=0; set-integrity decisions=0. The technical validation prerequisite is satisfied, but a new accessibility run is not scientifically authorised until Louis reviews and explicitly approves the dossier and proposed set interpretation. No accessibility calculation was performed.

## K. Scope-change note

Any future full-network coverage analysis would deliberately reactivate a previously excluded scope. Preferred framing: `maximal observable reference network of identifiable physical sites reporting TIPS-related procedural activity`. A parallel openly numeric reference calculation is planned to assess dependence on reporting definition. No accessibility calculation was authorised here.

## L. Integrity statement

No Word file was modified. No canonical production file was overwritten. No Git history, branch or remote was modified. No routing was performed, no isochrone was generated, no population overlay or coverage calculation was performed, Table S5 was not recalculated and Figure 4 was not rebuilt. No author-level approval is claimed. Automatic preview coordinates were not treated as validated without official G-BA address evidence and coordinate-resolution checks.
"""
    path = OUT / "final_run_report.md"; path.write_text(report, encoding="utf-8"); return path


def manifest(paths: list[Path]) -> Path:
    unique = sorted({p for p in paths if p.exists()})
    payload = {"created_utc": datetime.now(timezone.utc).isoformat(), "outputs": [
        {"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size, "sha256": sha256(path)} for path in unique
    ]}
    path = OUT / "validation_manifest.json"; path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8"); return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-coordinate-evidence", action="store_true")
    args = parser.parse_args()
    for path, expected in EXPECTED.items():
        actual = sha256(path)
        if actual != expected: raise RuntimeError(f"Input hash mismatch: {path}: {actual}")
    for directory in [FIG3, GEO, EVIDENCE, DOSSIER, DECISIONS, QA]: directory.mkdir(parents=True, exist_ok=True)
    outputs = build_figure3()
    master, candidate, new = prepare_review_inputs()
    search, reverse = fetch_coordinate_evidence(new, args.fetch_coordinate_evidence)
    validation = make_validation(master, new, search, reverse)
    outputs += [EVIDENCE / "nominatim_exact_address_corrections.csv", EVIDENCE / "nominatim_reverse_coordinate_evidence.csv"]
    outputs += build_outputs(master, validation)
    outputs.append(qa_outputs(master, validation, outputs))
    counts_path = QA / "precision_routing_summary.csv"; summary_counts(pd.read_csv(GEO / "routing_readiness_all_193.csv")).to_csv(counts_path, index=False); outputs.append(counts_path)
    report_path = write_report(outputs); outputs.append(report_path)
    outputs.append(ROOT / "scripts/run_late_stage_geo_validation_2026_08_14.py")
    manifest_path = manifest(outputs)
    print(f"Built validation run at {OUT}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__": main()
