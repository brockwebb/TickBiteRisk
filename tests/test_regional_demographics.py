import csv
from pathlib import Path

from tickbiterisk.etl.regional_demographics import (
    build_midatlantic_age_sex_urls,
    parse_census_pep_2019_age_sex,
    parse_census_pep_2024_age_sex,
)
from tickbiterisk.etl.regional_demographics_build import (
    REGIONAL_AGE_DEMOGRAPHICS_COLUMNS,
    write_regional_age_demographics_output,
)


def test_build_midatlantic_age_sex_urls_uses_static_census_csvs() -> None:
    urls = build_midatlantic_age_sex_urls(state_fips_list=("10", "24"))

    assert urls == [
        "https://www2.census.gov/programs-surveys/popest/datasets/"
        "2010-2019/counties/asrh/cc-est2019-agesex-10.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/"
        "2010-2019/counties/asrh/cc-est2019-agesex-24.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/"
        "2020-2024/counties/asrh/cc-est2024-agesex-10.csv",
        "https://www2.census.gov/programs-surveys/popest/datasets/"
        "2020-2024/counties/asrh/cc-est2024-agesex-24.csv",
    ]


def test_parse_census_pep_2019_age_sex_derives_population_shares() -> None:
    rows = parse_census_pep_2019_age_sex(
        _age_sex_csv(
            [
                {
                    "STATE": "24",
                    "COUNTY": "003",
                    "STNAME": "Maryland",
                    "CTYNAME": "Anne Arundel County",
                    "YEAR": "2",
                    "POPESTIMATE": "90",
                    "UNDER5_TOT": "4",
                    "AGE513_TOT": "8",
                    "AGE1417_TOT": "3",
                    "AGE1824_TOT": "7",
                    "AGE2544_TOT": "20",
                    "AGE4564_TOT": "30",
                    "AGE65PLUS_TOT": "18",
                    "MEDIAN_AGE_TOT": "42.5",
                },
                {
                    "STATE": "24",
                    "COUNTY": "003",
                    "STNAME": "Maryland",
                    "CTYNAME": "Anne Arundel County",
                    "YEAR": "12",
                    "POPESTIMATE": "100",
                    "UNDER5_TOT": "5",
                    "AGE513_TOT": "10",
                    "AGE1417_TOT": "5",
                    "AGE1824_TOT": "8",
                    "AGE2544_TOT": "22",
                    "AGE4564_TOT": "30",
                    "AGE65PLUS_TOT": "20",
                    "MEDIAN_AGE_TOT": "43.1",
                },
            ]
        ),
        source_url="https://example.test/cc-est2019-agesex-24.csv",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "24003"
    assert row.year == 2019
    assert row.population == 100
    assert row.age5_17_population == 15
    assert row.age5_17_share == 0.15
    assert row.age65plus_share == 0.2
    assert row.median_age == 43.1
    assert row.source_id == "census_pep_2019_county_age_sex_24"
    assert "human_exposure_context_only" in row.feature_quality_flags
    assert "not_tick_bite_counts" in row.feature_quality_flags


def test_parse_census_pep_2024_age_sex_derives_latest_years() -> None:
    rows = parse_census_pep_2024_age_sex(
        _age_sex_csv(
            [
                {
                    "STATE": "10",
                    "COUNTY": "001",
                    "STNAME": "Delaware",
                    "CTYNAME": "Kent County",
                    "YEAR": "1",
                    "POPESTIMATE": "80",
                    "UNDER5_TOT": "4",
                    "AGE513_TOT": "8",
                    "AGE1417_TOT": "4",
                    "AGE1824_TOT": "8",
                    "AGE2544_TOT": "20",
                    "AGE4564_TOT": "24",
                    "AGE65PLUS_TOT": "12",
                    "MEDIAN_AGE_TOT": "39.8",
                },
                {
                    "STATE": "10",
                    "COUNTY": "001",
                    "STNAME": "Delaware",
                    "CTYNAME": "Kent County",
                    "YEAR": "6",
                    "POPESTIMATE": "200",
                    "UNDER5_TOT": "8",
                    "AGE513_TOT": "18",
                    "AGE1417_TOT": "12",
                    "AGE1824_TOT": "20",
                    "AGE2544_TOT": "50",
                    "AGE4564_TOT": "52",
                    "AGE65PLUS_TOT": "40",
                    "MEDIAN_AGE_TOT": "40.2",
                },
            ]
        ),
        source_url="https://example.test/cc-est2024-agesex-10.csv",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.county_fips == "10001"
    assert row.year == 2024
    assert row.age5_17_population == 30
    assert row.age5_17_share == 0.15
    assert row.age25_44_share == 0.25
    assert row.source_id == "census_pep_2024_county_age_sex_10"


def test_write_regional_age_demographics_output_writes_stable_columns(
    tmp_path: Path,
) -> None:
    rows = parse_census_pep_2024_age_sex(
        _age_sex_csv(
            [
                {
                    "STATE": "24",
                    "COUNTY": "011",
                    "STNAME": "Maryland",
                    "CTYNAME": "Caroline County",
                    "YEAR": "6",
                    "POPESTIMATE": "100",
                    "UNDER5_TOT": "5",
                    "AGE513_TOT": "10",
                    "AGE1417_TOT": "5",
                    "AGE1824_TOT": "8",
                    "AGE2544_TOT": "22",
                    "AGE4564_TOT": "30",
                    "AGE65PLUS_TOT": "20",
                    "MEDIAN_AGE_TOT": "43.1",
                }
            ]
        ),
        source_url="https://example.test/cc-est2024-agesex-24.csv",
    )

    output = write_regional_age_demographics_output(rows, tmp_path / "out")

    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        assert next(reader) == REGIONAL_AGE_DEMOGRAPHICS_COLUMNS
        first_row = next(reader)
    assert first_row[0:6] == ["24", "MD", "Maryland", "24011", "Caroline County", "2024"]


def _age_sex_csv(rows: list[dict[str, str]]) -> str:
    fieldnames = [
        "SUMLEV",
        "STATE",
        "COUNTY",
        "STNAME",
        "CTYNAME",
        "YEAR",
        "POPESTIMATE",
        "UNDER5_TOT",
        "AGE513_TOT",
        "AGE1417_TOT",
        "AGE1824_TOT",
        "AGE2544_TOT",
        "AGE4564_TOT",
        "AGE65PLUS_TOT",
        "MEDIAN_AGE_TOT",
    ]
    output_rows = []
    for row in rows:
        record = {fieldname: row.get(fieldname, "") for fieldname in fieldnames}
        record["SUMLEV"] = record.get("SUMLEV") or "050"
        output_rows.append(record)

    lines = [",".join(fieldnames)]
    for row in output_rows:
        lines.append(",".join(row[fieldname] for fieldname in fieldnames))
    return "\n".join(lines)
