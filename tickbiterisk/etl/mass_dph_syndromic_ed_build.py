from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from tickbiterisk.etl.mass_dph_syndromic_ed import (
    MassDphSyndromicEdCountySummary,
)


MASS_DPH_SYNDROMIC_ED_COLUMNS = [
    "state_fips",
    "state_abbr",
    "state_name",
    "report_year",
    "report_period_label",
    "report_period_start",
    "report_period_end",
    "county_name",
    "county_fips",
    "county_fips_list",
    "geography_type",
    "total_ed_visits",
    "tickborne_disease_ed_visits",
    "tickborne_disease_rate_per_10000",
    "missing_or_out_of_state_visits",
    "source_id",
    "source_url",
    "parser_method",
    "feature_quality_flags",
]


def write_mass_dph_syndromic_ed_output(
    rows: list[MassDphSyndromicEdCountySummary],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "mass_dph_syndromic_ed_county_summary.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MASS_DPH_SYNDROMIC_ED_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {
                column: _format_value(record[column])
                for column in MASS_DPH_SYNDROMIC_ED_COLUMNS
            }
            for record in [asdict(row) for row in rows]
        )
    return output_path


def _format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)
