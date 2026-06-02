from tickbiterisk.modeling.regimes import (
    CASE_DEFINITION_2022_PLUS,
    COVID_REPORTING_DISRUPTION,
    MDH_PROBABLE_ONLY_2024,
    PRE_2020_BASELINE,
    classify_surveillance_regime,
    is_reporting_break_regime,
    split_flags,
)


def test_classify_surveillance_regime_matches_existing_boundary_contract() -> None:
    assert classify_surveillance_regime("", 2019) == PRE_2020_BASELINE
    assert classify_surveillance_regime("", 2020) == COVID_REPORTING_DISRUPTION
    assert classify_surveillance_regime("", 2021) == "other_surveillance_regime"
    assert classify_surveillance_regime("", 2022) == CASE_DEFINITION_2022_PLUS
    assert (
        classify_surveillance_regime("lyme_case_definition_change", 2018)
        == CASE_DEFINITION_2022_PLUS
    )
    assert (
        classify_surveillance_regime("mdh_probable_only_2024,lyme_case_definition_change", 2024)
        == MDH_PROBABLE_ONLY_2024
    )


def test_reporting_break_regime_helper_and_flag_splitter_are_shared() -> None:
    assert split_flags(" covid_reporting_disruption, lyme_case_definition_change, ") == [
        "covid_reporting_disruption",
        "lyme_case_definition_change",
    ]
    assert is_reporting_break_regime(COVID_REPORTING_DISRUPTION) is True
    assert is_reporting_break_regime(CASE_DEFINITION_2022_PLUS) is True
    assert is_reporting_break_regime(MDH_PROBABLE_ONLY_2024) is True
    assert is_reporting_break_regime(PRE_2020_BASELINE) is False
