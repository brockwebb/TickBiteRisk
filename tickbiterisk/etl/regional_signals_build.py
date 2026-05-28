from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.regional_signals import RegionalSignalRow


REGIONAL_SIGNAL_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "county_fips",
    "county_name",
    "year",
    "total_cases",
    "diagnostic_state_total_cases",
    "diagnostic_midatlantic_total_cases",
    "diagnostic_county_share_of_state_cases",
    "diagnostic_county_share_of_midatlantic_cases",
    "feature_prior_year_total_cases",
    "feature_prior_year_county_share_of_state_cases",
    "feature_prior_year_county_share_of_midatlantic_cases",
    "feature_prior_year_state_total_cases",
    "feature_prior_year_midatlantic_total_cases",
    "feature_trailing_5yr_midatlantic_total_min",
    "feature_trailing_5yr_midatlantic_total_mean",
    "feature_trailing_5yr_midatlantic_total_max",
    "diagnostic_midatlantic_total_within_trailing_5yr_band",
    "source_panel_sha256",
    "feature_quality_flags",
]


def write_regional_signals_output(
    rows: list[RegionalSignalRow],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "midatlantic_regional_signals.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGIONAL_SIGNAL_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record.get(column))
                for column in REGIONAL_SIGNAL_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )
    return output_path


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
