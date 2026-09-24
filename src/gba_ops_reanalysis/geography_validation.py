"""Offline-only helpers for validating corrected 2024 provider geography."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


EXPECTED_NETWORK_COUNTS = {
    "ge100": 16, "ge50": 31, "ge20": 60, "visible": 113, "all_active": 193,
}
ACCEPTED_CONFIRMATIONS = {"yes", "confirmed", "validated"}


def normalize_address(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("ß", "ss")
    text = re.sub(r"str(?:asse|\.)", "strasse", text)
    text = re.sub(r"\bgermany\b|\bdeutschland\b", "", text)
    text = re.sub(r"[^a-z0-9äöü]+", " ", text)
    return " ".join(text.split())


def reconstruct_provider_sets(site: pd.DataFrame) -> pd.DataFrame:
    work = site[site["reporting_year"] == 2024].copy()
    work["suppressed_only"] = (work["visible_activity"] == 0) & (work["suppressed_entries"] > 0)
    work["exclusive_volume_category"] = pd.cut(
        work["visible_activity"],
        bins=[-1, 0, 3, 19, 49, 99, 199, float("inf")],
        labels=["suppressed-only", "visible_1_3", "4–19", "20–49", "50–99", "100–199", "≥200"],
    ).astype(str)
    for threshold in (20, 50, 100, 200):
        work[f"threshold_ge{threshold}"] = work["visible_activity"] >= threshold
    return work.sort_values(["visible_activity", "site_identifier"], ascending=[False, True]).reset_index(drop=True)


def validate_provider_sets(providers: pd.DataFrame) -> dict[str, bool]:
    visible = providers["visible_activity"] > 0
    checks = {
        "visible_113": int(visible.sum()) == 113,
        "ge20_60": int(providers["threshold_ge20"].sum()) == 60,
        "ge50_31": int(providers["threshold_ge50"].sum()) == 31,
        "ge100_16": int(providers["threshold_ge100"].sum()) == 16,
        "ge200_6": int(providers["threshold_ge200"].sum()) == 6,
        "all_active_193": len(providers) == 193,
        "nested_ge100_ge50": set(providers.loc[providers.threshold_ge100, "site_identifier"])
        <= set(providers.loc[providers.threshold_ge50, "site_identifier"]),
        "nested_ge50_ge20": set(providers.loc[providers.threshold_ge50, "site_identifier"])
        <= set(providers.loc[providers.threshold_ge20, "site_identifier"]),
    }
    return checks


def address_status(row: pd.Series) -> str:
    complete = all(str(row.get(c, "") or "").strip() not in {"", "nan"} for c in (
        "street", "house_number", "postal_code", "city"
    ))
    source = str(row.get("address_source", ""))
    if source == "site-specific address from source data":
        return "validated site-specific address" if complete else "probable site-specific address"
    if source in {
        "institution-level address inherited by a site",
        "institution-level address from aggregate report",
    }:
        return "institution-level address only"
    return "no address found" if not str(row.get("full_address", "") or "").strip() else "probable site-specific address"


def query_matches_address(query: Any, address: Any) -> bool:
    q, a = normalize_address(query), normalize_address(address)
    return bool(q and a and (q == a or a in q or q in a))


def confirmation_is_accepted(value: Any) -> bool:
    return str(value or "").strip().casefold() in ACCEPTED_CONFIRMATIONS


def apply_manual_reviews(work: pd.DataFrame, reviewed: pd.DataFrame) -> pd.DataFrame:
    """Apply explicitly sourced review decisions without inventing corrections.

    Existing address and coordinate values may be confirmed unchanged. Corrected
    addresses require a complete manual address and postcode; corrected coordinates
    require both latitude and longitude. A traceable evidence source is mandatory
    for every promotion.
    """
    result = work.copy()
    review_id = "site_id" if "site_id" in reviewed.columns else "site_identifier"
    review_rows = reviewed.fillna("").drop_duplicates(review_id).set_index(review_id)
    editable = (
        "manual_status", "manual_address", "manual_postcode", "manual_federal_state",
        "manual_latitude", "manual_longitude", "manual_source", "manual_notes",
        "address_confirmation", "federal_state_confirmation", "coordinate_confirmation",
        "evidence_source", "review_notes",
    )
    for index, row in result.iterrows():
        site_id = str(row.site_identifier)
        if site_id not in review_rows.index:
            continue
        review = review_rows.loc[site_id]
        for column in editable:
            if column in review_rows.columns:
                result.at[index, column] = str(review.get(column, ""))
        evidence = str(review.get("evidence_source") or review.get("manual_source") or "").strip()
        if not evidence:
            continue

        if confirmation_is_accepted(review.get("address_confirmation")):
            manual_address = str(review.get("manual_address", "")).strip()
            manual_postcode = str(review.get("manual_postcode", "")).strip()
            if manual_address:
                match = re.search(r"(?:,\s*)?(\d{5})\s+([^,]+)\s*$", manual_address)
                if not manual_postcode or not match or match.group(1) != manual_postcode:
                    continue
                street_part = manual_address[:match.start()].strip(" ,")
                street_match = re.match(r"(.+?)\s+(\d+\S*)$", street_part)
                if not street_match:
                    continue
                result.at[index, "original_address"] = manual_address
                result.at[index, "normalised_address"] = normalize_address(manual_address)
                result.at[index, "street"] = street_match.group(1)
                result.at[index, "house_number"] = street_match.group(2)
                result.at[index, "postal_code"] = manual_postcode
                result.at[index, "city"] = match.group(2).strip()
            complete = all(
                str(result.at[index, column] or "").strip() not in {"", "nan"}
                for column in ("street", "house_number", "postal_code", "city")
            )
            if complete:
                result.at[index, "address_validation_status"] = "validated site-specific address"
                result.at[index, "address_source_file"] = evidence
                result.at[index, "exact_source_field_or_xml_path"] = "manual review: official source"
                result.at[index, "source_type"] = "reviewed official physical-site evidence"

        if confirmation_is_accepted(review.get("coordinate_confirmation")):
            manual_latitude = str(review.get("manual_latitude", "")).strip()
            manual_longitude = str(review.get("manual_longitude", "")).strip()
            if bool(manual_latitude) != bool(manual_longitude):
                continue
            if manual_latitude:
                result.at[index, "latitude"] = float(manual_latitude)
                result.at[index, "longitude"] = float(manual_longitude)
                result.at[index, "geocode_source"] = str(review.get("manual_source") or evidence)
                result.at[index, "geocode_query"] = str(
                    review.get("manual_address") or result.at[index, "original_address"]
                )
            if pd.notna(result.at[index, "latitude"]) and pd.notna(result.at[index, "longitude"]):
                result.at[index, "coordinate_validation_status"] = (
                    "validated physical-site coordinate"
                )
                result.at[index, "coordinate_validation_reason"] = (
                    "manually confirmed against official physical-site evidence"
                )

        if (
            confirmation_is_accepted(review.get("federal_state_confirmation"))
            and str(review.get("manual_federal_state", "")).strip()
        ):
            result.at[index, "federal_state"] = str(review["manual_federal_state"]).strip()
            result.at[index, "federal_state_source"] = evidence
            result.at[index, "federal_state_status"] = "validated from site-specific address"
    return result


def manual_priority(activity: float, suppressed_only: bool) -> int:
    if activity >= 100:
        return 1
    if activity >= 50:
        return 2
    if activity >= 20:
        return 3
    if activity > 0:
        return 4
    return 5 if suppressed_only else 4


def network_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "ge100": frame["visible_activity"] >= 100,
        "ge50": frame["visible_activity"] >= 50,
        "ge20": frame["visible_activity"] >= 20,
        "visible": frame["visible_activity"] > 0,
        "all_active": (frame["visible_activity"] > 0) | (frame["suppressed_entries"] > 0),
    }


__all__ = [
    "ACCEPTED_CONFIRMATIONS", "EXPECTED_NETWORK_COUNTS", "address_status",
    "apply_manual_reviews", "confirmation_is_accepted", "manual_priority",
    "network_masks", "normalize_address", "query_matches_address",
    "reconstruct_provider_sets", "validate_provider_sets",
]
