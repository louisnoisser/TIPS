"""Static web dashboard builder for indication reports."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from . import config

ASSET_DIR = Path(__file__).resolve().parent / "webapp_assets"


def _figure_specs(main_threshold: int, strict_threshold: int) -> list[tuple[str, str, str]]:
    return [
        ("01_yearly_trends.png", "Longitudinal volume", "Procedure volume and threshold-based center counts over time."),
        ("03_top_centers_latest_year.png", "Latest-year leaders", "Highest-volume centers in the latest reporting year."),
        ("11_concentration_trends.png", "Concentration trends", "Top-share concentration, HHI, and effective center count over time."),
        (
            f"13_coverage_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.png",
            "Access trade-off",
            "Urban-rural access loss when moving from the broader to the stricter network.",
        ),
        (
            f"15_population_coverage_ge_{main_threshold}_vs_ge_{strict_threshold}.png",
            "Population coverage",
            "Population-weighted access curves for the main and strict center networks.",
        ),
        ("17_isochrone_multipanel_thresholds.png", "Isochrone multipanel", "National multipanel comparison of the main and strict networks at 30 and 60 minutes."),
        ("18_state_county_access_context.png", "Regional context", "State-level access and the counties with the weakest strict-network access."),
        ("19_county_population_coverage_multipanel.png", "County coverage maps", "County-level population coverage across threshold and time scenarios."),
    ]


def _asset_text(name: str) -> str:
    return (ASSET_DIR / name).read_text(encoding="utf-8")


def _case_prefix(case_col: str) -> str:
    return case_col[:-6] if case_col.endswith("_cases") else case_col


def _records(df: pd.DataFrame, *, columns: list[str] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    work = df.copy()
    if columns is not None:
        available = [column for column in columns if column in work.columns]
        work = work[available]
    if limit is not None:
        work = work.head(limit)
    return json.loads(work.to_json(orient="records"))


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _threshold_row(threshold_summary: list[dict[str, Any]], threshold: int) -> dict[str, Any]:
    for row in threshold_summary:
        if int(row.get("threshold", -1)) == threshold:
            return row
    return {}


def _metric_delta(summary: dict[str, Any], key: str) -> int | None:
    latest = summary.get("latest_year_row", {})
    previous = summary.get("previous_year_row", {})
    if key not in latest or key not in previous:
        return None
    try:
        return int(round(float(latest[key]) - float(previous[key])))
    except (TypeError, ValueError):
        return None


def _key_findings(
    summary: dict[str, Any],
    state_access: pd.DataFrame,
    county_access: pd.DataFrame,
    latest_centers: pd.DataFrame,
) -> list[dict[str, str]]:
    main_threshold = int(summary["main_threshold"])
    strict_threshold = int(summary["strict_threshold"])
    strict_row = _threshold_row(summary["threshold_summary"], strict_threshold)
    main_row = _threshold_row(summary["threshold_summary"], main_threshold)

    findings = [
        {
            "kicker": "Volume",
            "title": f"{summary['latest_year_cases_total']:,} procedures in {summary['latest_year']}",
            "body": (
                f"{summary['latest_year_hospitals_any']} hospitals reported activity. "
                f"The >= {strict_threshold} cohort captured {float(strict_row.get('pct_of_cases_total', 0.0)):.2f}% of all cases."
            ),
        },
        {
            "kicker": "Thresholding",
            "title": f"{int(main_row.get('hospitals', 0))} broad-network vs {int(strict_row.get('hospitals', 0))} strict-network centers",
            "body": (
                f"The stricter cohort removes {int(main_row.get('hospitals', 0)) - int(strict_row.get('hospitals', 0))} sites "
                f"while preserving most procedural volume."
            ),
        },
    ]

    strict_60_col = f"coverage_ge_{strict_threshold}_60m_pct"
    if not state_access.empty and strict_60_col in state_access.columns:
        weakest = state_access.sort_values(strict_60_col, ascending=True).iloc[0]
        strongest = state_access.sort_values(strict_60_col, ascending=False).iloc[0]
        findings.append(
            {
                "kicker": "Regional gap",
                "title": f"{weakest['state_name']} has the weakest strict-network 60-minute access",
                "body": (
                    f"{float(weakest[strict_60_col]):.2f}% covered versus "
                    f"{float(strongest[strict_60_col]):.2f}% in {strongest['state_name']}."
                ),
            }
        )

    if not county_access.empty and strict_60_col in county_access.columns:
        zero_count = int((pd.to_numeric(county_access[strict_60_col], errors="coerce").fillna(0) <= 0).sum())
        findings.append(
            {
                "kicker": "County exposure",
                "title": f"{zero_count} counties have 0% strict-network 60-minute coverage",
                "body": "This is a direct local-access signal and highlights where the threshold decision bites hardest.",
            }
        )

    if not latest_centers.empty:
        top_center = latest_centers.iloc[0]
        findings.append(
            {
                "kicker": "Leading center",
                "title": f"{top_center['hospital_name']} leads the latest year",
                "body": f"{int(top_center[summary['case_col']])} procedures in {top_center['city']}.",
            }
        )

    return findings[:4]


def _normalized_yearly(yearly: pd.DataFrame, case_prefix: str, main_threshold: int, strict_threshold: int) -> pd.DataFrame:
    rename_map = {
        "year": "year",
        f"{case_prefix}_cases_total": "cases_total",
        f"{case_prefix}_hospitals_any": "hospitals_any",
        f"{case_prefix}_hospitals_{main_threshold}plus": "hospitals_main",
        f"{case_prefix}_hospitals_{strict_threshold}plus": "hospitals_strict",
        f"{case_prefix}_share_cases_in_{strict_threshold}plus_hospitals": "strict_share_pct",
    }
    available = {source: target for source, target in rename_map.items() if source in yearly.columns}
    return yearly[list(available)].rename(columns=available)


def _copy_figures(report_dir: Path, output_dir: Path, *, main_threshold: int, strict_threshold: int) -> list[dict[str, str]]:
    figures_dir = report_dir / "figures"
    asset_dir = output_dir / "assets" / "figures"
    asset_dir.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, str]] = []

    for file_name, title, caption in _figure_specs(main_threshold, strict_threshold):
        source = figures_dir / file_name
        if not source.exists():
            continue
        target = asset_dir / file_name
        shutil.copy2(source, target)
        payload.append(
            {
                "file": f"assets/figures/{file_name}",
                "title": title,
                "caption": caption,
            }
        )
    return payload


def build_indication_webapp(
    *,
    report_dir: Path | str,
    output_dir: Path | str,
    title: str | None = None,
) -> dict[str, str]:
    report_path = config.resolve(report_dir).resolve()
    output_path = config.resolve(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    summary = json.loads((report_path / "report_summary.json").read_text(encoding="utf-8"))
    summary_md_path = report_path / "SUMMARY.md"
    summary_md = summary_md_path.read_text(encoding="utf-8") if summary_md_path.exists() else ""

    tables_dir = report_path / "tables"
    case_col = summary["case_col"]
    case_prefix = _case_prefix(case_col)
    latest_year = int(summary["latest_year"])
    main_threshold = int(summary["main_threshold"])
    strict_threshold = int(summary["strict_threshold"])

    yearly = _read_csv(tables_dir / "yearly_summary.csv")
    latest_centers = _read_csv(tables_dir / "latest_year_hospital_code_totals.csv")
    latest_state_rates = _read_csv(tables_dir / "latest_year_state_population_rates.csv")
    state_access = _read_csv(tables_dir / "state_access_context.csv")
    county_access = _read_csv(tables_dir / "county_access_context.csv")
    concentration = _read_csv(tables_dir / "yearly_concentration_summary.csv")
    churn = _read_csv(tables_dir / "threshold_churn_by_ik.csv")
    top_ik = _read_csv(tables_dir / "top_ik_all_years.csv")
    provider_counties = _read_csv(tables_dir / "latest_year_county_provider_rates.csv")
    population_main = _read_csv(tables_dir / f"isochrone_population_coverage_ge_{main_threshold}.csv")
    population_strict = _read_csv(tables_dir / f"isochrone_population_coverage_ge_{strict_threshold}.csv")
    coverage_tradeoff = _read_csv(tables_dir / f"coverage_tradeoff_ge_{main_threshold}_vs_ge_{strict_threshold}.csv")

    yearly_normalized = _normalized_yearly(yearly, case_prefix, main_threshold, strict_threshold)
    if not latest_centers.empty and case_col in latest_centers.columns:
        latest_centers = latest_centers.sort_values(case_col, ascending=False).reset_index(drop=True)

    top_provider_counties = provider_counties.loc[provider_counties.get("threshold", pd.Series(dtype=int)) == 1].copy()
    if not top_provider_counties.empty and "cases_per_million" in top_provider_counties.columns:
        top_provider_counties = top_provider_counties.sort_values("cases_per_million", ascending=False).reset_index(drop=True)

    figures = _copy_figures(
        report_path,
        output_path,
        main_threshold=main_threshold,
        strict_threshold=strict_threshold,
    )

    findings = _key_findings(summary, state_access, county_access, latest_centers)

    latest_row = summary.get("latest_year_row", {})
    previous_year = summary.get("previous_year_row", {}).get("year")
    strict_row = _threshold_row(summary["threshold_summary"], strict_threshold)

    metrics = {
        "latest_year_cases_total": int(summary["latest_year_cases_total"]),
        "latest_year_hospitals_any": int(summary["latest_year_hospitals_any"]),
        "main_threshold_centers": int(_threshold_row(summary["threshold_summary"], main_threshold).get("hospitals", 0)),
        "strict_threshold_centers": int(strict_row.get("hospitals", 0)),
        "strict_threshold_case_share_pct": float(strict_row.get("pct_of_cases_total", 0.0)),
        "delta_cases_vs_previous": _metric_delta(summary, f"{case_prefix}_cases_total"),
        "delta_main_centers_vs_previous": _metric_delta(summary, f"{case_prefix}_hospitals_{main_threshold}plus"),
        "delta_strict_centers_vs_previous": _metric_delta(summary, f"{case_prefix}_hospitals_{strict_threshold}plus"),
        "previous_year": int(previous_year) if previous_year is not None else None,
        "matched_subcodes": summary.get("matched_subcodes", []),
    }

    methods = [
        f"OPS selector: {summary['ops_selector']}",
        f"Time bands used for access: {', '.join(str(value) for value in summary.get('time_bins', []))} minutes",
        f"Thresholds emphasized in the app: >= {main_threshold} and >= {strict_threshold} procedures per year",
        "Population access is raster-based and aggregated across Germany, states, and counties.",
        "The app is static: all tables and figures are embedded from the existing report output folder.",
    ]

    payload = {
        "meta": {
            "title": title or f"{summary['indication_name']} dashboard",
            "indication_name": summary["indication_name"],
            "ops_selector": summary["ops_selector"],
            "latest_year": latest_year,
            "main_threshold": main_threshold,
            "strict_threshold": strict_threshold,
            "time_bins": summary.get("time_bins", []),
            "report_dir": str(report_path),
        },
        "metrics": metrics,
        "methods": methods,
        "summary_markdown": summary_md,
        "findings": findings,
        "yearly": _records(yearly_normalized),
        "threshold_summary": summary["threshold_summary"],
        "top_centers": _records(latest_centers, columns=["hospital_name", "city", case_col], limit=15),
        "top_ik": _records(top_ik, columns=["hospital_name", "city", "total_cases", "years_active", "first_year", "last_year"], limit=15),
        "state_rates": _records(
            latest_state_rates.loc[latest_state_rates.get("threshold", pd.Series(dtype=int)) == 1].sort_values(
                "cases_per_million", ascending=False
            ),
            columns=["state_name", "cases_per_million", "hospitals_per_million", "total_cases", "hospitals"],
        ),
        "state_access": _records(state_access.sort_values(f"coverage_ge_{strict_threshold}_60m_pct", ascending=False)),
        "county_access": _records(county_access.sort_values(f"coverage_ge_{strict_threshold}_60m_pct", ascending=True)),
        "top_provider_counties": _records(
            top_provider_counties,
            columns=["state_name", "county_name", "hospitals", "total_cases", "cases_per_million"],
            limit=15,
        ),
        "population_coverage": {
            "main": _records(population_main),
            "strict": _records(population_strict),
        },
        "coverage_tradeoff": _records(coverage_tradeoff),
        "concentration": _records(concentration),
        "churn": _records(churn),
        "figures": figures,
        "case_col": case_col,
        "latest_year_row": latest_row,
    }

    (output_path / "index.html").write_text(_asset_text("index.html"), encoding="utf-8")
    (output_path / "styles.css").write_text(_asset_text("styles.css"), encoding="utf-8")
    (output_path / "app.js").write_text(_asset_text("app.js"), encoding="utf-8")
    (output_path / "data.js").write_text(
        "window.GBA_INDICATION_DASHBOARD = " + json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    return {
        "report_dir": str(report_path),
        "output_dir": str(output_path),
        "index_html": str(output_path / "index.html"),
    }


__all__ = ["build_indication_webapp"]
