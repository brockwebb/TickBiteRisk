from __future__ import annotations


PRE_2020_BASELINE = "pre_2020_baseline"
COVID_REPORTING_DISRUPTION = "covid_reporting_disruption"
CASE_DEFINITION_2022_PLUS = "case_definition_change_2022_plus"
MDH_PROBABLE_ONLY_2024 = "mdh_probable_only_2024"
OTHER_SURVEILLANCE_REGIME = "other_surveillance_regime"

REPORTING_BREAK_REGIMES = {
    COVID_REPORTING_DISRUPTION,
    CASE_DEFINITION_2022_PLUS,
    MDH_PROBABLE_ONLY_2024,
}

SURVEILLANCE_REGIMES = {
    PRE_2020_BASELINE,
    COVID_REPORTING_DISRUPTION,
    CASE_DEFINITION_2022_PLUS,
    MDH_PROBABLE_ONLY_2024,
    OTHER_SURVEILLANCE_REGIME,
}


def split_flags(value: str) -> list[str]:
    return [
        flag
        for raw_flag in str(value).split(",")
        if (flag := raw_flag.strip())
    ]


def classify_surveillance_regime(quality_flags: str, test_year: int) -> str:
    flags = split_flags(quality_flags)
    if "mdh_probable_only_2024" in flags:
        return MDH_PROBABLE_ONLY_2024
    if "covid_reporting_disruption" in flags or test_year == 2020:
        return COVID_REPORTING_DISRUPTION
    if "lyme_case_definition_change" in flags or test_year >= 2022:
        return CASE_DEFINITION_2022_PLUS
    if test_year < 2020:
        return PRE_2020_BASELINE
    return OTHER_SURVEILLANCE_REGIME


def is_reporting_break_regime(regime: str) -> bool:
    return regime in REPORTING_BREAK_REGIMES
