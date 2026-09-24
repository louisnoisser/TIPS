"""Geocoding helpers with CSV-based local caching."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
import zipfile

import pandas as pd
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import ArcGIS, Nominatim
import requests

from . import config


def build_geocode_key(row: pd.Series) -> str:
    preferred = [
        ("facility_id",),
        ("ik", "standortnummer"),
        ("hospital_name", "postal_code", "city"),
        ("full_address",),
        ("file_name",),
    ]
    for columns in preferred:
        values = [str(row.get(column, "")).strip() for column in columns]
        if all(value and value.lower() != "nan" for value in values):
            return "|".join(values)
    return str(row.name)


def build_query_candidates(row: pd.Series, country_suffix: str) -> list[tuple[str, str]]:
    candidates = [
        ("full_address", str(row.get("full_address", "")).strip()),
        (
            "street_city",
            " ".join(
                part
                for part in (
                    str(row.get("street", "")).strip(),
                    str(row.get("house_number", "")).strip(),
                    f"{str(row.get('postal_code', '')).strip()} {str(row.get('city', '')).strip()}".strip(),
                )
                if part
            ).strip(),
        ),
        ("postal_city", f"{str(row.get('postal_code', '')).strip()} {str(row.get('city', '')).strip()}".strip()),
        ("city", str(row.get("city", "")).strip()),
    ]
    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, candidate in candidates:
        clean = candidate.strip(" ,")
        if not clean:
            continue
        query = f"{clean}, {country_suffix}".strip(" ,")
        if query in seen:
            continue
        seen.add(query)
        deduped.append((label, query))
    return deduped


def _postal_cache_dir() -> Path:
    path = config.CACHE_DIR / "postal_codes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_postal_code(value: Any) -> str:
    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(5) if digits else ""


def _normalize_city(value: Any) -> str:
    return " ".join(str(value).strip().lower().split())


def load_german_postal_reference() -> pd.DataFrame:
    cache_path = _postal_cache_dir() / "geonames_de_postal_codes.tsv"
    if not cache_path.exists():
        response = requests.get("https://download.geonames.org/export/zip/DE.zip", timeout=60)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            with archive.open("DE.txt") as handle:
                cache_path.write_text(handle.read().decode("utf-8"), encoding="utf-8")

    columns = [
        "country_code",
        "postal_code",
        "place_name",
        "admin_name1",
        "admin_code1",
        "admin_name2",
        "admin_code2",
        "admin_name3",
        "admin_code3",
        "latitude",
        "longitude",
        "accuracy",
    ]
    postal = pd.read_csv(cache_path, sep="\t", header=None, names=columns, dtype={"postal_code": str})
    postal["postal_code"] = postal["postal_code"].map(_normalize_postal_code)
    postal["city_norm"] = postal["place_name"].map(_normalize_city)
    postal["latitude"] = pd.to_numeric(postal["latitude"], errors="coerce")
    postal["longitude"] = pd.to_numeric(postal["longitude"], errors="coerce")
    postal = postal.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    return postal


def postal_centroid_geocode(
    df: pd.DataFrame,
    *,
    postal_code_col: str = "postal_code",
    city_col: str = "city",
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    postal = load_german_postal_reference()
    work = df.copy().drop(
        columns=["latitude", "longitude", "admin_name1", "geocode_source", "geocode_query"],
        errors="ignore",
    )
    work["postal_code_norm"] = work[postal_code_col].map(_normalize_postal_code)
    work["city_norm"] = work[city_col].map(_normalize_city)
    work["row_id"] = range(len(work))

    exact = work.merge(
        postal[["postal_code", "city_norm", "admin_name1", "latitude", "longitude"]].rename(
            columns={"postal_code": "postal_code_ref", "admin_name1": "state_name_postal"}
        ),
        left_on=["postal_code_norm", "city_norm"],
        right_on=["postal_code_ref", "city_norm"],
        how="left",
    )

    unmatched = exact["latitude"].isna() | exact["longitude"].isna()
    if unmatched.any():
        postal_unique = (
            postal.sort_values(["postal_code", "accuracy"], ascending=[True, False])
            .drop_duplicates(subset=["postal_code"], keep="first")
            .rename(columns={"postal_code": "postal_code_ref", "admin_name1": "state_name_postal"})
        )
        fallback = (
            work.loc[work["row_id"].isin(exact.loc[unmatched, "row_id"])]
            .merge(
                postal_unique[["postal_code_ref", "state_name_postal", "latitude", "longitude"]],
                left_on="postal_code_norm",
                right_on="postal_code_ref",
                how="left",
            )
            .set_index("row_id")
        )
        exact = exact.set_index("row_id")
        exact.loc[fallback.index, "latitude"] = fallback["latitude"]
        exact.loc[fallback.index, "longitude"] = fallback["longitude"]
        exact.loc[fallback.index, "state_name_postal"] = fallback["state_name_postal"]
        exact = exact.reset_index()

    exact["admin_name1"] = exact["state_name_postal"]
    exact["geocode_source"] = exact["latitude"].notna().map(lambda matched: "geonames_postal_centroid" if matched else "")
    exact["geocode_query"] = exact.apply(
        lambda row: (
            f"{row.get('postal_code_norm', '')} {str(row.get(city_col, '')).strip()}".strip()
            if pd.notna(row.get("latitude"))
            else ""
        ),
        axis=1,
    )
    return exact.drop(
        columns=["postal_code_ref", "postal_code_norm", "city_norm", "state_name_postal", "row_id"],
        errors="ignore",
    )


def arcgis_address_fallback(
    df: pd.DataFrame,
    *,
    cache_path: Path,
    country_suffix: str = config.DEFAULT_COUNTRY_SUFFIX,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_columns = ["geocode_key", "latitude", "longitude", "geocode_source", "geocode_query"]
    if cache_path.exists():
        cache = pd.read_csv(cache_path)
        for column in cache_columns:
            if column not in cache.columns:
                cache[column] = ""
        cache = cache[cache_columns].drop_duplicates(subset=["geocode_key"], keep="last")
    else:
        cache = pd.DataFrame(columns=cache_columns)

    work = df.copy()
    work["geocode_key"] = work.apply(build_geocode_key, axis=1)
    work = work.drop(columns=["latitude", "longitude", "geocode_source", "geocode_query"], errors="ignore")
    work = work.merge(cache, how="left", on="geocode_key")

    unresolved = work.loc[work["latitude"].isna() | work["longitude"].isna()].drop_duplicates(subset=["geocode_key"])
    if unresolved.empty:
        return work.drop(columns=["geocode_key"], errors="ignore")

    geocoder = ArcGIS(timeout=10)
    updates: list[dict[str, object]] = []
    for index, row in enumerate(unresolved.itertuples(index=False), start=1):
        row_series = pd.Series(row._asdict())
        geocoded = None
        geocode_query = ""
        geocode_source = "failed_arcgis"
        for query_label, query in build_query_candidates(row_series, country_suffix):
            geocode_query = query
            try:
                geocoded = geocoder.geocode(query)
            except Exception:
                continue
            if geocoded is not None:
                geocode_source = f"arcgis_{query_label}"
                break
        if index % 25 == 0:
            print(f"  ArcGIS fallback geocoded {index}/{len(unresolved)} unresolved addresses")
        updates.append(
            {
                "geocode_key": str(row_series["geocode_key"]),
                "latitude": getattr(geocoded, "latitude", None),
                "longitude": getattr(geocoded, "longitude", None),
                "geocode_source": geocode_source,
                "geocode_query": geocode_query,
            }
        )

    update_df = pd.DataFrame(updates)
    if cache.empty:
        cache = update_df.copy()
    else:
        cache = pd.concat([cache, update_df], ignore_index=True)
    cache = cache.drop_duplicates(subset=["geocode_key"], keep="last").sort_values("geocode_key").reset_index(drop=True)
    cache.to_csv(cache_path, index=False)

    work = work.drop(columns=["latitude", "longitude", "geocode_source", "geocode_query"], errors="ignore")
    work = work.merge(cache, how="left", on="geocode_key")
    return work.drop(columns=["geocode_key"], errors="ignore")


def combined_postal_arcgis_geocode(
    df: pd.DataFrame,
    *,
    cache_path: Path,
    country_suffix: str = config.DEFAULT_COUNTRY_SUFFIX,
) -> pd.DataFrame:
    geocoded = postal_centroid_geocode(df)
    unresolved = geocoded.loc[geocoded["latitude"].isna() | geocoded["longitude"].isna()].copy()
    if unresolved.empty:
        return geocoded

    fallback = arcgis_address_fallback(
        unresolved,
        cache_path=cache_path,
        country_suffix=country_suffix,
    ).set_index("facility_id")
    result = geocoded.set_index("facility_id")
    for column in ("latitude", "longitude", "geocode_source", "geocode_query"):
        result.loc[fallback.index, column] = fallback[column]
    return result.reset_index()


def geocode_dataframe(
    df: pd.DataFrame,
    *,
    cache_path: Path,
    country_suffix: str = config.DEFAULT_COUNTRY_SUFFIX,
    min_delay_seconds: float = 1.0,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_columns = ["geocode_key", "latitude", "longitude", "geocode_source", "geocode_query"]
    if cache_path.exists():
        cache = pd.read_csv(cache_path)
        for column in cache_columns:
            if column not in cache.columns:
                cache[column] = ""
        cache = cache[cache_columns].drop_duplicates(subset=["geocode_key"], keep="last")
    else:
        cache = pd.DataFrame(columns=cache_columns)

    result = df.copy()
    result["geocode_key"] = result.apply(build_geocode_key, axis=1)
    result = result.merge(cache, how="left", on="geocode_key")

    nominatim = Nominatim(user_agent=config.GEOCODER_USER_AGENT, timeout=10)
    arcgis = ArcGIS(timeout=10)
    geocode_nominatim = RateLimiter(
        nominatim.geocode,
        min_delay_seconds=min_delay_seconds,
        max_retries=0,
        error_wait_seconds=min_delay_seconds,
        swallow_exceptions=False,
    )
    geocode_arcgis = RateLimiter(
        arcgis.geocode,
        min_delay_seconds=min_delay_seconds,
        max_retries=0,
        error_wait_seconds=min_delay_seconds,
        swallow_exceptions=False,
    )
    source_available = {
        "nominatim": True,
        "arcgis": True,
    }

    updates: list[dict[str, object]] = []
    missing_mask = result["latitude"].isna() | result["longitude"].isna()
    missing = result.loc[missing_mask].drop_duplicates(subset=["geocode_key"])

    for index, row in enumerate(missing.itertuples(index=False), start=1):
        row_series = pd.Series(row._asdict())
        if index % 25 == 0:
            print(f"  geocoded {index}/{len(missing)} uncached addresses")
        geocode_key = str(row_series["geocode_key"])
        geocoded = None
        geocode_source = "failed_all"
        geocode_query = ""

        strategies = [
            ("nominatim", geocode_nominatim),
            ("arcgis", geocode_arcgis),
        ]
        for source_name, geocoder in strategies:
            if not source_available[source_name]:
                continue
            for query_label, query in build_query_candidates(row_series, country_suffix):
                geocode_query = query
                try:
                    geocoded = geocoder(query)
                except (GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError):
                    # If a provider is unavailable (e.g., local/offline run), skip it for later rows.
                    source_available[source_name] = False
                    continue
                except Exception:
                    continue
                if geocoded is not None:
                    geocode_source = f"{source_name}_{query_label}"
                    break
            if geocoded is not None:
                break

        updates.append(
            {
                "geocode_key": geocode_key,
                "latitude": getattr(geocoded, "latitude", None),
                "longitude": getattr(geocoded, "longitude", None),
                "geocode_source": geocode_source,
                "geocode_query": geocode_query,
            }
        )

    if updates:
        update_df = pd.DataFrame(updates)
        if cache.empty:
            cache = update_df.copy()
        else:
            cache = pd.concat([cache, update_df], ignore_index=True)
        cache = (
            cache.drop_duplicates(subset=["geocode_key"], keep="last")
            .sort_values("geocode_key")
            .reset_index(drop=True)
        )
        cache.to_csv(cache_path, index=False)
        result = result.drop(columns=["latitude", "longitude", "geocode_source", "geocode_query"], errors="ignore")
        result = result.merge(cache, how="left", on="geocode_key")

    return result
