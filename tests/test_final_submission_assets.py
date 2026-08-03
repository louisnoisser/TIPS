from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/final_submission_assets_2026-07-24"
GEO = OUT / "geography"
SOURCE_REVIEW = (
    ROOT
    / "outputs/geography_validation_ge50_2026-07-24/"
    "geography_manual_review_ge20_2024_ge50_completed.csv"
)


def test_manual_review_import_and_priority_isolation():
    source = pd.read_csv(SOURCE_REVIEW, dtype=str).fillna("")
    final = pd.read_csv(
        OUT / "geography_manual_review_ge20_2024_completed.csv",
        dtype=str,
    ).fillna("")
    assert len(final[final.manual_review_priority == "3"]) == 29
    for priority, expected in (("1", 16), ("2", 15)):
        mask = source.manual_review_priority == priority
        assert int(mask.sum()) == expected
        assert source.loc[mask].equals(final.loc[mask])


def test_address_coordinate_and_threshold_release_gates():
    master = pd.read_csv(GEO / "provider_locations_master_2024.csv")
    expected = {20: 60, 50: 31, 100: 16, 200: 6}
    for threshold, count in expected.items():
        selected = master[master[f"threshold_ge{threshold}"]]
        assert len(selected) == count
        assert selected.address_validation_status.eq(
            "validated site-specific address"
        ).all()
        assert selected.federal_state_status.str.startswith("validated").all()
        assert selected.coordinate_status.eq(
            "validated physical-site coordinate"
        ).all()


def test_routing_completeness():
    audit = pd.read_csv(GEO / "accessibility_routing_audit.csv")
    assert len(audit) == 60
    assert audit.routing_error.fillna("").eq("").all()
    assert audit.routed_30m.all()
    assert audit.routed_60m.all()


def test_population_denominator_and_benchmark_reproduction():
    final = pd.read_csv(GEO / "accessibility_final.csv")
    assert final.germany_population_denominator.eq(83_194_667).all()
    assert final.query("threshold == 50").covered_population.tolist() == [
        25_708_947, 60_465_819
    ]
    assert final.query("threshold == 100").covered_population.tolist() == [
        16_035_551, 48_597_532
    ]


def test_settlement_class_additivity():
    final = pd.read_csv(GEO / "accessibility_final.csv")
    classes = pd.read_csv(GEO / "accessibility_urban_rural_final.csv")
    assert set(classes.settlement_class) == {"urban", "rural", "other"}
    for row in final.itertuples(index=False):
        selected = classes[
            (classes.threshold == row.threshold)
            & (classes.time_minutes == row.time_minutes)
        ]
        assert int(selected.covered_population.sum()) == row.covered_population
        assert abs(
            int(selected.class_population_denominator.sum()) - 83_194_667
        ) <= 1


def test_federal_state_consistency():
    state = pd.read_csv(GEO / "federal_state_distribution_2024.csv")
    assert state.groupby("threshold").provider_count.sum().to_dict() == {
        20: 60, 50: 31, 100: 16, 200: 6
    }
    assert state.groupby("threshold").visible_activity.sum().to_dict() == {
        20: 4679, 50: 3717, 100: 2673, 200: 1422
    }


def test_figure_data_consistency():
    annual = pd.read_csv(
        ROOT / "outputs/final_corrected_2026-07-24/final_annual_metrics.csv"
    )
    figure1 = pd.read_csv(OUT / "figures/Figure1_data.csv")
    pd.testing.assert_frame_equal(figure1, annual)
    figure3 = pd.read_csv(OUT / "figures/Figure3_data.csv")
    assert int(figure3.provider_sites.sum()) == 113
    assert int(figure3.visible_procedural_activity.sum()) == 5_247
    figure4 = pd.read_csv(OUT / "figures/Figure4_data.csv")
    assert len(figure4) == 60
    assert figure4.threshold_ge20.all()


def test_table_data_consistency():
    source = pd.read_csv(
        ROOT
        / "outputs/final_corrected_2026-07-24/"
        "table1_2024_exclusive_categories.csv"
    )
    table = pd.read_csv(OUT / "tables/Table1_2024_exclusive_categories.csv")
    assert table.physical_sites.tolist() == source.provider_sites.tolist()
    assert (
        table.visible_procedural_activity.tolist()
        == source.visible_procedural_activity.tolist()
    )
    table_s5 = pd.read_csv(
        OUT / "tables/TableS5_potential_geographic_accessibility.csv"
    )
    assert len(table_s5) == 6
    assert table_s5.failed_routing_sites.eq(0).all()


def test_caption_numbers_and_punctuation():
    captions = (OUT / "figure_captions.md").read_text(encoding="utf-8")
    footnotes = (
        OUT / "table_titles_and_footnotes.md"
    ).read_text(encoding="utf-8")
    assert "113 physical sites and 5,247 visible procedure occurrences" in captions
    assert "60 physical sites" in captions
    assert "31 physical sites" in captions
    assert "16 physical sites" in captions
    assert "83,194,667" in footnotes
    assert ";" not in captions + footnotes
    assert "—" not in captions + footnotes


def test_asset_manifest_completeness_and_output_isolation():
    manifest = pd.read_csv(OUT / "submission_asset_manifest.csv")
    expected = {
        "Figure 1", "Figure 2", "Figure 3", "Figure 4", "Table 1",
        "Table S1", "Table S2", "Table S3", "Table S4", "Table S5",
        "Table S6",
    }
    assert expected.issubset(set(manifest.asset_number))
    assert manifest.loc[
        manifest.asset_number == "Table S6", "final_or_withheld"
    ].eq("withheld").all()
    assert not list((OUT / "tables").glob("TableS6*.csv"))
    for path in OUT.rglob("*"):
        if path.is_file():
            assert OUT in path.parents
