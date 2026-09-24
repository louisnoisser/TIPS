#!/usr/bin/env python3
"""Create the reproducible Priority-2-only TIPS geography review files."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "outputs/geography_validation_ge100_2026-07-24/"
    "geography_manual_review_ge20_2024_ge100_completed.csv"
)
OUT = ROOT / "outputs/geography_validation_ge50_2026-07-24"
COMPLETED = OUT / "geography_manual_review_ge20_2024_ge50_completed.csv"
EVIDENCE = OUT / "ge50_manual_validation_evidence.csv"
PREIMPORT = OUT / "ge50_preimport_validation.md"
ACCESS_DATE = "2026-07-24"
GBA = "https://qb-referenzdatenbank.g-ba.de/api/download/{site_id}-2024-xml.pdf"
CACHE = "data/cache/geocode/tips_8-839-8_geocode_cache.csv"
NOMINATIM_MAGDEBURG = (
    "https://nominatim.openstreetmap.org/search?"
    "q=Leipziger+Straße+44%2C+39120+Magdeburg%2C+Germany&format=jsonv2&limit=1"
)


ROWS = [
    {
        "site_id": "260612124-772858000",
        "verified_site_name": "Universitätsmedizin Frankfurt, Hauptcampus",
        "verified_address": "Theodor-Stern-Kai 7, 60590 Frankfurt am Main",
        "verified_postcode": "60590", "verified_city": "Frankfurt am Main",
        "verified_federal_state": "Hessen",
        "verified_latitude": "50.0952039", "verified_longitude": "8.6611054",
        "official_source_url": "https://www.unimedizin-ffm.de/einrichtungen/kliniken/zentrum-der-radiologie/diagnostische-und-interventionelle-radiologie/anfahrt",
        "notes": "Official interventional-radiology directions identify the Theodor-Stern-Kai campus; the cached exact-address point lies on that campus.",
    },
    {
        "site_id": "260320597-771519000",
        "verified_site_name": "Medizinische Hochschule Hannover, Hauptcampus",
        "verified_address": "Carl-Neuberg-Straße 1, 30625 Hannover",
        "verified_postcode": "30625", "verified_city": "Hannover",
        "verified_federal_state": "Niedersachsen",
        "verified_latitude": "52.3842111", "verified_longitude": "9.8027950",
        "official_source_url": "https://www.mh-hannover.de/homepages/Info/2019_26_06_a4_Flyer_FB.pdf",
        "notes": "Official MHH campus plan identifies Carl-Neuberg-Straße 1 and the main hospital campus; the cached exact-address point lies on it.",
    },
    {
        "site_id": "260102343-773447000",
        "verified_site_name": "Universitätsklinikum Schleswig-Holstein, Campus Lübeck",
        "verified_address": "Ratzeburger Allee 160, 23538 Lübeck",
        "verified_postcode": "23538", "verified_city": "Lübeck",
        "verified_federal_state": "Schleswig-Holstein",
        "verified_latitude": "53.8387592", "verified_longitude": "10.7078632",
        "official_source_url": "https://www.iem.uni-luebeck.de/en/contact/",
        "notes": "Official UKSH-affiliated institute directions explicitly identify Campus Lübeck at this address; the site identifier is distinct from the already validated Kiel campus.",
    },
    {
        "site_id": "260310378-772918000",
        "verified_site_name": "Universitätsmedizin Göttingen, Hauptgebäude",
        "verified_address": "Robert-Koch-Straße 40, 37075 Göttingen",
        "verified_postcode": "37075", "verified_city": "Göttingen",
        "verified_federal_state": "Niedersachsen",
        "verified_latitude": "51.5493820", "verified_longitude": "9.9443011",
        "official_source_url": "https://radiologie.umg.eu/kontakt-anfahrt/",
        "notes": "Official diagnostic/interventional-radiology contact page identifies the UMG main building at this address.",
    },
    {
        "site_id": "260530283-773491000",
        "verified_site_name": "Uniklinik Köln, Hauptcampus",
        "verified_address": "Kerpener Straße 62, 50937 Köln",
        "verified_postcode": "50937", "verified_city": "Köln",
        "verified_federal_state": "Nordrhein-Westfalen",
        "verified_latitude": "50.9235258", "verified_longitude": "6.9192613",
        "official_source_url": "https://www.uk-koeln.de/uniklinik-koeln/kontakt/",
        "notes": "Official hospital contact page identifies the Kerpener Straße main campus; the cached exact-address point lies on it.",
    },
    {
        "site_id": "260913195-772053000",
        "verified_site_name": "TUM Klinikum Rechts der Isar",
        "verified_address": "Ismaninger Straße 22, 81675 München",
        "verified_postcode": "81675", "verified_city": "München",
        "verified_federal_state": "Bayern",
        "verified_latitude": "48.1378387", "verified_longitude": "11.6015956",
        "official_source_url": "https://radiologie.mri.tum.de/en/node/3194",
        "notes": "Official diagnostic/interventional-radiology page identifies the Rechts der Isar campus at this address.",
    },
    {
        "site_id": "260510381-771967000",
        "verified_site_name": "Universitätsklinikum Essen, Hauptcampus",
        "verified_address": "Hufelandstraße 55, 45147 Essen",
        "verified_postcode": "45147", "verified_city": "Essen",
        "verified_federal_state": "Nordrhein-Westfalen",
        "verified_latitude": "51.4331571", "verified_longitude": "6.9882830",
        "official_source_url": "https://www.uk-essen.de/impressum/",
        "notes": "Official hospital imprint confirms the physical Hufelandstraße address; spelling is expanded but the baseline address is substantively unchanged.",
    },
    {
        "site_id": "261400847-771139000",
        "verified_site_name": "Helios Park-Klinikum Leipzig",
        "verified_address": "Strümpellstraße 41, 04289 Leipzig",
        "verified_postcode": "04289", "verified_city": "Leipzig",
        "verified_federal_state": "Sachsen",
        "verified_latitude": "51.3080037", "verified_longitude": "12.4369348",
        "official_source_url": "https://www.helios-gesundheit.de/standorte-angebote/kliniken/leipzig/aufenthalt/kontakt-anfahrt/",
        "notes": "Official hospital directions identify the Park-Klinikum physical site; the cached exact-address point lies on it.",
    },
    {
        "site_id": "260970015-772997000",
        "verified_site_name": "Universitätsklinikum Augsburg, Standort Stenglinstraße",
        "verified_address": "Stenglinstraße 2, 86156 Augsburg",
        "verified_postcode": "86156", "verified_city": "Augsburg",
        "verified_federal_state": "Bayern",
        "verified_latitude": "48.3848965", "verified_longitude": "10.8396834",
        "official_source_url": "https://www.uk-augsburg.de/en/arrival",
        "notes": "Official directions identify the Stenglinstraße clinical campus; abbreviation is expanded but the baseline address is substantively unchanged.",
    },
    {
        "site_id": "261500289-773667000",
        "verified_site_name": "Universitätsklinikum Magdeburg, Campus Leipziger Straße",
        "verified_address": "Leipziger Straße 44, 39120 Magdeburg",
        "verified_postcode": "39120", "verified_city": "Magdeburg",
        "verified_federal_state": "Sachsen-Anhalt",
        "verified_latitude": "52.1041758", "verified_longitude": "11.6201463",
        "official_source_url": "https://krn.med.ovgu.de/Kontakt.html",
        "notes": "Corrected the duplicated house number in the baseline. The original cached point lies within the official hospital campus and within the bounding box returned by a serial exact corrected-address Nominatim query, so the coordinate is retained.",
        "address_changed": True,
    },
    {
        "site_id": "261000386-771261000",
        "verified_site_name": "Universitätsklinikum des Saarlandes, Campus Homburg",
        "verified_address": "Kirrberger Straße 100, 66421 Homburg",
        "verified_postcode": "66421", "verified_city": "Homburg",
        "verified_federal_state": "Saarland",
        "verified_latitude": "49.3062191", "verified_longitude": "7.3464925",
        "official_source_url": "https://www.uks.eu/mit-dem-eigenen-pkw",
        "notes": "Official UKS directions confirm the campus-only postcode 66421 and explain the alternative navigation postcode; the cached point is on the Homburg campus.",
    },
    {
        "site_id": "261300118-771003000",
        "verified_site_name": "Klinikum Südstadt Rostock",
        "verified_address": "Südring 81, 18059 Rostock",
        "verified_postcode": "18059", "verified_city": "Rostock",
        "verified_federal_state": "Mecklenburg-Vorpommern",
        "verified_latitude": "54.0717274", "verified_longitude": "12.1066615",
        "official_source_url": "https://www.kliniksued-rostock.de/patienten-besucher/kontakt-anfahrt.html",
        "notes": "Official hospital contact and directions page confirms this distinct Südstadt physical site.",
    },
    {
        "site_id": "261300425-773084000",
        "verified_site_name": "Universitätsmedizin Rostock, Campus Schillingallee",
        "verified_address": "Schillingallee 35, 18057 Rostock",
        "verified_postcode": "18057", "verified_city": "Rostock",
        "verified_federal_state": "Mecklenburg-Vorpommern",
        "verified_latitude": "54.0857050", "verified_longitude": "12.1014711",
        "official_source_url": "https://radiologie.med.uni-rostock.de/patienten-besucher/standorte",
        "notes": "Official radiology location page identifies Campus Schillingallee, distinct from Klinikum Südstadt.",
    },
    {
        "site_id": "260840108-772041000",
        "verified_site_name": "Universitätsklinikum Tübingen",
        "verified_address": "Geissweg 3, 72076 Tübingen",
        "verified_postcode": "72076", "verified_city": "Tübingen",
        "verified_federal_state": "Baden-Württemberg",
        "verified_latitude": "48.5277394", "verified_longitude": "9.0489311",
        "official_source_url": "https://www.medizin.uni-tuebingen.de/de/kontakt/impressum",
        "notes": "Official UKT imprint confirms the address and IK; the 2024 G-BA report explicitly ties site identifier 772041000 to the same address. UKT has distributed clinical buildings, but no conflicting site identity was found.",
    },
    {
        "site_id": "260810271-772311000",
        "verified_site_name": "Robert Bosch Krankenhaus, Hauptstandort",
        "verified_address": "Auerbachstraße 110, 70376 Stuttgart",
        "verified_postcode": "70376", "verified_city": "Stuttgart",
        "verified_federal_state": "Baden-Württemberg",
        "verified_latitude": "48.8143238", "verified_longitude": "9.1872156",
        "official_source_url": "https://www.rbk.de/kontakt",
        "notes": "Official contact page distinguishes the Auerbachstraße main hospital from the separate City location and confirms this physical site.",
    },
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(SOURCE, dtype=str).fillna("")
    completed = source.copy()
    evidence_rows = []
    by_id = {row["site_id"]: row for row in ROWS}
    priority_ids = set(
        completed.loc[completed.manual_review_priority == "2", "site_id"]
    )
    if priority_ids != set(by_id):
        raise SystemExit("Priority-2 identifiers do not match the fixed validation set")

    for index, row in completed.iterrows():
        site_id = row["site_id"]
        if site_id not in by_id:
            continue
        item = by_id[site_id]
        address_changed = bool(item.get("address_changed", False))
        coordinate_changed = bool(item.get("coordinate_changed", False))
        gba_url = GBA.format(site_id=site_id)
        sources = f"{item['official_source_url']}; {gba_url}"
        manual_source = f"{CACHE}; {item['official_source_url']}"
        if site_id == "261500289-773667000":
            manual_source = (
                f"{CACHE}; {NOMINATIM_MAGDEBURG}; {item['official_source_url']}"
            )

        completed.at[index, "manual_status"] = "validated"
        completed.at[index, "address_confirmation"] = "validated"
        completed.at[index, "federal_state_confirmation"] = "validated"
        completed.at[index, "coordinate_confirmation"] = "validated"
        completed.at[index, "evidence_source"] = sources
        completed.at[index, "manual_federal_state"] = item["verified_federal_state"]
        completed.at[index, "manual_source"] = manual_source
        completed.at[index, "manual_notes"] = item["notes"]
        completed.at[index, "review_notes"] = item["notes"]
        if address_changed:
            completed.at[index, "manual_address"] = item["verified_address"]
            completed.at[index, "manual_postcode"] = item["verified_postcode"]
        if coordinate_changed:
            completed.at[index, "manual_latitude"] = item["verified_latitude"]
            completed.at[index, "manual_longitude"] = item["verified_longitude"]

        evidence_rows.append({
            "ik": row["ik"], "site_id": site_id,
            "provider_name": row["provider_name"],
            "visible_activity": row["visible_activity"],
            "verified_site_name": item["verified_site_name"],
            "verified_address": item["verified_address"],
            "verified_postcode": item["verified_postcode"],
            "verified_city": item["verified_city"],
            "verified_federal_state": item["verified_federal_state"],
            "verified_latitude": item["verified_latitude"],
            "verified_longitude": item["verified_longitude"],
            "address_changed": address_changed,
            "coordinate_changed": coordinate_changed,
            "official_source_url": item["official_source_url"],
            "secondary_source_url": gba_url,
            "source_access_date": ACCESS_DATE,
            "validation_decision": "validated",
            "notes": item["notes"],
        })

    unchanged = completed.manual_review_priority != "2"
    if not source.loc[unchanged].equals(completed.loc[unchanged]):
        raise SystemExit("A non-Priority-2 row changed")
    evidence = pd.DataFrame(evidence_rows)
    completed.to_csv(COMPLETED, index=False)
    evidence.to_csv(EVIDENCE, index=False)

    reviewed = completed[completed.manual_review_priority == "2"]
    states = gpd.read_file(ROOT / "spatial/germany-states.geojson").to_crs("EPSG:4326")
    points = gpd.GeoDataFrame(
        evidence[["site_id", "verified_federal_state"]].copy(),
        geometry=gpd.points_from_xy(
            evidence.verified_longitude.astype(float),
            evidence.verified_latitude.astype(float),
        ),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(
        points,
        states.rename(columns={"NAME_1": "coordinate_state"})[
            ["coordinate_state", "geometry"]
        ],
        how="left",
        predicate="within",
    )
    checks = {
        "Priority-2 rows reviewed": len(reviewed) == 15,
        "Priority-1 rows unchanged": source.loc[
            source.manual_review_priority == "1"
        ].equals(completed.loc[completed.manual_review_priority == "1"]),
        "Priority-3 rows unchanged": source.loc[
            source.manual_review_priority == "3"
        ].equals(completed.loc[completed.manual_review_priority == "3"]),
        "Identifiers unchanged": source.site_id.equals(completed.site_id),
        "Visible activity unchanged": source.visible_activity.equals(
            completed.visible_activity
        ),
        "Accepted confirmations complete": reviewed[
            [
                "address_confirmation",
                "federal_state_confirmation",
                "coordinate_confirmation",
            ]
        ].eq("validated").all().all(),
        "Mandatory evidence complete": reviewed.evidence_source.str.strip().ne("").all(),
        "Evidence rows complete": len(evidence) == 15
        and evidence.validation_decision.eq("validated").all(),
        "Complete postcodes": evidence.verified_postcode.str.fullmatch(r"\d{5}").all(),
        "Complete cities": evidence.verified_city.str.strip().ne("").all(),
        "Coordinate pairs complete": evidence[
            ["verified_latitude", "verified_longitude"]
        ].notna().all().all(),
        "No reviewed coordinate duplicates": not evidence[
            ["verified_latitude", "verified_longitude"]
        ].duplicated().any(),
        "State-coordinate consistency": joined.coordinate_state.eq(
            joined.verified_federal_state
        ).all(),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit("Pre-import QC failed: " + "; ".join(failed))
    check_lines = "\n".join(
        f"- [{'x' if passed else ' '}] {name}" for name, passed in checks.items()
    )
    PREIMPORT.write_text(
        "# ≥50 pre-import validation\n\n"
        f"{check_lines}\n\n"
        "All 15 Priority-2 sites have traceable official evidence. The one address "
        "correction removes the duplicated Magdeburg house number. No coordinate "
        "correction is required: all retained points lie at the verified hospital "
        "campus, have no unexplained duplicate, and agree with the documented "
        "federal state. Import may proceed.\n",
        encoding="utf-8",
    )
    print(f"Wrote {COMPLETED}")
    print(f"Wrote {EVIDENCE}")
    print(f"Wrote {PREIMPORT}")


if __name__ == "__main__":
    main()
