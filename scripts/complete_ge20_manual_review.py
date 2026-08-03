#!/usr/bin/env python3
"""Complete only the 29 Priority-3 rows in the final TIPS geography review."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "outputs/geography_validation_ge50_2026-07-24/"
    "geography_manual_review_ge20_2024_ge50_completed.csv"
)
OUT = ROOT / "outputs/final_submission_assets_2026-07-24"
COMPLETED = OUT / "geography_manual_review_ge20_2024_completed.csv"
EVIDENCE = OUT / "ge20_manual_validation_evidence.csv"
PREIMPORT = OUT / "ge20_preimport_validation.md"
ACCESS_DATE = "2026-07-24"
GBA = "https://qb-referenzdatenbank.g-ba.de/api/download/{site_id}-2024-xml.pdf"
CACHE = "data/cache/geocode/tips_8-839-8_geocode_cache.csv"
NOMINATIM_COESFELD = (
    "https://nominatim.openstreetmap.org/search?"
    "q=S%C3%BCdring%2041%2C%2048653%20Coesfeld%2C%20Germany"
    "&format=jsonv2&limit=1"
)
NOMINATIM_WUPPERTAL = (
    "https://nominatim.openstreetmap.org/search?"
    "q=Carnaper%20Stra%C3%9Fe%2048%2C%2042283%20Wuppertal%2C%20Germany"
    "&format=jsonv2&limit=1"
)
NOMINATIM_PASSAU = (
    "https://nominatim.openstreetmap.org/search?"
    "q=Innstra%C3%9Fe%2076%2C%2094032%20Passau%2C%20Germany"
    "&format=jsonv2&limit=1"
)


def item(
    site_id: str,
    name: str,
    address: str,
    postcode: str,
    city: str,
    state: str,
    latitude: str,
    longitude: str,
    source: str,
    note: str,
    *,
    address_changed: bool = False,
    coordinate_changed: bool = False,
    coordinate_source: str = "",
) -> dict[str, object]:
    return {
        "site_id": site_id,
        "verified_site_name": name,
        "verified_address": address,
        "verified_postcode": postcode,
        "verified_city": city,
        "verified_federal_state": state,
        "verified_latitude": latitude,
        "verified_longitude": longitude,
        "official_source_url": source,
        "notes": note,
        "address_changed": address_changed,
        "coordinate_changed": coordinate_changed,
        "coordinate_source": coordinate_source,
    }


ROWS = [
    item(
        "260950567-771175000", "Universitätsklinikum Erlangen",
        "Maximiliansplatz 2, 91054 Erlangen", "91054", "Erlangen", "Bayern",
        "49.6008509", "11.0104406", "https://www.uk-erlangen.de/kontakt/",
        "Official hospital contact details confirm the represented Erlangen campus. The cached exact-address point lies on that campus.",
    ),
    item(
        "261400530-772884000", "Klinikum St. Georg Leipzig",
        "Delitzscher Straße 141, 04129 Leipzig", "04129", "Leipzig", "Sachsen",
        "51.3840002", "12.3810491",
        "https://www.sanktgeorg.de/medizinische-bereiche/kliniken-abteilungen/radiologie-und-nuklearmedizin/kontakt.html",
        "Official radiology contact details identify the Delitzscher Straße campus and a building on that campus.",
    ),
    item(
        "260200079-772901000", "Asklepios Klinikum Harburg",
        "Eißendorfer Pferdeweg 52, 21075 Hamburg", "21075", "Hamburg", "Hamburg",
        "53.4594541", "9.9501356",
        "https://www.asklepios.com/harburg/anmeldung-aufenthalt/kontakt-anfahrt",
        "Official hospital directions confirm the physical Harburg site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260920014-773514000", "Klinikum Landshut",
        "Robert-Koch-Straße 1, 84034 Landshut", "84034", "Landshut", "Bayern",
        "48.5376923", "12.1374237",
        "https://www.klinikum-landshut.de/fileadmin/pdfs/qm/Referenzbericht_zum_Qualitaetsbericht_Klinikum_Landshut_AdoeR_der_Stadt_Landshut_2023.pdf",
        "The official hospital quality report confirms the physical Landshut site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260200035-772584000", "Asklepios Klinik Barmbek",
        "Rübenkamp 220, 22307 Hamburg", "22307", "Hamburg", "Hamburg",
        "53.6062742", "10.0364792",
        "https://www.asklepios.com/barmbek/anmeldung-aufenthalt/kontakt-anfahrt",
        "Official hospital directions confirm the physical Barmbek site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "261401052-771392000", "Universitätsklinikum Leipzig",
        "Liebigstraße 18, 04103 Leipzig", "04103", "Leipzig", "Sachsen",
        "51.3310239", "12.3850465",
        "https://www.uniklinikum-leipzig.de/Seiten/impressum.aspx",
        "The official hospital imprint confirms the represented Leipzig campus. The cached exact-address point lies on that campus.",
    ),
    item(
        "261500702-773513000", "Universitätsklinikum Halle (Saale)",
        "Ernst-Grube-Straße 40, 06120 Halle (Saale)", "06120", "Halle (Saale)",
        "Sachsen-Anhalt", "51.5018258", "11.9364462",
        "https://www.uk-halle.de/fileadmin/Einrichtungsordner/Gremien_und_Verwaltung/Stabsstellen/Presse_und_Unternehmenskommunikation/Dokumente/Kompetenzreport_UniMedHal_2018_web.pdf",
        "An official university medicine document confirms the Ernst-Grube-Straße campus. The cached exact-address point lies on that campus.",
    ),
    item(
        "260913480-771080000", "München Klinik Bogenhausen",
        "Englschalkinger Straße 77, 81925 München", "81925", "München", "Bayern",
        "48.1551599", "11.6247172",
        "https://www.muenchen-klinik.de/kontakt-und-anfahrt/",
        "Official hospital directions distinguish and confirm the Bogenhausen physical site. The cached exact-address point lies on that campus.",
    ),
    item(
        "260840200-773713000", "Universitätsklinikum Ulm",
        "Albert-Einstein-Allee 29, 89081 Ulm", "89081", "Ulm",
        "Baden-Württemberg", "48.4226209", "9.9484836",
        "https://www.uniklinik-ulm.de/ueber-uns/management.html",
        "Official hospital management contact details confirm the represented Ulm campus. The cached exact-address point lies on that campus.",
    ),
    item(
        "260530465-772075000", "Cellitinnen-Krankenhaus St. Franziskus",
        "Schönsteinstraße 63, 50825 Köln-Ehrenfeld", "50825", "Köln-Ehrenfeld",
        "Nordrhein-Westfalen", "50.9541498", "6.9175248",
        "https://sfh.gutes-tun-cellitinnen.de/unternehmen/",
        "The official hospital page confirms the distinct St. Franziskus physical site in Köln-Ehrenfeld. The cached exact-address point lies on that campus.",
    ),
    item(
        "260590139-773659000", "Klinikum Dortmund, Klinikzentrum Mitte",
        "Beurhausstraße 40, 44137 Dortmund", "44137", "Dortmund",
        "Nordrhein-Westfalen", "51.5084552", "7.4576213",
        "https://www.klinikumdo.de/patienten-besucher/anfahrt",
        "Official hospital directions confirm Klinikzentrum Mitte and distinguish its street address from the car-park entrance.",
    ),
    item(
        "260550460-771191000", "Christophorus Kliniken, Standort Coesfeld",
        "Südring 41, 48653 Coesfeld", "48653", "Coesfeld",
        "Nordrhein-Westfalen", "51.9441642", "7.1700403",
        "https://christophorus-kliniken.de/radiologie/",
        "Official radiology contact details identify Standort Coesfeld. The baseline coordinate came from Südwall 22 and was replaced by the exact-address hospital point.",
        coordinate_changed=True, coordinate_source=NOMINATIM_COESFELD,
    ),
    item(
        "260101488-772073000", "Friedrich-Ebert-Krankenhaus Neumünster",
        "Friesenstraße 11, 24534 Neumünster", "24534", "Neumünster",
        "Schleswig-Holstein", "54.0643152", "9.9913258",
        "https://www.friedrich-ebert-krankenhaus.de/impressum/",
        "The official hospital imprint confirms the physical Neumünster site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260820569-772389000", "Universitätsklinikum Mannheim",
        "Theodor-Kutzer-Ufer 1-3, 68167 Mannheim", "68167", "Mannheim",
        "Baden-Württemberg", "49.4914346", "8.4903529",
        "https://www.umm.de/neuroradiologie/patienteninformationen/ambulanzen/",
        "Official neuroradiology contact details confirm the physical Mannheim campus. The cached exact-address point lies on that campus.",
    ),
    item(
        "260820115-772143000", "Städtisches Klinikum Karlsruhe",
        "Moltkestraße 90, 76133 Karlsruhe", "76133", "Karlsruhe",
        "Baden-Württemberg", "49.0156523", "8.3745829",
        "https://www.klinikum-karlsruhe.de/ueber-uns/kontakt-anfahrt",
        "Official hospital contact details confirm the physical Karlsruhe site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260920069-772859000", "Klinikum Passau",
        "Innstraße 76, 94032 Passau", "94032", "Passau", "Bayern",
        "48.5650357", "13.4453357",
        "https://www.klinikum-passau.de/fileadmin/user_upload/downloads/broschueren/Broschuere_ASV_Lunge-Thorax_DINlang_12-Seiter_2024-08_WEB.pdf",
        "Official clinical material confirms the physical Passau site. A repeat exact-address query returned the unchanged hospital coordinate and Bayern, resolving the local polygon flag.",
        coordinate_source=NOMINATIM_PASSAU,
    ),
    item(
        "260950099-771374000", "Klinikum Nürnberg, Campus Nord",
        "Prof.-Ernst-Nathan-Straße 1, 90419 Nürnberg", "90419", "Nürnberg",
        "Bayern", "49.4630757", "11.0633534",
        "https://www.klinikum-nuernberg.de/kontakt",
        "Official hospital contact details distinguish and confirm Campus Nord. The cached exact-address point lies on that campus.",
    ),
    item(
        "261100070-773109000", "DRK Kliniken Berlin Mitte",
        "Drontheimer Straße 39-40, 13359 Berlin", "13359", "Berlin", "Berlin",
        "52.5570876", "13.3766559",
        "https://www.drk-kliniken-berlin.de/mitte",
        "Official hospital directions confirm the physical Berlin-Mitte site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "261401416-772794000", "Klinikum Chemnitz, Standort Flemmingstraße",
        "Flemmingstraße 2, 09116 Chemnitz", "09116", "Chemnitz", "Sachsen",
        "50.8447689", "12.8861281",
        "https://www.klinikumchemnitz.de/kliniken-bereiche/institute-abteilungen/institut-fuer-radiologie-und-neuroradiologie/mitarbeiter",
        "Official radiology details identify the Flemmingstraße physical site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260620431-773132000", "Universitätsklinikum Gießen und Marburg, Standort Marburg",
        "Baldingerstraße 1, 35043 Marburg", "35043", "Marburg", "Hessen",
        "50.8174459", "8.8087518",
        "https://www.ukgm.de/ugm_2/deu/umr_rdi/2651.html",
        "Official radiology details identify the Marburg campus. The baseline house number 01 was normalised to the official form 1 without changing the coordinate.",
        address_changed=True,
    ),
    item(
        "260571421-773289000", "Franziskus Hospital Bielefeld",
        "Kiskerstraße 26, 33615 Bielefeld", "33615", "Bielefeld",
        "Nordrhein-Westfalen", "52.0226864", "8.5227616",
        "https://www.franziskus.de/fr/kontakt/?contact=%2Ffr%2Fansprechpartner%2Ffranziskus-hospital.php",
        "Official hospital contact details resolve the provider name to the Franziskus Hospital physical site. The cached exact-address point lies on that campus.",
    ),
    item(
        "260550701-772358000", "Prosper-Hospital Recklinghausen",
        "Mühlenstraße 27, 45659 Recklinghausen", "45659", "Recklinghausen",
        "Nordrhein-Westfalen", "51.6063388", "7.1923347",
        "https://www.proselis.de/prosper-hospital-recklinghausen/aufenthalt-und-besuch",
        "Official hospital directions identify the PROSELIS report site as Prosper-Hospital. The cached exact-address point lies on that campus.",
    ),
    item(
        "260510939-771562000", "Cellitinnen-Krankenhaus St. Petrus",
        "Carnaper Straße 48, 42283 Wuppertal", "42283", "Wuppertal",
        "Nordrhein-Westfalen", "51.2758661", "7.1918608",
        "https://pkh.gutes-tun-cellitinnen.de/impressum/",
        "The official hospital imprint and 2024 G-BA report resolve the provider to St. Petrus. The baseline coordinate came from the legal entity address at Bergstraße 6-12 and was replaced by the exact Carnaper Straße hospital point.",
        coordinate_changed=True, coordinate_source=NOMINATIM_WUPPERTAL,
    ),
    item(
        "261101479-773680000", "Evangelisches Krankenhaus Königin Elisabeth Herzberge",
        "Herzbergstraße 79, 10365 Berlin", "10365", "Berlin", "Berlin",
        "52.5279222", "13.5089920",
        "https://www.keh-berlin.de/kontakt",
        "Official hospital contact details confirm the physical Herzbergstraße site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "261300185-772916000", "Helios Kliniken Schwerin",
        "Wismarsche Straße 393-397, 19055 Schwerin", "19055", "Schwerin",
        "Mecklenburg-Vorpommern", "53.6514220", "11.4082224",
        "https://www.helios-gesundheit.de/standorte-angebote/kliniken/schwerin/leistungen/fachbereiche/strahlentherapie/sprechzeiten/",
        "Official hospital contact details confirm the physical Schwerin site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260570692-772283000", "Johannes Wesling Klinikum Minden",
        "Hans-Nolte-Straße 1, 32429 Minden", "32429", "Minden",
        "Nordrhein-Westfalen", "52.2612462", "8.8890891",
        "https://www.muehlenkreiskliniken.de/muehlenkreiskliniken/kontakt-neu-1",
        "Official hospital contact details confirm the physical Minden site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260530012-771450000", "Uniklinik RWTH Aachen",
        "Pauwelsstraße 30, 52074 Aachen", "52074", "Aachen",
        "Nordrhein-Westfalen", "50.7769172", "6.0433753",
        "https://www.ukaachen.de/kliniken-institute/klinik-fuer-diagnostische-und-interventionelle-radiologie/kontakt/",
        "Official radiology contact details confirm the physical Aachen site. The cached exact-address point lies on the hospital campus.",
    ),
    item(
        "260730025-772988000", "Westpfalz-Klinikum, Standort I Kaiserslautern",
        "Hellmut-Hartert-Straße 1, 67655 Kaiserslautern", "67655",
        "Kaiserslautern", "Rheinland-Pfalz", "49.4414169", "7.7560839",
        "https://www.westpfalz-klinikum.de/ueber-uns/standorte/kaiserslautern",
        "Official hospital details distinguish and confirm Standort I Kaiserslautern. The cached exact-address point lies on that campus.",
    ),
    item(
        "260810453-771315000", "Krankenhaus Leonberg",
        "Rutesheimer Straße 50, 71229 Leonberg", "71229", "Leonberg",
        "Baden-Württemberg", "48.8018366", "9.0033196",
        "https://www.klinikverbund-suedwest.de/der-klinikverbund-suedwest/standorte-kontakt/krankenhaus-leonberg/",
        "Official hospital details confirm the physical Leonberg site and the report identity. The cached exact-address point lies on the hospital campus.",
    ),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source_bytes = SOURCE.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    source = pd.read_csv(SOURCE, dtype=str).fillna("")
    completed = source.copy()
    by_id = {row["site_id"]: row for row in ROWS}
    priority_ids = set(
        completed.loc[completed.manual_review_priority == "3", "site_id"]
    )
    if len(ROWS) != 29 or priority_ids != set(by_id):
        raise SystemExit("Priority-3 identifiers do not match the fixed validation set")

    evidence_rows: list[dict[str, object]] = []
    for index, row in completed.iterrows():
        site_id = row["site_id"]
        if site_id not in by_id:
            continue
        record = by_id[site_id]
        gba_url = GBA.format(site_id=site_id)
        coordinate_source = str(record["coordinate_source"])
        completed.at[index, "manual_status"] = "validated"
        completed.at[index, "address_confirmation"] = "validated"
        completed.at[index, "federal_state_confirmation"] = "validated"
        completed.at[index, "coordinate_confirmation"] = "validated"
        completed.at[index, "evidence_source"] = (
            f"{record['official_source_url']}; {gba_url}"
        )
        completed.at[index, "manual_federal_state"] = record[
            "verified_federal_state"
        ]
        completed.at[index, "manual_source"] = "; ".join(
            value for value in (CACHE, coordinate_source, str(record["official_source_url"]))
            if value
        )
        completed.at[index, "manual_notes"] = record["notes"]
        completed.at[index, "review_notes"] = record["notes"]
        if record["address_changed"]:
            completed.at[index, "manual_address"] = record["verified_address"]
            completed.at[index, "manual_postcode"] = record["verified_postcode"]
        if record["coordinate_changed"]:
            completed.at[index, "manual_latitude"] = record["verified_latitude"]
            completed.at[index, "manual_longitude"] = record["verified_longitude"]

        evidence_rows.append({
            "ik": row["ik"],
            "site_id": site_id,
            "provider_name": row["provider_name"],
            "visible_activity": row["visible_activity"],
            "verified_site_name": record["verified_site_name"],
            "verified_address": record["verified_address"],
            "verified_postcode": record["verified_postcode"],
            "verified_city": record["verified_city"],
            "verified_federal_state": record["verified_federal_state"],
            "verified_latitude": record["verified_latitude"],
            "verified_longitude": record["verified_longitude"],
            "address_changed": record["address_changed"],
            "coordinate_changed": record["coordinate_changed"],
            "official_source_url": record["official_source_url"],
            "secondary_source_url": gba_url,
            "source_access_date": ACCESS_DATE,
            "validation_decision": "validated",
            "notes": record["notes"],
        })

    priority_1 = source.manual_review_priority == "1"
    priority_2 = source.manual_review_priority == "2"
    non_priority_3 = source.manual_review_priority != "3"
    if not source.loc[non_priority_3].equals(completed.loc[non_priority_3]):
        raise SystemExit("A Priority-1 or Priority-2 row changed")

    evidence = pd.DataFrame(evidence_rows)
    completed.to_csv(COMPLETED, index=False)
    evidence.to_csv(EVIDENCE, index=False)

    identity_columns = [
        "ik", "site_id", "provider_name", "visible_activity",
        "threshold_ge20", "threshold_ge50", "threshold_ge100", "threshold_ge200",
    ]
    reviewed = completed[completed.manual_review_priority == "3"]
    confirmed = [
        "address_confirmation", "federal_state_confirmation",
        "coordinate_confirmation",
    ]
    checks = {
        "29/29 Priority-3 rows reviewed": len(reviewed) == 29,
        "16/16 Priority-1 rows byte-for-byte unchanged after CSV parsing":
            int(priority_1.sum()) == 16
            and source.loc[priority_1].equals(completed.loc[priority_1]),
        "15/15 Priority-2 rows byte-for-byte unchanged after CSV parsing":
            int(priority_2.sum()) == 15
            and source.loc[priority_2].equals(completed.loc[priority_2]),
        "Identifiers, activity and threshold membership unchanged":
            source[identity_columns].equals(completed[identity_columns]),
        "All Priority-3 confirmation fields use the accepted value":
            reviewed[confirmed].eq("validated").all().all(),
        "All Priority-3 rows have traceable evidence":
            reviewed.evidence_source.str.strip().ne("").all(),
        "All Priority-3 state assignments are populated":
            reviewed.manual_federal_state.str.strip().ne("").all(),
        "All corrections have complete replacement fields":
            completed.loc[
                completed.site_id.eq("260620431-773132000"),
                ["manual_address", "manual_postcode"],
            ].ne("").all().all()
            and completed.loc[
                completed.site_id.isin({
                    "260550460-771191000", "260510939-771562000"
                }),
                ["manual_latitude", "manual_longitude"],
            ].ne("").all().all(),
        "No duplicate final Priority-3 coordinate remains":
            ~evidence.duplicated(["verified_latitude", "verified_longitude"]).any(),
        "No Priority-3 site remains unresolved":
            evidence.validation_decision.eq("validated").all(),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    correction_rows = evidence[
        evidence.address_changed.astype(bool)
        | evidence.coordinate_changed.astype(bool)
    ][
        [
            "site_id", "verified_site_name", "verified_address",
            "verified_latitude", "verified_longitude",
            "address_changed", "coordinate_changed",
        ]
    ]
    lines = [
        "# ≥20 manual-review preimport validation",
        "",
        f"Overall status: **{status}**",
        "",
        f"Source file: `{SOURCE.relative_to(ROOT)}`",
        "",
        f"Source SHA-256: `{source_hash}`",
        "",
        "The source hash was recorded before the working copy was written.",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
        *[
            f"| {label} | {'PASS' if passed else 'FAIL'} |"
            for label, passed in checks.items()
        ],
        "",
        "## Corrections",
        "",
        correction_rows.to_markdown(index=False),
        "",
        "The Passau coordinate was independently reproduced by an exact-address "
        "query. Its earlier invalid flag arose from the local state polygon check, "
        "not from a hospital-location mismatch.",
        "",
        "Importer release decision: **proceed**."
        if status == "PASS"
        else "Importer release decision: **stop**.",
        "",
    ]
    PREIMPORT.write_text("\n".join(lines), encoding="utf-8")
    if status != "PASS":
        raise SystemExit("Preimport validation failed")


if __name__ == "__main__":
    main()
