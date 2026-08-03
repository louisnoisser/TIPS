#!/usr/bin/env python3
"""Create the reproducible, Priority-1-only TIPS geography review files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/geography_validation_2026-07-24/geography_manual_review_ge20_2024.csv"
OUT = ROOT / "outputs/geography_validation_ge100_2026-07-24"
COMPLETED = OUT / "geography_manual_review_ge20_2024_ge100_completed.csv"
EVIDENCE = OUT / "ge100_manual_validation_evidence.csv"
ACCESS_DATE = "2026-07-24"
GBA = "https://qb-referenzdatenbank.g-ba.de/api/download/{site_id}-2024-xml.pdf"
CACHE = "data/cache/geocode/tips_8-839-8_geocode_cache.csv"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


ROWS = [
    {
        "site_id": "260530103-772247000", "verified_site_name": "Universitätsklinikum Bonn, Venusberg-Campus",
        "verified_address": "Venusberg-Campus 1, 53127 Bonn", "verified_postcode": "53127",
        "verified_city": "Bonn", "verified_federal_state": "Nordrhein-Westfalen",
        "verified_latitude": "50.6957054", "verified_longitude": "7.1048217",
        "official_source_url": "https://www.ukbonn.de/patient_innen/anfahrt-und-lageplan/",
        "notes": "Official campus address exactly matches the cached address query.",
    },
    {
        "site_id": "260510018-773410000", "verified_site_name": "Universitätsklinikum Düsseldorf",
        "verified_address": "Moorenstraße 5, 40225 Düsseldorf", "verified_postcode": "40225",
        "verified_city": "Düsseldorf", "verified_federal_state": "Nordrhein-Westfalen",
        "verified_latitude": "51.1959679", "verified_longitude": "6.7898208",
        "official_source_url": "https://www.uniklinik-duesseldorf.de/patienten-besucher/klinikeninstitutezentren/medizinisches-versorgungszentrum-mvz/anreise",
        "notes": "Official UKD directions identify Moorenstraße 5 as the hospital campus entrance.",
    },
    {
        "site_id": "260930608-771402000", "verified_site_name": "Universitätsklinikum Regensburg",
        "verified_address": "Franz-Josef-Strauß-Allee 11, 93053 Regensburg", "verified_postcode": "93053",
        "verified_city": "Regensburg", "verified_federal_state": "Bayern",
        "verified_latitude": "48.9904494", "verified_longitude": "12.0813806",
        "official_source_url": "https://www.ukr.de/kontakt",
        "notes": "Official UKR contact address exactly matches the cached address query.",
    },
    {
        "site_id": "261101015-772563000", "verified_site_name": "Charité – Universitätsmedizin Berlin, Campus Charité Mitte",
        "verified_address": "Charitéplatz 1, 10117 Berlin", "verified_postcode": "10117",
        "verified_city": "Berlin", "verified_federal_state": "Berlin",
        "verified_latitude": "52.5258523", "verified_longitude": "13.3777575",
        "official_source_url": "https://radiologie.charite.de/metas/lageplan/plan/map/ccm",
        "notes": "The 2024 G-BA identifier uses the CCM house address; the official campus page confirms it. Charité radiology also operates at other campuses.",
    },
    {
        "site_id": "260200013-773675000", "verified_site_name": "Universitätsklinikum Hamburg-Eppendorf, UKE Campus",
        "verified_address": "Martinistraße 52, 20246 Hamburg", "verified_postcode": "20246",
        "verified_city": "Hamburg", "verified_federal_state": "Hamburg",
        "verified_latitude": "53.5918063", "verified_longitude": "9.9725632",
        "official_source_url": "https://www.uke.de/kontakt-uke-hamburg-eppendorf.html",
        "notes": "Official contact address and G-BA address use 20246; UKE separately advises 20251 for navigation systems.",
    },
    {
        "site_id": "260530443-771696000", "verified_site_name": "Cellitinnen-Krankenhaus St. Vinzenz",
        "verified_address": "Merheimer Straße 221-223, 50733 Köln", "verified_postcode": "50733",
        "verified_city": "Köln", "verified_federal_state": "Nordrhein-Westfalen",
        "verified_latitude": "50.9669681", "verified_longitude": "6.9471043",
        "official_source_url": "https://www.vinzenz-hospital.de/ihr-aufenthalt/anfahrt-parken",
        "notes": "Official hospital directions and imprint identify the same physical hospital and IK.",
    },
    {
        "site_id": "260550131-772432000", "verified_site_name": "Universitätsklinikum Münster, Zentralklinikum",
        "verified_address": "Albert-Schweitzer-Campus 1, 48149 Münster", "verified_postcode": "48149",
        "verified_city": "Münster", "verified_federal_state": "Nordrhein-Westfalen",
        "verified_latitude": "51.9607705", "verified_longitude": "7.5959555",
        "official_source_url": "https://www.ukm.de/anfahrt",
        "notes": "Official UKM directions identify the Zentralklinikum at Albert-Schweitzer-Campus 1.",
    },
    {
        "site_id": "260820466-771700000", "verified_site_name": "Universitätsklinikum Heidelberg",
        "verified_address": "Im Neuenheimer Feld 672, 69120 Heidelberg", "verified_postcode": "69120",
        "verified_city": "Heidelberg", "verified_federal_state": "Baden-Württemberg",
        "verified_latitude": "49.4199193", "verified_longitude": "8.6676297",
        "official_source_url": "https://www.klinikum.uni-heidelberg.de/kontakt",
        "notes": "Official hospital contact address exactly matches the cached address query.",
    },
    {
        "site_id": "260832299-773657000", "verified_site_name": "Universitätsklinikum Freiburg",
        "verified_address": "Hugstetter Straße 55, 79106 Freiburg", "verified_postcode": "79106",
        "verified_city": "Freiburg", "verified_federal_state": "Baden-Württemberg",
        "verified_latitude": "48.0060746", "verified_longitude": "7.8411712",
        "official_source_url": "https://www.uniklinik-freiburg.de/kontakt.html",
        "notes": "Official hospital contact address exactly matches the cached address query.",
    },
    {
        "site_id": "260810647-772121000", "verified_site_name": "RKH Klinikum Ludwigsburg",
        "verified_address": "Posilipostraße 4, 71640 Ludwigsburg", "verified_postcode": "71640",
        "verified_city": "Ludwigsburg", "verified_federal_state": "Baden-Württemberg",
        "verified_latitude": "48.8989021", "verified_longitude": "9.2035793",
        "official_source_url": "https://www.rkh-gesundheit.de/klinikum-ludwigsburg/behandlung/zentren/neuroonkologisches-zentrum-ludwigsburg/",
        "notes": "Official RKH clinical page identifies the physical Klinikum Ludwigsburg address.",
    },
    {
        "site_id": "261600736-772874000", "verified_site_name": "Universitätsklinikum Jena, Standort Lobeda",
        "verified_address": "Am Klinikum 1, 07747 Jena", "verified_postcode": "07747",
        "verified_city": "Jena", "verified_federal_state": "Thüringen",
        "verified_latitude": "50.8856144", "verified_longitude": "11.6213180",
        "official_source_url": "https://www.uniklinikum-jena.de/idir/Patienteninformation.html",
        "notes": "Corrected from the administrative report address at Kastanienstraße 1 to the Lobeda clinical campus housing diagnostic/interventional radiology. Coordinate is a serial exact-address Nominatim result.",
        "address_changed": True, "coordinate_changed": True,
    },
    {
        "site_id": "260102343-773448000", "verified_site_name": "Universitätsklinikum Schleswig-Holstein, Campus Kiel",
        "verified_address": "Arnold-Heller-Straße 3, 24105 Kiel", "verified_postcode": "24105",
        "verified_city": "Kiel", "verified_federal_state": "Schleswig-Holstein",
        "verified_latitude": "54.3287985", "verified_longitude": "10.1441819",
        "official_source_url": "https://www.statusplus.uksh.de/impressum",
        "notes": "Corrected cached Lübeck coordinate to the G-BA-identified Campus Kiel address. Coordinate is a serial exact-address Nominatim result.",
        "coordinate_changed": True,
    },
    {
        "site_id": "260914050-771736000", "verified_site_name": "LMU Klinikum, Campus Großhadern",
        "verified_address": "Marchioninistraße 15, 81377 München", "verified_postcode": "81377",
        "verified_city": "München", "verified_federal_state": "Bayern",
        "verified_latitude": "48.1091496", "verified_longitude": "11.4739688",
        "official_source_url": "https://www.lmu-klinikum.de/kardiologie/kontakt-und-anfahrt/cd4018951ac88541",
        "notes": "Official clinical page explicitly identifies Campus Großhadern.",
    },
    {
        "site_id": "260812364-772783000", "verified_site_name": "Klinikum Stuttgart, Katharinenhospital",
        "verified_address": "Kriegsbergstraße 60, 70174 Stuttgart", "verified_postcode": "70174",
        "verified_city": "Stuttgart", "verified_federal_state": "Baden-Württemberg",
        "verified_latitude": "48.7837421", "verified_longitude": "9.1733168",
        "official_source_url": "https://www.klinikum-stuttgart.de/impressum",
        "notes": "Official Klinikum Stuttgart page confirms the Kriegsbergstraße physical address.",
    },
    {
        "site_id": "261401030-773444000", "verified_site_name": "Universitätsklinikum Carl Gustav Carus Dresden",
        "verified_address": "Fetscherstraße 74, 01307 Dresden", "verified_postcode": "01307",
        "verified_city": "Dresden", "verified_federal_state": "Sachsen",
        "verified_latitude": "51.0565116", "verified_longitude": "13.7825779",
        "official_source_url": "https://www.uniklinikum-dresden.de/de/impressum",
        "notes": "Official UKD imprint and clinical directions confirm the physical campus address.",
    },
    {
        "site_id": "260730161-771621000", "verified_site_name": "Universitätsmedizin Mainz",
        "verified_address": "Langenbeckstraße 1, 55131 Mainz", "verified_postcode": "55131",
        "verified_city": "Mainz", "verified_federal_state": "Rheinland-Pfalz",
        "verified_latitude": "49.9942674", "verified_longitude": "8.2565791",
        "official_source_url": "https://www.unimedizin-mainz.de/radioonkologie-und-strahlentherapie/index.html",
        "notes": "Official clinical page and hospital footer confirm the campus address.",
    },
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    original = pd.read_csv(SOURCE, dtype=str).fillna("")
    completed = original.copy()
    evidence_rows = []
    by_id = {row["site_id"]: row for row in ROWS}
    priority_ids = set(completed.loc[completed.manual_review_priority == "1", "site_id"])
    if priority_ids != set(by_id):
        raise SystemExit("Priority-1 identifiers do not match the fixed validation set")

    for index, row in completed.iterrows():
        site_id = row["site_id"]
        if site_id not in by_id:
            continue
        item = by_id[site_id]
        address_changed = bool(item.get("address_changed", False))
        coordinate_changed = bool(item.get("coordinate_changed", False))
        gba_url = GBA.format(site_id=site_id)
        exact_query = (
            f"{NOMINATIM}?q={item['verified_address'].replace(' ', '+')}"
            "&format=jsonv2&limit=1&addressdetails=1"
        )
        evidence_source = f"{item['official_source_url']}; {gba_url}"
        manual_source = exact_query if coordinate_changed else f"{CACHE}; {item['official_source_url']}"
        completed.at[index, "manual_status"] = "validated"
        completed.at[index, "address_confirmation"] = "validated"
        completed.at[index, "federal_state_confirmation"] = "validated"
        completed.at[index, "coordinate_confirmation"] = "validated"
        completed.at[index, "evidence_source"] = evidence_source
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
            "ik": row["ik"], "site_id": site_id, "provider_name": row["provider_name"],
            "visible_activity": row["visible_activity"],
            "verified_site_name": item["verified_site_name"],
            "verified_address": item["verified_address"],
            "verified_postcode": item["verified_postcode"],
            "verified_city": item["verified_city"],
            "verified_federal_state": item["verified_federal_state"],
            "verified_latitude": item["verified_latitude"],
            "verified_longitude": item["verified_longitude"],
            "address_changed": address_changed, "coordinate_changed": coordinate_changed,
            "official_source_url": item["official_source_url"],
            "secondary_source_url": gba_url, "source_access_date": ACCESS_DATE,
            "validation_decision": "validated", "notes": item["notes"],
        })

    unchanged_columns = list(original.columns)
    nonpriority = original.manual_review_priority != "1"
    if not original.loc[nonpriority, unchanged_columns].equals(
        completed.loc[nonpriority, unchanged_columns]
    ):
        raise SystemExit("A non-Priority-1 row changed")
    completed.to_csv(COMPLETED, index=False)
    pd.DataFrame(evidence_rows).to_csv(EVIDENCE, index=False)
    print(f"Wrote {COMPLETED}")
    print(f"Wrote {EVIDENCE}")


if __name__ == "__main__":
    main()
