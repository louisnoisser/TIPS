"""Shared G-BA XML parsing helpers."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

REPORT_RE = re.compile(r"-xml\.xml$", re.IGNORECASE)
YEAR_DIR_RE = re.compile(r"xml_(\d{4})$")

DIAGNOSIS_PATTERNS = [
    ".//Hauptdiagnose",
    ".//MainDiagnosis",
    ".//Diagnosis",
    ".//Diagnose",
]
DIAGNOSIS_CODE_NAMES = ["ICD_10", "ICD10", "ICD", "Code", "Diagnoseschluessel"]
PROCEDURE_PATTERNS = [
    ".//Prozedur",
    ".//Procedure",
    ".//OPS_Prozedur",
    ".//Leistung",
    ".//Behandlung",
]
PROCEDURE_CODE_NAMES = ["OPS_301", "OPS301", "OPS_Code", "OPS", "Code", "Prozedurenschluessel"]
COUNT_NAMES = ["Fallzahl", "Anzahl", "Count", "Cases", "Faelle"]

CONTACT_PATHS = [
    ".//Kontaktdaten",
    ".//Krankenhauskontaktdaten",
    ".//Standortkontaktdaten",
    ".//Krankenhaus/Mehrere_Standorte/Krankenhauskontaktdaten",
    ".//Krankenhaus/Mehrere_Standorte/Standortkontaktdaten",
    ".//Krankenhaus/Kontaktdaten",
    ".//Einziger_Standort/Kontaktdaten",
]


def discover_year_dirs(base_dir: Path) -> list[Path]:
    year_dirs: list[tuple[int, Path]] = []
    for path in base_dir.iterdir():
        if not path.is_dir():
            continue
        match = YEAR_DIR_RE.fullmatch(path.name)
        if match:
            year_dirs.append((int(match.group(1)), path))
    return [path for _, path in sorted(year_dirs)]


def report_files(xml_dir: Path, pattern: str = "*-xml.xml") -> list[Path]:
    return sorted(
        path
        for path in xml_dir.glob(pattern)
        if path.is_file() and path.suffix.lower() == ".xml" and REPORT_RE.search(path.name)
    )


def safe_find_text(element: ET.Element | None, xpath: str, default: str = "") -> str:
    if element is None:
        return default
    try:
        found = element.find(xpath)
    except Exception:
        return default
    if found is None or found.text is None:
        return default
    text = found.text.strip()
    return text if text else default


def find_first_text(element: ET.Element, names: list[str]) -> str:
    for name in names:
        found = element.find(name)
        if found is not None and found.text:
            text = found.text.strip()
            if text:
                return text
    return ""


def find_first_int(element: ET.Element, names: list[str]) -> int:
    for name in names:
        found = element.find(name)
        if found is None or found.text is None:
            continue
        try:
            return int(found.text.strip())
        except ValueError:
            continue
    return 0


def parse_file_identity(file_path: Path, fallback_year: int | None = None) -> tuple[str, str, int | None]:
    parts = file_path.stem.split("-")
    ik = parts[0] if parts else ""
    standortnummer = parts[1] if len(parts) > 1 else ""
    year = fallback_year
    if len(parts) >= 3 and parts[2].isdigit():
        year = int(parts[2])
    return ik, standortnummer, year


def extract_contact_info(root: ET.Element) -> dict[str, str]:
    info = {
        "hospital_name": "",
        "city": "",
        "postal_code": "",
        "street": "",
        "house_number": "",
        "phone": "",
        "email": "",
    }

    contact = None
    for path in CONTACT_PATHS:
        contact = root.find(path)
        if contact is not None:
            break

    if contact is None:
        return info

    info["hospital_name"] = (
        safe_find_text(root, ".//Krankenhaus_Name")
        or safe_find_text(root, ".//Name_Krankenhaus")
        or safe_find_text(root, ".//Krankenhaus/Name")
        or safe_find_text(contact, ".//Name")
        or safe_find_text(contact, "n")
    )
    info["city"] = (
        safe_find_text(contact, ".//Ort")
        or safe_find_text(contact, "Hausanschrift/Ort")
        or safe_find_text(contact, "Kontakt_Zugang/Ort")
        or safe_find_text(contact, "Kontakt_Adresse/Ort")
        or safe_find_text(contact, "Kontakt_Adresse/Adresse/Ort")
    )
    info["postal_code"] = (
        safe_find_text(contact, ".//Postleitzahl")
        or safe_find_text(contact, "Hausanschrift/Postleitzahl")
        or safe_find_text(contact, "Kontakt_Zugang/Postleitzahl")
        or safe_find_text(contact, "Kontakt_Adresse/Postleitzahl")
        or safe_find_text(contact, "Kontakt_Adresse/Adresse/Postleitzahl")
    )
    info["street"] = (
        safe_find_text(contact, ".//Strasse")
        or safe_find_text(contact, "Hausanschrift/Strasse")
        or safe_find_text(contact, "Kontakt_Zugang/Strasse")
        or safe_find_text(contact, "Kontakt_Adresse/Strasse")
        or safe_find_text(contact, "Kontakt_Adresse/Adresse/Strasse")
    )
    info["house_number"] = (
        safe_find_text(contact, ".//Hausnummer")
        or safe_find_text(contact, "Hausanschrift/Hausnummer")
        or safe_find_text(contact, "Kontakt_Zugang/Hausnummer")
        or safe_find_text(contact, "Kontakt_Adresse/Hausnummer")
        or safe_find_text(contact, "Kontakt_Adresse/Adresse/Hausnummer")
    )

    vorwahl = safe_find_text(contact, ".//Telefon/Vorwahl")
    rufnummer = safe_find_text(contact, ".//Telefon/Rufnummer")
    durchwahl = safe_find_text(contact, ".//Telefon/Durchwahl")
    if vorwahl and rufnummer:
        info["phone"] = f"{vorwahl}-{rufnummer}" + (f"-{durchwahl}" if durchwahl else "")
    info["email"] = safe_find_text(contact, ".//Email")
    return info


def iter_diagnosis_counts(root: ET.Element) -> Iterable[tuple[str, int]]:
    for pattern in DIAGNOSIS_PATTERNS:
        for diagnosis in root.findall(pattern):
            code = find_first_text(diagnosis, DIAGNOSIS_CODE_NAMES)
            cases = find_first_int(diagnosis, COUNT_NAMES)
            if code and cases > 0:
                yield code.strip(), cases


def iter_procedure_counts(root: ET.Element) -> Iterable[tuple[str, int]]:
    for pattern in PROCEDURE_PATTERNS:
        for procedure in root.findall(pattern):
            code = find_first_text(procedure, PROCEDURE_CODE_NAMES)
            cases = find_first_int(procedure, COUNT_NAMES)
            if code and cases > 0:
                yield code.strip(), cases


def aggregate_counts(pairs: Iterable[tuple[str, int]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for code, cases in pairs:
        counts[code] = counts.get(code, 0) + int(cases)
    return counts


def code_in_range(code: str, start_code: str, end_code: str) -> bool:
    if not code:
        return False
    base_code = code.split(".")[0]
    try:
        prefix = "".join(ch for ch in base_code if ch.isalpha())
        number = int("".join(ch for ch in base_code if ch.isdigit()))
        start_prefix = "".join(ch for ch in start_code if ch.isalpha())
        start_number = int("".join(ch for ch in start_code if ch.isdigit()))
        end_prefix = "".join(ch for ch in end_code if ch.isalpha())
        end_number = int("".join(ch for ch in end_code if ch.isdigit()))
    except ValueError:
        return False
    return prefix == start_prefix == end_prefix and start_number <= number <= end_number


def build_full_address(parts: dict[str, str]) -> str:
    street_bits = " ".join(
        bit.strip()
        for bit in (parts.get("street", ""), parts.get("house_number", ""))
        if bit and bit.strip()
    ).strip()
    city_bits = " ".join(
        bit.strip()
        for bit in (parts.get("postal_code", ""), parts.get("city", ""))
        if bit and bit.strip()
    ).strip()
    return ", ".join(bit for bit in (street_bits, city_bits) if bit)
