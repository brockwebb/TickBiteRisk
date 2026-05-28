from __future__ import annotations

import hashlib
import csv
import io
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from urllib.request import Request, urlopen


NOAA_CPC_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
NOAA_PSL_MEI_V2_URL = "https://psl.noaa.gov/data/correlation/meiv2.csv"
NOAA_PSL_MEI_V2_CITATION_URL = "https://psl.noaa.gov/enso/mei/"
ONI_SOURCE_ID = "noaa_cpc_oni"
MEI_V2_SOURCE_ID = "noaa_psl_mei_v2"
ONI_FEATURE_FLAGS = "global_climate_index,not_maryland_specific"
ONI_MODEL_YEAR_FEATURE_FLAGS = f"{ONI_FEATURE_FLAGS},prior_year_signal"
MEI_V2_FEATURE_FLAGS = "global_climate_index,not_maryland_specific,mei_v2_index"
MEI_V2_MODEL_YEAR_FEATURE_FLAGS = f"{MEI_V2_FEATURE_FLAGS},prior_year_signal"
ONI_SEASON_ORDER = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}


class OniInputError(ValueError):
    """Raised when the NOAA CPC ONI source table cannot be parsed."""


class MeiV2InputError(ValueError):
    """Raised when the NOAA PSL MEI.v2 source table cannot be parsed."""


@dataclass(frozen=True)
class OniSeason:
    season: str
    year: int
    total_sst_c: float
    oni_anomaly_c: float
    enso_phase: str
    source_id: str
    source_url_hash: str
    feature_quality_flags: str


@dataclass(frozen=True)
class OniModelYearFeatures:
    model_year: int
    oni_prior_year_season_count: int
    oni_prior_year_mean_anomaly_c: float | None
    oni_prior_year_max_anomaly_c: float | None
    oni_prior_year_min_anomaly_c: float | None
    oni_prior_year_el_nino_season_count: int
    oni_prior_year_la_nina_season_count: int
    source_ids: str
    source_url_hashes: str
    feature_quality_flags: str


@dataclass(frozen=True)
class MeiV2Month:
    month_start_date: str
    year: int
    month: int
    mei_v2_value: float | None
    mei_v2_phase: str
    source_id: str
    source_url_hash: str
    feature_quality_flags: str


@dataclass(frozen=True)
class MeiV2ModelYearFeatures:
    model_year: int
    mei_v2_prior_year_month_count: int
    mei_v2_prior_year_mean: float | None
    mei_v2_prior_year_max: float | None
    mei_v2_prior_year_min: float | None
    mei_v2_prior_year_positive_month_count: int
    mei_v2_prior_year_negative_month_count: int
    source_ids: str
    source_url_hashes: str
    feature_quality_flags: str


def fetch_oni_text(url: str = NOAA_CPC_ONI_URL) -> str:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def fetch_mei_v2_text(url: str = NOAA_PSL_MEI_V2_URL) -> str:
    request = Request(url, headers={"User-Agent": "tickbiterisk-etl/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8-sig")


def parse_oni_ascii_text(text: str, *, source_url: str) -> list[OniSeason]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    rows = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("SEAS"):
            continue
        parts = stripped.split()
        if len(parts) != 4:
            raise OniInputError(f"malformed ONI row at line {line_number}: {line}")
        season, year, total, anomaly = parts
        if season not in ONI_SEASON_ORDER:
            raise OniInputError(f"unsupported ONI season at line {line_number}: {season}")
        rows.append(
            OniSeason(
                season=season,
                year=int(year),
                total_sst_c=float(total),
                oni_anomaly_c=float(anomaly),
                enso_phase=_enso_phase(float(anomaly)),
                source_id=ONI_SOURCE_ID,
                source_url_hash=source_url_hash,
                feature_quality_flags=ONI_FEATURE_FLAGS,
            )
        )
    if not rows:
        raise OniInputError("no ONI season rows found")
    keyed = {(row.year, row.season): row for row in rows}
    return sorted(
        keyed.values(),
        key=lambda row: (row.year, ONI_SEASON_ORDER[row.season]),
    )


def build_oni_model_year_features(
    rows: list[OniSeason],
) -> list[OniModelYearFeatures]:
    grouped: dict[int, list[OniSeason]] = defaultdict(list)
    for row in rows:
        grouped[row.year].append(row)

    features = []
    for prior_year, prior_year_rows in grouped.items():
        ordered = sorted(
            prior_year_rows,
            key=lambda row: ONI_SEASON_ORDER[row.season],
        )
        if {row.season for row in ordered} != set(ONI_SEASON_ORDER):
            continue
        anomalies = [row.oni_anomaly_c for row in ordered]
        features.append(
            OniModelYearFeatures(
                model_year=prior_year + 1,
                oni_prior_year_season_count=len(ordered),
                oni_prior_year_mean_anomaly_c=_mean(anomalies),
                oni_prior_year_max_anomaly_c=max(anomalies) if anomalies else None,
                oni_prior_year_min_anomaly_c=min(anomalies) if anomalies else None,
                oni_prior_year_el_nino_season_count=sum(
                    1 for row in ordered if row.enso_phase == "el_nino"
                ),
                oni_prior_year_la_nina_season_count=sum(
                    1 for row in ordered if row.enso_phase == "la_nina"
                ),
                source_ids=",".join(sorted({row.source_id for row in ordered})),
                source_url_hashes=",".join(
                    sorted({row.source_url_hash for row in ordered})
                ),
                feature_quality_flags=ONI_MODEL_YEAR_FEATURE_FLAGS,
            )
        )
    return sorted(features, key=lambda row: row.model_year)


def parse_mei_v2_csv_text(text: str, *, source_url: str) -> list[MeiV2Month]:
    source_url_hash = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    reader = csv.reader(io.StringIO(text))
    rows = []
    for line_number, parts in enumerate(reader, start=1):
        if not parts or not parts[0].strip():
            continue
        first = parts[0].strip()
        if first.lower() == "date":
            continue
        if len(parts) < 2:
            raise MeiV2InputError(f"malformed MEI.v2 row at line {line_number}: {parts}")
        try:
            month_start = date.fromisoformat(first)
        except ValueError as exc:
            raise MeiV2InputError(
                f"unsupported MEI.v2 date at line {line_number}: {first}"
            ) from exc
        if month_start.day != 1:
            raise MeiV2InputError(
                f"MEI.v2 date must be first of month at line {line_number}: {first}"
            )
        raw_value = parts[1].strip()
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise MeiV2InputError(
                f"unsupported MEI.v2 value at line {line_number}: {raw_value}"
            ) from exc
        flags = [MEI_V2_FEATURE_FLAGS]
        parsed_value = None if value <= -999 else value
        if parsed_value is None:
            flags.append("missing_value")
        rows.append(
            MeiV2Month(
                month_start_date=month_start.isoformat(),
                year=month_start.year,
                month=month_start.month,
                mei_v2_value=parsed_value,
                mei_v2_phase=_mei_v2_phase(parsed_value),
                source_id=MEI_V2_SOURCE_ID,
                source_url_hash=source_url_hash,
                feature_quality_flags=",".join(flags),
            )
        )
    if not rows:
        raise MeiV2InputError("no MEI.v2 monthly rows found")
    keyed = {(row.year, row.month): row for row in rows}
    return sorted(keyed.values(), key=lambda row: (row.year, row.month))


def build_mei_v2_model_year_features(
    rows: list[MeiV2Month],
) -> list[MeiV2ModelYearFeatures]:
    grouped: dict[int, list[MeiV2Month]] = defaultdict(list)
    for row in rows:
        grouped[row.year].append(row)

    features = []
    for prior_year, prior_year_rows in grouped.items():
        ordered = sorted(prior_year_rows, key=lambda row: row.month)
        if {row.month for row in ordered} != set(range(1, 13)):
            continue
        if any(row.mei_v2_value is None for row in ordered):
            continue
        values = [row.mei_v2_value for row in ordered if row.mei_v2_value is not None]
        features.append(
            MeiV2ModelYearFeatures(
                model_year=prior_year + 1,
                mei_v2_prior_year_month_count=len(ordered),
                mei_v2_prior_year_mean=_mean(values),
                mei_v2_prior_year_max=max(values) if values else None,
                mei_v2_prior_year_min=min(values) if values else None,
                mei_v2_prior_year_positive_month_count=sum(
                    1 for row in ordered if row.mei_v2_phase == "positive"
                ),
                mei_v2_prior_year_negative_month_count=sum(
                    1 for row in ordered if row.mei_v2_phase == "negative"
                ),
                source_ids=",".join(sorted({row.source_id for row in ordered})),
                source_url_hashes=",".join(
                    sorted({row.source_url_hash for row in ordered})
                ),
                feature_quality_flags=MEI_V2_MODEL_YEAR_FEATURE_FLAGS,
            )
        )
    return sorted(features, key=lambda row: row.model_year)


def fetch_and_parse_oni(
    *,
    source_url: str = NOAA_CPC_ONI_URL,
    fetcher: Callable[[str], str] = fetch_oni_text,
) -> list[OniSeason]:
    return parse_oni_ascii_text(fetcher(source_url), source_url=source_url)


def fetch_and_parse_mei_v2(
    *,
    source_url: str = NOAA_PSL_MEI_V2_URL,
    fetcher: Callable[[str], str] = fetch_mei_v2_text,
) -> list[MeiV2Month]:
    return parse_mei_v2_csv_text(fetcher(source_url), source_url=source_url)


def _enso_phase(anomaly: float) -> str:
    if anomaly >= 0.5:
        return "el_nino"
    if anomaly <= -0.5:
        return "la_nina"
    return "neutral"


def _mei_v2_phase(value: float | None) -> str:
    if value is None:
        return "missing"
    if value >= 0.5:
        return "positive"
    if value <= -0.5:
        return "negative"
    return "neutral"


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)
