from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.lyme import LymeCountyYearValue
from tickbiterisk.etl.reconcile import reconcile_lyme_county_year

RECONCILED_LYME_COLUMNS = [
    "county_fips",
    "year",
    "confirmed_cases",
    "probable_cases",
    "total_cases",
    "canonical_source_id",
    "source_values_summary",
    "reconciliation_status",
    "data_quality_flags",
]


def write_reconciled_lyme_outputs(
    rows: list[LymeCountyYearValue], output_dir: Path
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    reconciled = reconcile_lyme_county_year(rows)
    output_path = output_dir / "lyme_county_year_reconciled.csv"
    pd.DataFrame(
        [asdict(row) for row in reconciled], columns=RECONCILED_LYME_COLUMNS
    ).to_csv(output_path, index=False)
    return output_path
