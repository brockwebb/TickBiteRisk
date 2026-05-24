from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tickbiterisk.etl.lyme import LymeCountyYearValue
from tickbiterisk.etl.reconcile import reconcile_lyme_county_year


def write_reconciled_lyme_outputs(
    rows: list[LymeCountyYearValue], output_dir: Path
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    reconciled = reconcile_lyme_county_year(rows)
    output_path = output_dir / "lyme_county_year_reconciled.csv"
    pd.DataFrame([asdict(row) for row in reconciled]).to_csv(output_path, index=False)
    return output_path
