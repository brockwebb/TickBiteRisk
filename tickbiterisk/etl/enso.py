from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from urllib.request import Request, urlopen


NOAA_CPC_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
ONI_SOURCE_ID = "noaa_cpc_oni"
ONI_FEATURE_FLAGS = "global_climate_index,not_maryland_specific"
ONI_MODEL_YEAR_FEATURE_FLAGS = f"{ONI_FEATURE_FLAGS},prior_year_signal"
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


def fetch_oni_text(url: str = NOAA_CPC_ONI_URL) -> str:
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


def fetch_and_parse_oni(
    *,
    source_url: str = NOAA_CPC_ONI_URL,
    fetcher: Callable[[str], str] = fetch_oni_text,
) -> list[OniSeason]:
    return parse_oni_ascii_text(fetcher(source_url), source_url=source_url)


def _enso_phase(anomaly: float) -> str:
    if anomaly >= 0.5:
        return "el_nino"
    if anomaly <= -0.5:
        return "la_nina"
    return "neutral"


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)
