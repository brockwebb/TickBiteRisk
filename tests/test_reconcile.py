from tickbiterisk.etl.lyme import LymeCountyYearValue
from tickbiterisk.etl.reconcile import reconcile_lyme_county_year


def test_reconcile_prefers_public_use_when_values_agree() -> None:
    rows = [
        LymeCountyYearValue("cdc_lyme_public_2022_2023", "24003", 2022, None, 127, 127),
        LymeCountyYearValue("cdc_lyme_county_dashboard_2023", "24003", 2022, None, None, 127),
    ]
    reconciled = reconcile_lyme_county_year(rows)
    assert len(reconciled) == 1
    assert reconciled[0].total_cases == 127
    assert reconciled[0].canonical_source_id == "cdc_lyme_public_2022_2023"
    assert reconciled[0].reconciliation_status == "matched"


def test_reconcile_flags_conflicting_comparator() -> None:
    rows = [
        LymeCountyYearValue("cdc_lyme_public_2022_2023", "24003", 2022, None, 127, 127),
        LymeCountyYearValue("cdc_all_tbd_2022_public", "24003", 2022, None, None, 460),
    ]
    reconciled = reconcile_lyme_county_year(rows)
    assert reconciled[0].total_cases == 127
    assert reconciled[0].canonical_source_id == "cdc_lyme_public_2022_2023"
    assert reconciled[0].reconciliation_status == "conflict"
    assert "cdc_all_tbd_2022_public=460" in reconciled[0].source_values_summary


def test_reconcile_flags_mdh_2024_probable_only_source() -> None:
    rows = [
        LymeCountyYearValue(
            "mdh_lyme_2013_2024_pdf",
            "24003",
            2024,
            None,
            203,
            203,
        )
    ]

    reconciled = reconcile_lyme_county_year(rows)

    assert len(reconciled) == 1
    assert reconciled[0].canonical_source_id == "mdh_lyme_2013_2024_pdf"
    assert reconciled[0].confirmed_cases is None
    assert reconciled[0].probable_cases == 203
    assert reconciled[0].data_quality_flags == (
        "lyme_case_definition_change;mdh_probable_only_2024;"
        "state_source_not_cdc_public_use"
    )
