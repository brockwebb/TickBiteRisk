from __future__ import annotations

from dataclasses import dataclass

from tickbiterisk.etl.lyme import LymeCountyYearValue

SOURCE_PRIORITY = [
    "mdh_lyme_2013_2024_pdf",
    "cdc_lyme_public_2022_2023",
    "cdc_lyme_public_2008_2021",
    "cdc_lyme_public_1992_2007",
    "cdc_lyme_county_dashboard_2023",
    "cdc_lyme_county_geodata_2000_2021",
    "cdc_all_tbd_2022_public",
]


@dataclass(frozen=True)
class ReconciledLymeCountyYear:
    county_fips: str
    year: int
    confirmed_cases: int | None
    probable_cases: int | None
    total_cases: int
    canonical_source_id: str
    source_values_summary: str
    reconciliation_status: str
    data_quality_flags: str


def _source_rank(source_id: str) -> int:
    try:
        return SOURCE_PRIORITY.index(source_id)
    except ValueError:
        return len(SOURCE_PRIORITY)


def reconcile_lyme_county_year(
    rows: list[LymeCountyYearValue],
) -> list[ReconciledLymeCountyYear]:
    grouped: dict[tuple[str, int], list[LymeCountyYearValue]] = {}
    for row in rows:
        grouped.setdefault((row.county_fips, row.year), []).append(row)

    reconciled: list[ReconciledLymeCountyYear] = []
    for (county_fips, year), values in sorted(grouped.items()):
        ordered = sorted(values, key=lambda item: _source_rank(item.source_id))
        canonical = ordered[0]
        totals = {value.total_cases for value in values}
        status = "matched" if len(totals) == 1 else "conflict"
        flags: list[str] = []
        if year == 2020:
            flags.append("covid_reporting_disruption")
        if year >= 2022:
            flags.append("lyme_case_definition_change")
        if any(
            value.source_id == "mdh_lyme_2013_2024_pdf" and year == 2024
            for value in values
        ):
            flags.append("mdh_probable_only_2024")
            flags.append("state_source_not_cdc_public_use")
        if any(value.source_id == "cdc_all_tbd_2022_public" for value in values):
            flags.append("contains_noncanonical_all_tbd_comparator")

        summary = ";".join(f"{value.source_id}={value.total_cases}" for value in ordered)
        reconciled.append(
            ReconciledLymeCountyYear(
                county_fips=county_fips,
                year=year,
                confirmed_cases=canonical.confirmed_cases,
                probable_cases=canonical.probable_cases,
                total_cases=canonical.total_cases,
                canonical_source_id=canonical.source_id,
                source_values_summary=summary,
                reconciliation_status=status,
                data_quality_flags=";".join(flags),
            )
        )
    return reconciled
