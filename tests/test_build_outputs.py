from pathlib import Path

import pandas as pd

from tickbiterisk.etl.build import write_reconciled_lyme_outputs
from tickbiterisk.etl.lyme import LymeCountyYearValue


def test_write_reconciled_lyme_outputs_creates_csv(tmp_path: Path) -> None:
    rows = [
        LymeCountyYearValue("cdc_lyme_public_2022_2023", "24003", 2022, None, 127, 127),
        LymeCountyYearValue(
            "cdc_lyme_county_dashboard_2023", "24003", 2022, None, None, 127
        ),
    ]
    output = write_reconciled_lyme_outputs(rows, tmp_path)
    assert output.name == "lyme_county_year_reconciled.csv"
    df = pd.read_csv(output, dtype={"county_fips": str})
    assert df.loc[0, "county_fips"] == "24003"
    assert int(df.loc[0, "total_cases"]) == 127
    assert df.loc[0, "reconciliation_status"] == "matched"
