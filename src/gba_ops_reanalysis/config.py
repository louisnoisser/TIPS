"""Repository-level paths and defaults."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DATA_DIR: Final[Path] = ROOT / "data"
XML_DIR: Final[Path] = DATA_DIR / "xml"
DERIVED_DIR: Final[Path] = DATA_DIR / "derived"
GEOCODED_DIR: Final[Path] = DATA_DIR / "geocoded"
CACHE_DIR: Final[Path] = DATA_DIR / "cache"
SPATIAL_DIR: Final[Path] = ROOT / "spatial"
OUTPUTS_DIR: Final[Path] = ROOT / "outputs"
ISOCHRONE_CACHE_DIR: Final[Path] = CACHE_DIR / "isochrones"
GEOCODE_CACHE_DIR: Final[Path] = CACHE_DIR / "geocode"
POPULATION_CACHE_DIR: Final[Path] = CACHE_DIR / "population"
ISOCHRONE_OUTPUT_DIR: Final[Path] = OUTPUTS_DIR / "isochrones"
LONGITUDINAL_OUTPUT_DIR: Final[Path] = OUTPUTS_DIR / "longitudinal"

for path in (
    DERIVED_DIR,
    GEOCODED_DIR,
    CACHE_DIR,
    SPATIAL_DIR,
    OUTPUTS_DIR,
    ISOCHRONE_CACHE_DIR,
    GEOCODE_CACHE_DIR,
    POPULATION_CACHE_DIR,
    ISOCHRONE_OUTPUT_DIR,
    LONGITUDINAL_OUTPUT_DIR,
):
    path.mkdir(parents=True, exist_ok=True)

GERMANY_OUTLINE: Final[Path] = SPATIAL_DIR / "germany-detailed-boundary_917.geojson"
GERMANY_STATES: Final[Path] = SPATIAL_DIR / "germany-states.geojson"
GERMANY_COUNTIES: Final[Path] = SPATIAL_DIR / "georef-germany-kreis@public.geojson"
DEFAULT_SMOD_RASTER: Final[Path] = Path(
    os.getenv(
        "GBA_OPS_SMOD_RASTER",
        SPATIAL_DIR / "GHS_SMOD_E2025_GLOBE_R2023A_54009_1000_V2_0.tif",
    )
)


def _default_population_raster() -> Path:
    env_path = os.getenv("GBA_OPS_POP_RASTER")
    if env_path:
        return Path(env_path)

    local_candidate = SPATIAL_DIR / "GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif"
    if local_candidate.exists():
        return local_candidate

    legacy_candidate = Path(
        "/Users/larsmasanneck/Library/CloudStorage/OneDrive-Personal/"
        "Dokumente/Research Basics and Coding Projects/Data Projects/"
        "Marc Pawlitzki/GeoStroke/raw_data/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0.tif"
    )
    return legacy_candidate


DEFAULT_POP_RASTER: Final[Path] = _default_population_raster()
POP_TOTAL_FALLBACK: Final[int] = int(os.getenv("GBA_OPS_POP_TOTAL_FALLBACK", "83420000"))

ORS_BASE_URL: Final[str] = os.getenv("GBA_OPS_ORS_URL", "http://localhost:8080/ors")
ORS_PROFILE: Final[str] = os.getenv("GBA_OPS_ORS_PROFILE", "driving-car")
ORS_TIMEOUT: Final[int] = int(os.getenv("GBA_OPS_ORS_TIMEOUT", "180"))
ORS_MAX_LOCATIONS_PER_REQUEST: Final[int] = int(os.getenv("GBA_OPS_ORS_MAX_LOCATIONS", "5"))
GEOCODER_USER_AGENT: Final[str] = os.getenv(
    "GBA_OPS_GEOCODER_USER_AGENT",
    "gba_ops_reanalysis",
)
DEFAULT_COUNTRY_SUFFIX: Final[str] = os.getenv("GBA_OPS_COUNTRY_SUFFIX", "Germany")

# TIPS OPS 8-839.8* methodological code sets
CODESET_A_PRIMARY_ONLY: Final[list[str]] = [
    "8-839.87",
    "8-839.88",
    "8-839.89",
    "8-839.8a",
]
CODESET_B_LOOSEN: Final[list[str]] = [
    "8-839.81",
    "8-839.82",
    "8-839.83",
    "8-839.85",
    "8-839.87",
    "8-839.88",
    "8-839.89",
    "8-839.8a",
    "8-839.8x",
]
CODESET_C_INCLUSIVE: Final[list[str]] = [
    "8-839.81",
    "8-839.82",
    "8-839.83",
    "8-839.84",
    "8-839.85",
    "8-839.86",
    "8-839.87",
    "8-839.88",
    "8-839.89",
    "8-839.8a",
    "8-839.8x",
    "8-839.8X",
]
TIPS_CODESETS: Final[dict[str, list[str]]] = {
    "A_PRIMARY_ONLY": CODESET_A_PRIMARY_ONLY,
    "B_LOOSEN": CODESET_B_LOOSEN,
    "C_INCLUSIVE": CODESET_C_INCLUSIVE,
}


def codeset_to_selector(codes: list[str]) -> str:
    return ",".join(codes)


def resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate
