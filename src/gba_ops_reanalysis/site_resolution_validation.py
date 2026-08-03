"""Validation-only provider resolution for the audited TIPS OPS extract.

This module deliberately consumes the immutable code-level audit table.  It does
not alter the production parser or its defaults.  Spatial precedence is applied
within exact (year, IK, OPS code) groups.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd


THRESHOLDS = (20, 50, 100, 200)


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def is_aggregate_99(site_identifier: Any) -> bool:
    return str(site_identifier).strip().lower().endswith("-99")


def _address_from_element(element: ET.Element | None) -> dict[str, str]:
    def text(name: str) -> str:
        if element is None:
            return ""
        found = element.find(f".//{name}")
        return found.text.strip() if found is not None and found.text else ""

    values = {
        "street": text("Strasse"),
        "house_number": text("Hausnummer"),
        "postal_code": text("Postleitzahl"),
        "city": text("Ort"),
    }
    values["full_address"] = ", ".join(
        item for item in (
            " ".join(x for x in (values["street"], values["house_number"]) if x).strip(),
            " ".join(x for x in (values["postal_code"], values["city"]) if x).strip(),
        ) if item
    )
    return values


def extract_address_provenance(source_files: pd.Series, root_dir: Path) -> pd.DataFrame:
    """Extract explicit institution/site address nodes without using generic XPath precedence."""
    rows: list[dict[str, Any]] = []
    for source in sorted(set(source_files.dropna().astype(str))):
        path = Path(source)
        if not path.is_absolute():
            path = root_dir / path
        try:
            root = ET.parse(path).getroot()
        except Exception:
            continue
        stem = path.stem.split("-")
        ik = stem[0] if stem else ""
        site_number = stem[1] if len(stem) > 1 else ""
        year = int(stem[2]) if len(stem) > 2 and stem[2].isdigit() else pd.NA
        site = _address_from_element(root.find(".//Standortkontaktdaten"))
        institution = _address_from_element(root.find(".//Krankenhauskontaktdaten"))
        legacy_element = root.find(".//Einziger_Standort/Kontaktdaten")
        if legacy_element is None:
            legacy_element = root.find(".//Kontaktdaten")
        legacy = _address_from_element(legacy_element)
        if site["full_address"]:
            selected = site
            source_class = "site-specific address from source data"
        elif institution["full_address"]:
            selected = institution
            source_class = "institution-level address inherited by a site"
        elif legacy["full_address"]:
            selected = legacy
            source_class = "unresolved legacy contact-address hierarchy"
        else:
            selected = _address_from_element(None)
            source_class = "unresolved or missing address"
        rows.append(
            {
                "year": year,
                "facility_id": f"{ik}-{site_number}".strip("-"),
                **selected,
                "address_source": (
                    "institution-level address from aggregate report"
                    if site_number == "99" and institution["full_address"]
                    else source_class
                ),
                "site_full_address": site["full_address"],
                "institution_full_address": institution["full_address"],
                "legacy_contact_full_address": legacy["full_address"],
                "address_source_file": source,
            }
        )
    return pd.DataFrame(rows)


def prepare_code_records(code_level: pd.DataFrame) -> pd.DataFrame:
    work = code_level.copy()
    work["reporting_year"] = pd.to_numeric(work["reporting_year"], errors="raise").astype(int)
    work["ik"] = work["ik"].astype(str).str.replace(r"\.0$", "", regex=True)
    work["site_identifier"] = work["site_identifier"].astype(str)
    work["OPS_code"] = work["OPS_code"].astype(str)
    for column in (
        "numeric_count",
        "current_parser_numeric_count",
        "suppressed_record_count",
        "raw_record_count",
    ):
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0).astype(int)
    work["suppressed_flag"] = work["suppressed_flag"].fillna(False).astype(bool)
    work["is_aggregate_99"] = work["site_identifier"].map(is_aggregate_99)
    work["visible_count"] = work["current_parser_numeric_count"]
    work["suppressed_entries"] = work["suppressed_record_count"]
    return work


def resolve_component_precedence(
    code_level: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve exact code groups and return annotated records plus overlap audit."""
    work = prepare_code_records(code_level)
    keys = ["reporting_year", "ik", "OPS_code"]
    work["component_exists"] = work.groupby(keys)["is_aggregate_99"].transform(lambda s: (~s).any())
    work["aggregate_exists"] = work.groupby(keys)["is_aggregate_99"].transform("any")
    work["retained_site_resolution"] = ~work["is_aggregate_99"] | ~work["component_exists"]
    work["resolution_reason"] = np.select(
        [
            work["is_aggregate_99"] & work["component_exists"],
            work["is_aggregate_99"] & ~work["component_exists"],
            ~work["is_aggregate_99"] & work["aggregate_exists"],
        ],
        [
            "aggregate_excluded_component_site_precedence",
            "aggregate_retained_no_component_site_unresolved_institution",
            "component_site_retained_precedence",
        ],
        default="component_or_single_site_retained",
    )
    work["unresolved_institution_provider"] = work["is_aggregate_99"] & ~work["component_exists"]

    rows: list[dict[str, Any]] = []
    for (year, ik, code), group in work.groupby(keys, sort=True):
        aggregates = group[group["is_aggregate_99"]]
        components = group[~group["is_aggregate_99"]]
        if aggregates.empty or components.empty:
            continue
        aggregate_source = int(aggregates["numeric_count"].sum())
        aggregate_production = int(aggregates["visible_count"].sum())
        component_visible = int(components["visible_count"].sum())
        suppressed = int(components["suppressed_entries"].sum())
        lower = component_visible + suppressed
        midpoint = component_visible + 2 * suppressed
        upper = component_visible + 3 * suppressed
        residual = aggregate_source - component_visible
        assessable = bool(aggregate_source > 0)
        rows.append(
            {
                "reporting_year": year,
                "ik": ik,
                "institution_name": next(
                    (str(x) for x in group["hospital_name"] if str(x).strip() and str(x) != "nan"), ""
                ),
                "OPS_code": code,
                "aggregate_site_identifiers": "|".join(sorted(aggregates["site_identifier"].unique())),
                "aggregate_numeric_source_value": aggregate_source,
                "aggregate_production_visible_value": aggregate_production,
                "aggregate_suppressed": bool(aggregates["suppressed_flag"].any()),
                "component_site_count": int(components["site_identifier"].nunique()),
                "component_visible_sum": component_visible,
                "suppressed_component_entries": suppressed,
                "visible_residual_source_aggregate_minus_components": residual,
                "component_total_lower": lower,
                "component_total_midpoint": midpoint,
                "component_total_upper": upper,
                "aggregate_value_assessable": assessable,
                "aggregate_within_suppression_interval": (
                    bool(lower <= aggregate_source <= upper) if assessable else pd.NA
                ),
                "exact_visible_equality": (
                    bool(aggregate_source == component_visible) if assessable else pd.NA
                ),
                "nonzero_difference_compatible_with_suppression": (
                    bool(residual != 0 and lower <= aggregate_source <= upper) if assessable else pd.NA
                ),
                "retained_records": "|".join(sorted(components["site_identifier"].unique())),
                "resolution": "retain all components; exclude aggregate; residual diagnostic only",
                "removed_legacy_visible_count": aggregate_production,
            }
        )
    audit = pd.DataFrame(rows)
    for column in (
        "aggregate_within_suppression_interval",
        "exact_visible_equality",
        "nonzero_difference_compatible_with_suppression",
    ):
        if column in audit:
            audit[column] = audit[column].astype("boolean")
    return work, audit


def aggregate_resolved_records(
    annotated: pd.DataFrame, contacts: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    retained = annotated[annotated["retained_site_resolution"]].copy()
    grouping = ["reporting_year", "site_identifier", "ik"]
    site = (
        retained.groupby(grouping, as_index=False)
        .agg(
            hospital_name=("hospital_name", "first"),
            visible_activity=("visible_count", "sum"),
            suppressed_entries=("suppressed_entries", "sum"),
            suppressed_any=("suppressed_flag", "any"),
            matched_ops_codes=("OPS_code", lambda s: "|".join(sorted(set(map(str, s))))),
            source_files=("source_file", lambda s: "|".join(sorted(set(map(str, s))))),
            unresolved_institution_provider=("unresolved_institution_provider", "any"),
        )
    )
    site["reporting_unit_type"] = np.where(
        site["unresolved_institution_provider"], "unresolved_aggregate_99", "physical_site"
    )
    site["lower_activity"] = site["visible_activity"] + site["suppressed_entries"]
    site["midpoint_activity"] = site["visible_activity"] + 2 * site["suppressed_entries"]
    site["upper_activity"] = site["visible_activity"] + 3 * site["suppressed_entries"]
    if contacts is not None and not contacts.empty:
        contact = contacts.copy()
        contact["year"] = pd.to_numeric(contact["year"], errors="coerce").astype("Int64")
        contact["facility_id"] = contact["facility_id"].astype(str)
        keep = [
            "year", "facility_id", "hospital_name", "street", "house_number",
            "postal_code", "city", "phone", "email",
        ]
        keep.extend(
            column
            for column in (
                "address_source",
                "site_full_address",
                "institution_full_address",
                "legacy_contact_full_address",
                "address_source_file",
            )
            if column in contact.columns
        )
        contact = contact[keep].drop_duplicates(["year", "facility_id"])
        site = site.merge(
            contact,
            left_on=["reporting_year", "site_identifier"],
            right_on=["year", "facility_id"],
            how="left",
            suffixes=("", "_contact"),
        ).drop(columns=["year", "facility_id"], errors="ignore")
        site["hospital_name"] = site["hospital_name_contact"].fillna(site["hospital_name"])
        site = site.drop(columns=["hospital_name_contact"], errors="ignore")
    for col in ("street", "house_number", "postal_code", "city", "phone", "email"):
        if col not in site:
            site[col] = ""
        site[col] = site[col].fillna("").astype(str).replace("nan", "")
    site["full_address"] = site.apply(
        lambda r: ", ".join(
            x for x in (
                " ".join(x for x in (r["street"], r["house_number"]) if x).strip(),
                " ".join(x for x in (r["postal_code"], r["city"]) if x).strip(),
            ) if x
        ),
        axis=1,
    )
    if "address_source_contact" in site:
        site["address_source"] = site["address_source_contact"].fillna("unresolved or missing address")
        site = site.drop(columns=["address_source_contact"], errors="ignore")
    elif "address_source" in site:
        site["address_source"] = site["address_source"].fillna("unresolved or missing address")
    else:
        site["address_source"] = np.where(
            site["unresolved_institution_provider"],
            "institution-level address from aggregate report",
            "address present but XML hierarchy provenance unavailable",
        )
    for column in ("site_full_address", "institution_full_address", "legacy_contact_full_address"):
        if column not in site:
            site[column] = ""
        site[column] = site[column].fillna("")

    institution = (
        site.groupby(["reporting_year", "ik"], as_index=False)
        .agg(
            hospital_name=("hospital_name", "first"),
            visible_activity=("visible_activity", "sum"),
            suppressed_entries=("suppressed_entries", "sum"),
            suppressed_any=("suppressed_any", "any"),
            component_provider_count=("site_identifier", "nunique"),
            site_identifiers=("site_identifier", lambda s: "|".join(sorted(set(map(str, s))))),
            contains_unresolved_aggregate=("unresolved_institution_provider", "any"),
            full_address=("full_address", "first"),
        )
    )
    institution["lower_activity"] = institution["visible_activity"] + institution["suppressed_entries"]
    institution["midpoint_activity"] = institution["visible_activity"] + 2 * institution["suppressed_entries"]
    institution["upper_activity"] = institution["visible_activity"] + 3 * institution["suppressed_entries"]
    institution["reporting_unit_type"] = "institution_ik"
    return site.sort_values(["reporting_year", "site_identifier"]), institution.sort_values(
        ["reporting_year", "ik"]
    )


def gini(values: pd.Series) -> float:
    array = np.sort(pd.to_numeric(values, errors="coerce").fillna(0).to_numpy(dtype=float))
    array = array[array > 0]
    if not len(array) or array.sum() == 0:
        return 0.0
    index = np.arange(1, len(array) + 1)
    return float(2 * np.sum(index * array) / (len(array) * array.sum()) - (len(array) + 1) / len(array))


def structural_metrics(data: pd.DataFrame, definition: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year, group in data.groupby("reporting_year", sort=True):
        visible = pd.to_numeric(group["visible_activity"], errors="coerce").fillna(0)
        active = visible[visible > 0].sort_values(ascending=False)
        total = float(active.sum())
        shares = active / total if total else pd.Series(dtype=float)
        row: dict[str, Any] = {
            "reporting_year": int(year),
            "provider_definition": definition,
            "visible_national_activity": int(total),
            "active_numeric_providers": int((visible > 0).sum()),
            "all_identifiable_active_providers": int(((visible > 0) | (group["suppressed_entries"] > 0)).sum()),
            "median_provider_volume": float(active.median()) if len(active) else 0.0,
            "minimum_provider_volume": int(active.min()) if len(active) else 0,
            "maximum_provider_volume": int(active.max()) if len(active) else 0,
            "top5_share_pct": round(100 * active.head(5).sum() / total, 4) if total else 0.0,
            "top10_share_pct": round(100 * active.head(10).sum() / total, 4) if total else 0.0,
            "top20_share_pct": round(100 * active.head(20).sum() / total, 4) if total else 0.0,
            "hhi_10000": round(float(np.square(shares).sum() * 10000), 4) if total else 0.0,
            "effective_center_count": round(float(1 / np.square(shares).sum()), 4)
            if total and np.square(shares).sum() else 0.0,
            "gini": round(gini(active), 6),
        }
        for threshold in THRESHOLDS:
            row[f"providers_ge_{threshold}"] = int((visible >= threshold).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def reporting_granularity(annotated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = annotated.copy()
    iy = (
        records.groupby(["reporting_year", "ik"], as_index=False)
        .agg(
            aggregate_present=("is_aggregate_99", "any"),
            component_present=("is_aggregate_99", lambda s: (~s).any()),
            component_sites=("site_identifier", lambda s: len({x for x in s if not is_aggregate_99(x)})),
        )
    )
    rows = []
    for year, group in iy.groupby("reporting_year", sort=True):
        only99 = group["aggregate_present"] & ~group["component_present"]
        onlycomp = ~group["aggregate_present"] & group["component_present"]
        both = group["aggregate_present"] & group["component_present"]
        multi = group.loc[group["component_sites"] > 1, "component_sites"]
        component_rows = records[(records["reporting_year"] == year) & ~records["is_aggregate_99"]]
        bysite = component_rows.groupby("site_identifier").agg(
            visible=("visible_count", "sum"), suppressed=("suppressed_entries", "sum")
        )
        rows.append(
            {
                "reporting_year": int(year),
                "unique_institutions": int(group["ik"].nunique()),
                "identifiable_component_sites": int(component_rows["site_identifier"].nunique()),
                "institutions_99_only": int(only99.sum()),
                "proportion_99_only": float(only99.mean()) if len(group) else 0,
                "institutions_component_only": int(onlycomp.sum()),
                "institutions_both": int(both.sum()),
                "unresolved_99_providers_retained": int(only99.sum()),
                "mean_component_sites_per_multisite_institution": float(multi.mean()) if len(multi) else 0,
                "median_component_sites_per_multisite_institution": float(multi.median()) if len(multi) else 0,
                "maximum_component_sites_per_institution": int(group["component_sites"].max()),
                "component_sites_numeric_activity": int((bysite["visible"] > 0).sum()),
                "component_sites_suppressed_only_activity": int(
                    ((bysite["visible"] == 0) & (bysite["suppressed"] > 0)).sum()
                ),
            }
        )
    years = sorted(iy["reporting_year"].unique())
    transitions = []
    for prior, current in zip(years[:-1], years[1:]):
        left = iy[iy["reporting_year"] == prior].set_index("ik")
        right = iy[iy["reporting_year"] == current].set_index("ik")
        for ik in sorted(set(left.index) & set(right.index)):
            before, after = left.loc[ik], right.loc[ik]
            if bool(before["aggregate_present"] and not before["component_present"]) and bool(
                after["component_present"]
            ):
                kind = "99_only_to_component_sites"
            elif bool(before["component_present"]) and bool(
                after["aggregate_present"] and not after["component_present"]
            ):
                kind = "component_sites_to_99_only"
            else:
                continue
            transitions.append(
                {
                    "previous_year": prior,
                    "reporting_year": current,
                    "ik": ik,
                    "transition_type": kind,
                    "previous_component_sites": int(before["component_sites"]),
                    "current_component_sites": int(after["component_sites"]),
                    "interpretation": "potential reporting-granularity change; not proof of provider opening/closure",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(transitions)


def parent_subcode_diagnostic(annotated: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, ik, site), group in annotated.groupby(
        ["reporting_year", "ik", "site_identifier"], sort=True
    ):
        parent = group[group["OPS_code"].str.lower().eq("8-839.8")]
        terminal = group[
            group["OPS_code"].str.lower().str.startswith("8-839.8")
            & ~group["OPS_code"].str.lower().eq("8-839.8")
        ]
        if parent.empty or terminal.empty:
            continue
        parent_value = int(parent["visible_count"].sum())
        sub_value = int(terminal["visible_count"].sum())
        relationship = "equal" if parent_value == sub_value else ("greater" if parent_value > sub_value else "less")
        rows.append(
            {
                "reporting_year": year,
                "ik": ik,
                "site_identifier": site,
                "institution_name": group["hospital_name"].iloc[0],
                "parent_code": "8-839.8",
                "terminal_subcodes": "|".join(sorted(terminal["OPS_code"].unique())),
                "parent_visible_value": parent_value,
                "subcode_visible_values": "|".join(
                    f"{r.OPS_code}:{r.visible_count}" for r in terminal.itertuples()
                ),
                "subcode_visible_sum": sub_value,
                "suppressed_entries": int(group["suppressed_entries"].sum()),
                "relationship_parent_to_subcode_sum": relationship,
                "source_reports": "|".join(sorted(group["source_file"].unique())),
                "current_production_treatment": "parent and terminal subcodes both retained and summed",
            }
        )
    return pd.DataFrame(rows)


def _similarity(a: Any, b: Any) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def identity_crosswalk(
    data: pd.DataFrame, level: str, id_column: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = data.copy()
    work["provider_id"] = work[id_column].astype(str)
    work["name_norm"] = work["hospital_name"].map(normalize_text)
    if "full_address" not in work:
        work["full_address"] = ""
    work["address_norm"] = work["full_address"].map(normalize_text)
    years = sorted(work["reporting_year"].unique())
    matches: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for previous, current in zip(years[:-1], years[1:]):
        left = work[work["reporting_year"] == previous]
        right = work[work["reporting_year"] == current]
        common = set(left["provider_id"]) & set(right["provider_id"])
        for provider_id in sorted(common):
            matches.append(
                {
                    "provider_level": level, "previous_year": previous, "reporting_year": current,
                    "previous_identifier": provider_id, "current_identifier": provider_id,
                    "match_status": "confirmed", "match_rule": "same_identifier",
                    "name_similarity": 1.0, "address_similarity": 1.0,
                }
            )
        lnew = left[~left["provider_id"].isin(common)]
        rnew = right[~right["provider_id"].isin(common)]
        candidates = []
        for lrow in lnew.itertuples():
            for rrow in rnew.itertuples():
                ns = _similarity(lrow.hospital_name, rrow.hospital_name)
                ads = _similarity(lrow.full_address, rrow.full_address)
                exact_name = bool(lrow.name_norm and lrow.name_norm == rrow.name_norm)
                exact_address = bool(lrow.address_norm and lrow.address_norm == rrow.address_norm)
                l_source = str(getattr(lrow, "address_source", ""))
                r_source = str(getattr(rrow, "address_source", ""))
                site_address_both = (
                    l_source == "site-specific address from source data"
                    and r_source == "site-specific address from source data"
                )
                if exact_name and exact_address and (level == "institution" or site_address_both):
                    status, rule = "confirmed", "exact_normalized_name_and_address"
                elif (
                    (exact_address and ns >= 0.85)
                    or (exact_name and ads >= 0.85)
                    or (ns >= 0.92 and ads >= 0.80)
                ):
                    status = "probable"
                    rule = (
                        "exact_name_address_but_site_address_provenance_not_confirmed"
                        if exact_name and exact_address
                        else "documented_name_address_similarity"
                    )
                else:
                    continue
                candidates.append((status == "confirmed", (ns + ads) / 2, lrow, rrow, ns, ads, rule, status))
        used_l: set[str] = set()
        used_r: set[str] = set()
        for _, _, lrow, rrow, ns, ads, rule, status in sorted(candidates, reverse=True, key=lambda x: (x[0], x[1])):
            if lrow.provider_id in used_l or rrow.provider_id in used_r:
                continue
            used_l.add(lrow.provider_id); used_r.add(rrow.provider_id)
            item = {
                "provider_level": level, "previous_year": previous, "reporting_year": current,
                "previous_identifier": lrow.provider_id, "current_identifier": rrow.provider_id,
                "previous_name": lrow.hospital_name, "current_name": rrow.hospital_name,
                "previous_address": lrow.full_address, "current_address": rrow.full_address,
                "previous_address_source": str(getattr(lrow, "address_source", "")),
                "current_address_source": str(getattr(rrow, "address_source", "")),
                "match_status": status, "match_rule": rule,
                "name_similarity": round(ns, 4), "address_similarity": round(ads, 4),
            }
            matches.append(item)
            if status == "probable":
                review.append({**item, "manual_review_reason": "probable continuity is not applied as definitive"})
    return pd.DataFrame(matches), pd.DataFrame(review)


def turnover_metrics(
    data: pd.DataFrame, crosswalk: pd.DataFrame, level: str, id_column: str
) -> pd.DataFrame:
    years = sorted(data["reporting_year"].unique())
    rows = []
    for threshold in THRESHOLDS:
        sets = {
            year: set(
                data.loc[
                    (data["reporting_year"] == year) & (data["visible_activity"] >= threshold),
                    id_column,
                ].astype(str)
            )
            for year in years
        }
        for previous, current in zip(years[:-1], years[1:]):
            raw_prev, raw_cur = sets[previous], sets[current]
            subset = crosswalk[
                (crosswalk["provider_level"] == level)
                & (crosswalk["previous_year"] == previous)
                & (crosswalk["reporting_year"] == current)
            ]
            for scenario, statuses in (
                ("raw_identifier", set()),
                ("confirmed_continuity", {"confirmed"}),
                ("confirmed_plus_probable", {"confirmed", "probable"}),
            ):
                pairs = {
                    (str(r.previous_identifier), str(r.current_identifier))
                    for r in subset.itertuples()
                    if r.match_status in statuses
                    and str(r.previous_identifier) != str(r.current_identifier)
                }
                linked = {(a, b) for a, b in pairs if a in raw_prev and b in raw_cur}
                retained_same = raw_prev & raw_cur
                rows.append(
                    {
                        "provider_level": level, "threshold": threshold,
                        "previous_year": previous, "reporting_year": current, "scenario": scenario,
                        "previous_providers": len(raw_prev), "current_providers": len(raw_cur),
                        "retained": len(retained_same) + len(linked),
                        "entries": len(raw_cur - retained_same - {b for _, b in linked}),
                        "exits": len(raw_prev - retained_same - {a for a, _ in linked}),
                        "entries_explained_identifier_continuity": len(linked),
                        "exits_explained_identifier_continuity": len(linked),
                    }
                )
    return pd.DataFrame(rows)


def classify_coordinates(site: pd.DataFrame, geocode_cache: pd.DataFrame) -> pd.DataFrame:
    result = site.copy()
    cache = geocode_cache.copy().rename(columns={"geocode_key": "site_identifier"})
    cache["site_identifier"] = cache["site_identifier"].astype(str)
    result = result.merge(cache, on="site_identifier", how="left")
    has_coord = result["latitude"].notna() & result["longitude"].notna()
    query_norm = result["geocode_query"].fillna("").map(normalize_text)
    site_norm = result.get("site_full_address", pd.Series("", index=result.index)).map(normalize_text)
    institution_norm = result.get(
        "institution_full_address", pd.Series("", index=result.index)
    ).map(normalize_text)
    query_matches_site = pd.Series(
        [bool(s and s in q) for q, s in zip(query_norm, site_norm)], index=result.index
    )
    query_matches_institution = pd.Series(
        [bool(a and a in q) for q, a in zip(query_norm, institution_norm)], index=result.index
    )
    result["coordinate_source_class"] = np.select(
        [
            ~has_coord,
            has_coord & result["geocode_source"].fillna("").str.contains("manual", case=False),
            has_coord & query_matches_site,
            has_coord & query_matches_institution,
        ],
        [
            "unresolved or ungeocoded",
            "existing manually corrected site-specific coordinate",
            "geocoded from a site-specific address",
            "geocoded from an institution-level address",
        ],
        default="coordinate present; address provenance unresolved",
    )
    result["coordinate_valid_germany_bbox"] = (
        result["latitude"].between(47.0, 55.5) & result["longitude"].between(5.0, 16.0)
    )
    result["coordinate_key"] = result.apply(
        lambda r: f"{r.latitude:.6f},{r.longitude:.6f}" if pd.notna(r.latitude) and pd.notna(r.longitude) else "",
        axis=1,
    )
    duplicate = result["coordinate_key"].ne("") & result.duplicated(
        ["reporting_year", "coordinate_key"], keep=False
    )
    result["shared_coordinate_same_year"] = duplicate
    result["requires_manual_review"] = (
        result["address_source"].ne("site-specific address from source data")
        | ~has_coord
        | ~result["coordinate_valid_germany_bbox"].fillna(False)
        | duplicate
    )
    return result


__all__ = [
    "THRESHOLDS", "aggregate_resolved_records", "classify_coordinates", "gini",
    "extract_address_provenance", "identity_crosswalk", "is_aggregate_99", "normalize_text",
    "parent_subcode_diagnostic", "prepare_code_records", "reporting_granularity",
    "resolve_component_precedence", "structural_metrics", "turnover_metrics",
]
