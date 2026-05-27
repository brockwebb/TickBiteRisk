import csv
from dataclasses import replace
from pathlib import Path

from tickbiterisk.etl.seasonality import (
    SeasonalityInputError,
    build_seasonality_baseline,
    parse_cdc_lyme_monthly_onset,
    parse_cdc_lyme_weekly_onset,
)
from tickbiterisk.etl.seasonality_build import (
    SEASONALITY_BASELINE_COLUMNS,
    SEASONALITY_OBSERVATION_COLUMNS,
    write_seasonality_outputs,
)


def test_parse_cdc_monthly_onset_normalizes_annual_shares(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "monthly.csv",
        [
            {"Year": "2010", "Onset Month": "January", "Cases": "20"},
            {"Year": "2010", "Onset Month": "February", "Cases": "80"},
            {"Year": "2011", "Onset Month": "January", "Cases": "40"},
            {"Year": "2011", "Onset Month": "February", "Cases": "60"},
        ],
    )

    rows = parse_cdc_lyme_monthly_onset(
        path, source_id="cdc_seasonality_month_2023"
    )

    assert [(row.year, row.period, row.cases, row.annual_cases) for row in rows] == [
        (2010, 1, 20, 100),
        (2010, 2, 80, 100),
        (2011, 1, 40, 100),
        (2011, 2, 60, 100),
    ]
    assert rows[0].disease == "lyme"
    assert rows[0].grain == "month"
    assert rows[0].period_label == "January"
    assert rows[0].seasonal_share == 0.2


def test_parse_cdc_weekly_onset_sorts_and_labels_weeks(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "weekly.csv",
        [
            {"Year": "2010", "MMWR Week": "2", "Cases": "30"},
            {"Year": "2010", "MMWR Week": "1", "Cases": "70"},
        ],
    )

    rows = parse_cdc_lyme_weekly_onset(path, source_id="cdc_seasonality_week_2023")

    assert [(row.period, row.period_label, row.seasonal_share) for row in rows] == [
        (1, "MMWR Week 1", 0.7),
        (2, "MMWR Week 2", 0.3),
    ]


def test_parse_cdc_monthly_onset_rejects_duplicate_periods(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "monthly.csv",
        [
            {"Year": "2010", "Onset Month": "January", "Cases": "20"},
            {"Year": "2010", "Onset Month": "January", "Cases": "30"},
        ],
    )

    try:
        parse_cdc_lyme_monthly_onset(path, source_id="cdc_seasonality_month_2023")
    except SeasonalityInputError as exc:
        assert "duplicate seasonality period" in str(exc)
    else:
        raise AssertionError("Expected duplicate period to fail")


def test_parse_cdc_monthly_onset_rejects_missing_required_columns(
    tmp_path: Path,
) -> None:
    path = _write_csv(
        tmp_path / "monthly.csv",
        [{"Year": "2010", "Onset Month": "January"}],
    )

    try:
        parse_cdc_lyme_monthly_onset(path, source_id="cdc_seasonality_month_2023")
    except SeasonalityInputError as exc:
        assert "missing required seasonality column(s): Cases" in str(exc)
    else:
        raise AssertionError("Expected missing required column to fail")


def test_parse_cdc_weekly_onset_rejects_invalid_week_and_negative_cases(
    tmp_path: Path,
) -> None:
    invalid_week_path = _write_csv(
        tmp_path / "invalid-week.csv",
        [{"Year": "2010", "MMWR Week": "54", "Cases": "30"}],
    )
    negative_cases_path = _write_csv(
        tmp_path / "negative-cases.csv",
        [{"Year": "2010", "MMWR Week": "1", "Cases": "-1"}],
    )

    for path in [invalid_week_path, negative_cases_path]:
        try:
            parse_cdc_lyme_weekly_onset(
                path, source_id="cdc_seasonality_week_2023"
            )
        except SeasonalityInputError:
            pass
        else:
            raise AssertionError(f"Expected invalid input to fail: {path}")


def test_build_seasonality_baseline_computes_prediction_bands(tmp_path: Path) -> None:
    observations = parse_cdc_lyme_monthly_onset(
        _write_csv(
            tmp_path / "monthly.csv",
            [
                {"Year": "2010", "Onset Month": "January", "Cases": "20"},
                {"Year": "2010", "Onset Month": "February", "Cases": "80"},
                {"Year": "2011", "Onset Month": "January", "Cases": "40"},
                {"Year": "2011", "Onset Month": "February", "Cases": "60"},
                {"Year": "2012", "Onset Month": "January", "Cases": "60"},
                {"Year": "2012", "Onset Month": "February", "Cases": "40"},
            ],
        ),
        source_id="cdc_seasonality_month_2023",
    )

    rows = build_seasonality_baseline(observations)

    january = next(row for row in rows if row.period == 1)
    february = next(row for row in rows if row.period == 2)
    assert january.years_observed == 3
    assert january.mean_share == 0.4
    assert january.median_share == 0.4
    assert january.lower_80_share == 0.2
    assert january.upper_80_share == 0.6
    assert january.lower_95_share == 0.2
    assert january.upper_95_share == 0.6
    assert january.cumulative_mean_share == 0.4
    assert february.cumulative_mean_share == 1.0
    assert january.peak_rank == 2
    assert february.peak_rank == 1
    assert january.feature_quality_flags == (
        "national_curve_not_county_specific,shares_normalized_by_annual_total,"
        "empirical_prediction_band"
    )


def test_build_seasonality_baseline_scopes_rank_and_cumulative_by_source(
    tmp_path: Path,
) -> None:
    first_source = parse_cdc_lyme_monthly_onset(
        _write_csv(
            tmp_path / "monthly-first.csv",
            [
                {"Year": "2010", "Onset Month": "January", "Cases": "20"},
                {"Year": "2010", "Onset Month": "February", "Cases": "80"},
            ],
        ),
        source_id="first_source",
    )
    second_source = parse_cdc_lyme_monthly_onset(
        _write_csv(
            tmp_path / "monthly-second.csv",
            [
                {"Year": "2010", "Onset Month": "January", "Cases": "70"},
                {"Year": "2010", "Onset Month": "February", "Cases": "30"},
            ],
        ),
        source_id="second_source",
    )

    rows = build_seasonality_baseline([*first_source, *second_source])

    first_january = next(
        row for row in rows if row.source_id == "first_source" and row.period == 1
    )
    second_january = next(
        row for row in rows if row.source_id == "second_source" and row.period == 1
    )
    assert first_january.cumulative_mean_share == 0.2
    assert first_january.peak_rank == 2
    assert second_january.cumulative_mean_share == 0.7
    assert second_january.peak_rank == 1


def test_write_seasonality_outputs_orders_and_dedupes(tmp_path: Path) -> None:
    observations = parse_cdc_lyme_monthly_onset(
        _write_csv(
            tmp_path / "monthly.csv",
            [
                {"Year": "2010", "Onset Month": "January", "Cases": "20"},
                {"Year": "2010", "Onset Month": "February", "Cases": "80"},
                {"Year": "2011", "Onset Month": "January", "Cases": "40"},
                {"Year": "2011", "Onset Month": "February", "Cases": "60"},
            ],
        ),
        source_id="cdc_seasonality_month_2023",
    )
    baseline = build_seasonality_baseline(observations)

    outputs = write_seasonality_outputs(
        observations=observations,
        baseline_rows=baseline,
        output_dir=tmp_path / "out",
    )
    second_outputs = write_seasonality_outputs(
        observations=observations,
        baseline_rows=baseline,
        output_dir=tmp_path / "out",
        append=True,
    )

    assert second_outputs == outputs
    with outputs.observations_path.open(newline="", encoding="utf-8") as handle:
        observation_rows = list(csv.DictReader(handle))
    with outputs.baseline_path.open(newline="", encoding="utf-8") as handle:
        baseline_rows = list(csv.DictReader(handle))

    assert list(observation_rows[0]) == SEASONALITY_OBSERVATION_COLUMNS
    assert list(baseline_rows[0]) == SEASONALITY_BASELINE_COLUMNS
    assert len(observation_rows) == 4
    assert len(baseline_rows) == 2
    assert observation_rows[0]["period_label"] == "January"


def test_write_seasonality_outputs_dedupes_with_disease_in_key(tmp_path: Path) -> None:
    lyme_observations = parse_cdc_lyme_monthly_onset(
        _write_csv(
            tmp_path / "monthly.csv",
            [
                {"Year": "2010", "Onset Month": "January", "Cases": "20"},
                {"Year": "2010", "Onset Month": "February", "Cases": "80"},
            ],
        ),
        source_id="mixed_source",
    )
    anaplasmosis_observations = [
        replace(row, disease="anaplasmosis") for row in lyme_observations
    ]
    baseline = build_seasonality_baseline(
        [*lyme_observations, *anaplasmosis_observations]
    )

    outputs = write_seasonality_outputs(
        observations=[*lyme_observations, *anaplasmosis_observations],
        baseline_rows=baseline,
        output_dir=tmp_path / "out",
    )

    with outputs.observations_path.open(newline="", encoding="utf-8") as handle:
        observation_rows = list(csv.DictReader(handle))
    with outputs.baseline_path.open(newline="", encoding="utf-8") as handle:
        baseline_rows = list(csv.DictReader(handle))

    assert len(observation_rows) == 4
    assert len(baseline_rows) == 4
    assert {row["disease"] for row in observation_rows} == {
        "anaplasmosis",
        "lyme",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
