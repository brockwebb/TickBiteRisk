from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


CLINICAL_DISCLAIMER = (
    "TickBiteRisk is for informational and educational purposes only. It is not "
    "medical advice, does not diagnose disease, and does not determine whether "
    "you are infected. Follow CDC guidance and contact a qualified healthcare "
    "professional about your situation."
)

GUIDANCE_LINKS = [
    {
        "title": "CDC: What to do after a tick bite",
        "url": "https://www.cdc.gov/ticks/after-a-tick-bite/index.html",
    },
    {
        "title": "CDC: Preventing tick bites",
        "url": "https://www.cdc.gov/ticks/prevention/index.html",
    },
    {
        "title": "CDC: Lyme disease signs and symptoms",
        "url": "https://www.cdc.gov/lyme/signs-symptoms/index.html",
    },
]

REQUIRED_SCORE_COLUMNS = [
    "source_prediction_run_id",
    "source_prediction_sha256",
    "source_seasonality_sha256",
    "model_name",
    "county_fips",
    "county_name",
    "year",
    "mmwr_week",
    "period_label",
    "predicted_annual_incidence_per_100k",
    "predicted_annual_cases",
    "seasonal_mean_share",
    "seasonal_lower_80_share",
    "seasonal_upper_80_share",
    "seasonal_lower_95_share",
    "seasonal_upper_95_share",
    "predicted_weekly_incidence_per_100k",
    "lower_80_weekly_incidence_per_100k",
    "upper_80_weekly_incidence_per_100k",
    "lower_95_weekly_incidence_per_100k",
    "upper_95_weekly_incidence_per_100k",
    "predicted_weekly_cases",
    "benchmark_quantile",
    "headroom_multiplier",
    "score_denominator",
    "risk_score_raw",
    "risk_score",
    "risk_category",
    "seasonality_source_id",
    "feature_quality_flags",
    "backtest_assumption_flags",
]


class RiskLookupInputError(ValueError):
    """Raised when runtime risk lookup inputs are invalid or unavailable."""


@dataclass(frozen=True)
class CountyWeekRiskRecord:
    source_prediction_run_id: str
    source_prediction_sha256: str
    source_seasonality_sha256: str
    model_name: str
    county_fips: str
    county_name: str
    year: int
    mmwr_week: int
    period_label: str
    predicted_annual_incidence_per_100k: float
    predicted_annual_cases: float
    seasonal_mean_share: float
    seasonal_lower_80_share: float
    seasonal_upper_80_share: float
    seasonal_lower_95_share: float
    seasonal_upper_95_share: float
    predicted_weekly_incidence_per_100k: float
    lower_80_weekly_incidence_per_100k: float
    upper_80_weekly_incidence_per_100k: float
    lower_95_weekly_incidence_per_100k: float
    upper_95_weekly_incidence_per_100k: float
    predicted_weekly_cases: float
    benchmark_quantile: float
    headroom_multiplier: float
    score_denominator: float
    risk_score_raw: float
    risk_score: int
    risk_category: str
    seasonality_source_id: str
    feature_quality_flags: str
    backtest_assumption_flags: str


@dataclass(frozen=True)
class CountyWeekRiskResponse:
    county_fips: str
    county_name: str
    query_date: str
    mmwr_year: int
    mmwr_week: int
    data_year: int
    model_name: str
    seasonality_source_id: str
    period_label: str
    risk_score: int
    risk_category: str
    risk_score_raw: float
    predicted_weekly_incidence_per_100k: float
    predicted_weekly_incidence_80_interval: list[float]
    predicted_weekly_incidence_95_interval: list[float]
    predicted_weekly_cases: float
    predicted_annual_incidence_per_100k: float
    score_scale: dict[str, float]
    source_metadata: dict[str, str]
    feature_quality_flags: list[str]
    backtest_assumption_flags: list[str]
    data_quality_flags: list[str]
    score_interpretation: str
    clinical_disclaimer: str
    guidance_links: list[dict[str, str]]


class RiskLookupStore:
    def __init__(self, records: list[CountyWeekRiskRecord]) -> None:
        self._records = records
        self._by_county_week: dict[
            tuple[str, str, str, int], list[CountyWeekRiskRecord]
        ] = {}
        for record in records:
            key = (
                record.county_fips,
                record.model_name,
                record.seasonality_source_id,
                record.mmwr_week,
            )
            self._by_county_week.setdefault(key, []).append(record)
        for rows in self._by_county_week.values():
            rows.sort(key=lambda row: row.year)

    @classmethod
    def from_csv(cls, scores_path: Path) -> RiskLookupStore:
        return cls(_read_score_records(scores_path))

    def lookup(
        self,
        *,
        county_fips: str,
        query_date: str | date,
        model_name: str = "linear_blend_baseline",
        seasonality_source_id: str = "cdc_seasonality_week_2023",
        benchmark_quantile: float | None = None,
        headroom_multiplier: float | None = None,
        source_prediction_run_id: str | None = None,
        source_prediction_sha256: str | None = None,
        source_seasonality_sha256: str | None = None,
    ) -> CountyWeekRiskResponse:
        normalized_fips = _normalize_fips(county_fips)
        parsed_date = _parse_date(query_date)
        mmwr_year, week = mmwr_year_week(parsed_date)
        county_records = [
            record
            for record in self._records
            if record.county_fips == normalized_fips
            and record.model_name == model_name
            and record.seasonality_source_id == seasonality_source_id
        ]
        if not county_records:
            raise RiskLookupInputError(
                f"No risk baseline rows found for county_fips={normalized_fips}"
            )

        key = (normalized_fips, model_name, seasonality_source_id, week)
        week_records = self._by_county_week.get(key, [])
        if benchmark_quantile is not None:
            week_records = [
                record
                for record in week_records
                if record.benchmark_quantile == benchmark_quantile
            ]
        if headroom_multiplier is not None:
            week_records = [
                record
                for record in week_records
                if record.headroom_multiplier == headroom_multiplier
            ]
        if source_prediction_run_id is not None:
            week_records = [
                record
                for record in week_records
                if record.source_prediction_run_id == source_prediction_run_id
            ]
        if source_prediction_sha256 is not None:
            week_records = [
                record
                for record in week_records
                if record.source_prediction_sha256 == source_prediction_sha256
            ]
        if source_seasonality_sha256 is not None:
            week_records = [
                record
                for record in week_records
                if record.source_seasonality_sha256 == source_seasonality_sha256
            ]
        if not week_records:
            raise RiskLookupInputError(
                "No risk baseline row found for "
                f"county_fips={normalized_fips}, mmwr_week={week}"
            )
        scale_configs = {
            (record.benchmark_quantile, record.headroom_multiplier)
            for record in week_records
        }
        if len(scale_configs) > 1:
            raise RiskLookupInputError(
                "Multiple risk score scale configurations found; provide "
                "benchmark_quantile and headroom_multiplier"
            )
        source_configs = {
            (
                record.source_prediction_run_id,
                record.source_prediction_sha256,
                record.source_seasonality_sha256,
            )
            for record in week_records
        }
        if len(source_configs) > 1:
            raise RiskLookupInputError(
                "Multiple risk score source versions found; provide "
                "source_prediction_run_id, source_prediction_sha256, or "
                "source_seasonality_sha256"
            )

        exact_records = [record for record in week_records if record.year == mmwr_year]
        if len(exact_records) > 1:
            raise RiskLookupInputError(
                "Multiple risk baseline rows found for selected county, week, "
                "year, and score scale"
            )
        exact_record = exact_records[0] if exact_records else None
        data_quality_flags = ["relative_seasonal_baseline"]
        if exact_record is None:
            record = week_records[-1]
            data_quality_flags.extend(
                ["requested_year_unavailable", "using_latest_available_year"]
            )
        else:
            record = exact_record
            data_quality_flags.append("exact_baseline_year")

        return CountyWeekRiskResponse(
            county_fips=record.county_fips,
            county_name=record.county_name,
            query_date=parsed_date.isoformat(),
            mmwr_year=mmwr_year,
            mmwr_week=week,
            data_year=record.year,
            model_name=record.model_name,
            seasonality_source_id=record.seasonality_source_id,
            period_label=record.period_label,
            risk_score=record.risk_score,
            risk_category=record.risk_category,
            risk_score_raw=record.risk_score_raw,
            predicted_weekly_incidence_per_100k=(
                record.predicted_weekly_incidence_per_100k
            ),
            predicted_weekly_incidence_80_interval=[
                record.lower_80_weekly_incidence_per_100k,
                record.upper_80_weekly_incidence_per_100k,
            ],
            predicted_weekly_incidence_95_interval=[
                record.lower_95_weekly_incidence_per_100k,
                record.upper_95_weekly_incidence_per_100k,
            ],
            predicted_weekly_cases=record.predicted_weekly_cases,
            predicted_annual_incidence_per_100k=(
                record.predicted_annual_incidence_per_100k
            ),
            score_scale={
                "benchmark_quantile": record.benchmark_quantile,
                "headroom_multiplier": record.headroom_multiplier,
                "score_denominator": record.score_denominator,
            },
            source_metadata={
                "source_prediction_run_id": record.source_prediction_run_id,
                "source_prediction_sha256": record.source_prediction_sha256,
                "source_seasonality_sha256": record.source_seasonality_sha256,
            },
            feature_quality_flags=_split_flags(record.feature_quality_flags),
            backtest_assumption_flags=_split_flags(record.backtest_assumption_flags),
            data_quality_flags=data_quality_flags,
            score_interpretation=(
                "Relative seasonal Lyme baseline on a 1-10 scale. This is not "
                "a per-bite infection probability, diagnosis, treatment "
                "recommendation, or weather-adjusted forecast."
            ),
            clinical_disclaimer=CLINICAL_DISCLAIMER,
            guidance_links=GUIDANCE_LINKS,
        )


def mmwr_year_week(value: str | date) -> tuple[int, int]:
    parsed_date = _parse_date(value)
    year_start = _mmwr_year_start(parsed_date.year)
    next_year_start = _mmwr_year_start(parsed_date.year + 1)
    if parsed_date < year_start:
        mmwr_year = parsed_date.year - 1
    elif parsed_date >= next_year_start:
        mmwr_year = parsed_date.year + 1
    else:
        mmwr_year = parsed_date.year
    week = ((parsed_date - _mmwr_year_start(mmwr_year)).days // 7) + 1
    return mmwr_year, week


def _read_score_records(path: Path) -> list[CountyWeekRiskRecord]:
    rows = _read_csv(path, required_columns=REQUIRED_SCORE_COLUMNS)
    records = [_score_record_from_row(row) for row in rows]
    if not records:
        raise RiskLookupInputError("Risk score file has no data rows")
    return records


def _score_record_from_row(row: dict[str, str]) -> CountyWeekRiskRecord:
    return CountyWeekRiskRecord(
        source_prediction_run_id=row["source_prediction_run_id"],
        source_prediction_sha256=row["source_prediction_sha256"],
        source_seasonality_sha256=row["source_seasonality_sha256"],
        model_name=row["model_name"],
        county_fips=_normalize_fips(row["county_fips"]),
        county_name=row["county_name"],
        year=_parse_int(row["year"], "year"),
        mmwr_week=_parse_week(row["mmwr_week"]),
        period_label=row["period_label"],
        predicted_annual_incidence_per_100k=_parse_float(
            row["predicted_annual_incidence_per_100k"],
            "predicted_annual_incidence_per_100k",
        ),
        predicted_annual_cases=_parse_float(
            row["predicted_annual_cases"],
            "predicted_annual_cases",
        ),
        seasonal_mean_share=_parse_float(row["seasonal_mean_share"], "seasonal_mean_share"),
        seasonal_lower_80_share=_parse_float(
            row["seasonal_lower_80_share"],
            "seasonal_lower_80_share",
        ),
        seasonal_upper_80_share=_parse_float(
            row["seasonal_upper_80_share"],
            "seasonal_upper_80_share",
        ),
        seasonal_lower_95_share=_parse_float(
            row["seasonal_lower_95_share"],
            "seasonal_lower_95_share",
        ),
        seasonal_upper_95_share=_parse_float(
            row["seasonal_upper_95_share"],
            "seasonal_upper_95_share",
        ),
        predicted_weekly_incidence_per_100k=_parse_float(
            row["predicted_weekly_incidence_per_100k"],
            "predicted_weekly_incidence_per_100k",
        ),
        lower_80_weekly_incidence_per_100k=_parse_float(
            row["lower_80_weekly_incidence_per_100k"],
            "lower_80_weekly_incidence_per_100k",
        ),
        upper_80_weekly_incidence_per_100k=_parse_float(
            row["upper_80_weekly_incidence_per_100k"],
            "upper_80_weekly_incidence_per_100k",
        ),
        lower_95_weekly_incidence_per_100k=_parse_float(
            row["lower_95_weekly_incidence_per_100k"],
            "lower_95_weekly_incidence_per_100k",
        ),
        upper_95_weekly_incidence_per_100k=_parse_float(
            row["upper_95_weekly_incidence_per_100k"],
            "upper_95_weekly_incidence_per_100k",
        ),
        predicted_weekly_cases=_parse_float(
            row["predicted_weekly_cases"],
            "predicted_weekly_cases",
        ),
        benchmark_quantile=_parse_float(row["benchmark_quantile"], "benchmark_quantile"),
        headroom_multiplier=_parse_float(
            row["headroom_multiplier"],
            "headroom_multiplier",
        ),
        score_denominator=_parse_float(row["score_denominator"], "score_denominator"),
        risk_score_raw=_parse_float(row["risk_score_raw"], "risk_score_raw"),
        risk_score=_parse_score(row["risk_score"]),
        risk_category=row["risk_category"],
        seasonality_source_id=row["seasonality_source_id"],
        feature_quality_flags=row["feature_quality_flags"],
        backtest_assumption_flags=row["backtest_assumption_flags"],
    )


def _read_csv(path: Path, *, required_columns: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_columns = [
            column for column in required_columns if column not in fieldnames
        ]
        if missing_columns:
            raise RiskLookupInputError(
                "missing required risk lookup column(s): "
                f"{', '.join(missing_columns)}"
            )
        return list(reader)


def _mmwr_year_start(year: int) -> date:
    jan4 = date(year, 1, 4)
    return jan4 - timedelta(days=(jan4.weekday() + 1) % 7)


def _normalize_fips(value: str) -> str:
    normalized = str(value).strip().zfill(5)
    if len(normalized) != 5 or not normalized.isdigit():
        raise RiskLookupInputError("county_fips must be a 5-digit FIPS code")
    return normalized


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RiskLookupInputError("query_date must use YYYY-MM-DD format") from exc


def _parse_int(value: str, field_name: str) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise RiskLookupInputError(f"{field_name} must be an integer") from exc


def _parse_week(value: str) -> int:
    week = _parse_int(value, "mmwr_week")
    if week < 1 or week > 53:
        raise RiskLookupInputError("mmwr_week must be between 1 and 53")
    return week


def _parse_score(value: str) -> int:
    score = _parse_int(value, "risk_score")
    if score < 1 or score > 10:
        raise RiskLookupInputError("risk_score must be between 1 and 10")
    return score


def _parse_float(value: str, field_name: str) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise RiskLookupInputError(f"{field_name} must be numeric") from exc


def _split_flags(value: str) -> list[str]:
    return [flag.strip() for flag in str(value).split(",") if flag.strip()]
