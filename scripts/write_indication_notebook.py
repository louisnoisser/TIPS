#!/usr/bin/env python3
"""Populate a scaffolded notebook for one indication report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def md_cell(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [line if line.endswith("\n") else f"{line}\n" for line in text.splitlines()]}


def code_cell(code: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": [line if line.endswith("\n") else f"{line}\n" for line in code.splitlines()],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--indication-name", required=True)
    parser.add_argument("--ops-selector", required=True)
    parser.add_argument("--latest-year", type=int, required=True)
    parser.add_argument("--main-threshold", type=int, required=True)
    parser.add_argument("--strict-threshold", type=int, required=True)
    parser.add_argument("--case-col", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    notebook = json.loads(args.notebook.read_text(encoding="utf-8"))
    report_dir = args.report_dir.resolve()
    repo_root = args.notebook.resolve().parents[2]

    notebook["cells"] = [
        md_cell(
            f"# Experiment: {args.title}\n\n"
            f"Objective:\n"
            f"- Review the reusable indication-report output for {args.indication_name}.\n"
            f"- Confirm latest-year center distribution, longitudinal trends, and access summaries.\n"
            f"- Reuse this notebook as a template for future OPS families.\n"
        ),
        code_cell(
            "from __future__ import annotations\n\n"
            "import json\n"
            "from pathlib import Path\n\n"
            "import pandas as pd\n"
            "from IPython.display import Image, display\n\n"
            f"REPO_ROOT = Path(r'{repo_root}')\n"
            f"REPORT_DIR = Path(r'{report_dir}')\n"
            "TABLES = REPORT_DIR / 'tables'\n"
            "FIGURES = REPORT_DIR / 'figures'\n"
            "GEO = REPORT_DIR / 'geo'\n"
            "summary = json.loads((REPORT_DIR / 'report_summary.json').read_text())\n"
            "summary\n"
        ),
        md_cell(
            "## Plan\n\n"
            "- Inspect the high-level summary and longitudinal tables.\n"
            f"- Inspect the {args.latest_year} center distribution and threshold sensitivity.\n"
            f"- Review the geocoded center mix and the access analyses for `>= {args.main_threshold}` and `>= {args.strict_threshold}` cases.\n"
        ),
        code_cell(
            "yearly = pd.read_csv(TABLES / 'yearly_summary.csv')\n"
            "thresholds = pd.read_csv(TABLES / 'latest_year_threshold_summary.csv')\n"
            "matched_subcodes = pd.read_csv(TABLES / 'latest_year_matched_subcodes.csv')\n"
            "top_all_years = pd.read_csv(TABLES / 'top_centers_all_years.csv')\n"
            "state_summary = pd.read_csv(TABLES / 'latest_year_state_summary.csv')\n"
            "urban_summary = pd.read_csv(TABLES / 'latest_year_urban_summary.csv')\n"
            "top_latest = pd.read_csv(TABLES / 'latest_year_hospital_code_totals.csv').head(15)\n"
            "display(yearly.tail())\n"
            "display(thresholds)\n"
            "display(matched_subcodes.head(20))\n"
            f"display(top_latest[['hospital_name', 'city', '{args.case_col}']])\n"
            "display(top_all_years.head(20))\n"
            "display(state_summary)\n"
            "display(urban_summary)\n"
            f"coverage_main_path = TABLES / 'isochrone_coverage_urban_rural_ge_{args.main_threshold}.csv'\n"
            f"coverage_strict_path = TABLES / 'isochrone_coverage_urban_rural_ge_{args.strict_threshold}.csv'\n"
            "concentration_path = TABLES / 'yearly_concentration_summary.csv'\n"
            "churn_path = TABLES / 'threshold_churn_by_ik.csv'\n"
            f"tradeoff_path = TABLES / 'coverage_tradeoff_ge_{args.main_threshold}_vs_ge_{args.strict_threshold}.csv'\n"
            f"population_tradeoff_path = TABLES / 'population_tradeoff_ge_{args.main_threshold}_vs_ge_{args.strict_threshold}.csv'\n"
            "state_population_rates_path = TABLES / 'latest_year_state_population_rates.csv'\n"
            f"population_main_path = TABLES / 'isochrone_population_coverage_ge_{args.main_threshold}.csv'\n"
            f"population_strict_path = TABLES / 'isochrone_population_coverage_ge_{args.strict_threshold}.csv'\n"
            "top_ik_path = TABLES / 'top_ik_all_years.csv'\n"
            "state_context_path = TABLES / 'state_access_context.csv'\n"
            "county_context_path = TABLES / 'county_access_context.csv'\n"
            f"state_coverage_main_path = TABLES / 'state_population_coverage_ge_{args.main_threshold}.csv'\n"
            f"state_coverage_strict_path = TABLES / 'state_population_coverage_ge_{args.strict_threshold}.csv'\n"
            f"county_coverage_main_path = TABLES / 'county_population_coverage_ge_{args.main_threshold}.csv'\n"
            f"county_coverage_strict_path = TABLES / 'county_population_coverage_ge_{args.strict_threshold}.csv'\n"
            "county_provider_rates_path = TABLES / 'latest_year_county_provider_rates.csv'\n"
            "if coverage_main_path.exists():\n"
            "    display(pd.read_csv(coverage_main_path))\n"
            "if coverage_strict_path.exists() and coverage_strict_path != coverage_main_path:\n"
            "    display(pd.read_csv(coverage_strict_path))\n"
            "if concentration_path.exists():\n"
            "    display(pd.read_csv(concentration_path))\n"
            "if churn_path.exists():\n"
            "    display(pd.read_csv(churn_path))\n"
            "if tradeoff_path.exists():\n"
            "    display(pd.read_csv(tradeoff_path))\n"
            "if population_tradeoff_path.exists():\n"
            "    display(pd.read_csv(population_tradeoff_path))\n"
            "if population_main_path.exists():\n"
            "    display(pd.read_csv(population_main_path))\n"
            "if population_strict_path.exists() and population_strict_path != population_main_path:\n"
            "    display(pd.read_csv(population_strict_path))\n"
            "if state_population_rates_path.exists():\n"
            "    display(pd.read_csv(state_population_rates_path))\n"
            "if top_ik_path.exists():\n"
            "    display(pd.read_csv(top_ik_path).head(20))\n"
            "if state_context_path.exists():\n"
            "    display(pd.read_csv(state_context_path).head(16))\n"
            "if county_context_path.exists():\n"
            f"    display(pd.read_csv(county_context_path).sort_values('coverage_ge_{args.strict_threshold}_60m_pct').head(20))\n"
            "if state_coverage_main_path.exists():\n"
            "    display(pd.read_csv(state_coverage_main_path).head(20))\n"
            "if state_coverage_strict_path.exists():\n"
            "    display(pd.read_csv(state_coverage_strict_path).head(20))\n"
            "if county_coverage_main_path.exists():\n"
            "    display(pd.read_csv(county_coverage_main_path).head(20))\n"
            "if county_coverage_strict_path.exists():\n"
            "    display(pd.read_csv(county_coverage_strict_path).head(20))\n"
            "if county_provider_rates_path.exists():\n"
            "    display(pd.read_csv(county_provider_rates_path).sort_values(['threshold', 'cases_per_million'], ascending=[True, False]).head(20))\n"
        ),
        md_cell(
            "## Results\n\n"
            "- The report folder already contains all generated tables and figures.\n"
            "- The code below displays the key figures directly from disk.\n"
        ),
        code_cell(
            "figure_files = [\n"
            "    '01_yearly_trends.png',\n"
            "    '02_threshold_counts_latest_year.png',\n"
            "    '03_top_centers_latest_year.png',\n"
            "    '04_case_distribution_latest_year.png',\n"
            f"    '05_state_summary_ge_{args.main_threshold}.png',\n"
            "    '06_urban_rural_centers.png',\n"
            f"    '07_centers_map_ge_{args.main_threshold}.png',\n"
            f"    '08_centers_map_ge_{args.strict_threshold}.png',\n"
            f"    '09_isochrone_map_ge_{args.main_threshold}.png',\n"
            f"    '10_isochrone_coverage_ge_{args.main_threshold}.png',\n"
            f"    '09_isochrone_map_ge_{args.strict_threshold}.png',\n"
            f"    '10_isochrone_coverage_ge_{args.strict_threshold}.png',\n"
            "    '11_concentration_trends.png',\n"
            "    '12_threshold_churn_by_ik.png',\n"
            f"    '13_coverage_tradeoff_ge_{args.main_threshold}_vs_ge_{args.strict_threshold}.png',\n"
            "    '14_top_ik_all_years.png',\n"
            f"    '15_population_coverage_ge_{args.main_threshold}_vs_ge_{args.strict_threshold}.png',\n"
            "    '16_state_case_rates_per_million.png',\n"
            "    '17_isochrone_multipanel_thresholds.png',\n"
            "    '18_state_county_access_context.png',\n"
            "    '19_county_population_coverage_multipanel.png',\n"
            "]\n"
            "for name in figure_files:\n"
            "    path = FIGURES / name\n"
            "    if path.exists():\n"
                "        display(path)\n"
            "        display(Image(filename=str(path)))\n"
        ),
        md_cell(
            "## Next steps\n\n"
            "- Swap the OPS selector and rerun the generic report builder for the next indication.\n"
            "- If a clinical denominator is needed, extend the report to include specific ICD selectors.\n"
            "- If referral-style access is more appropriate, adjust the time bins and rerun the report.\n"
        ),
    ]
    args.notebook.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")
    print(f"Updated notebook: {args.notebook}")


if __name__ == "__main__":
    main()
