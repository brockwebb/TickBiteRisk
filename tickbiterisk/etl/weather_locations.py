from __future__ import annotations

import csv
from dataclasses import dataclass
from importlib.resources import files

from tickbiterisk.etl.maryland import maryland_fips_set


@dataclass(frozen=True)
class WeatherLocation:
    county_fips: str
    state_fips: str
    state: str
    county_name: str
    centroid_lat: float
    centroid_lon: float
    geography_source: str


def load_maryland_weather_locations() -> list[WeatherLocation]:
    resource = files("tickbiterisk.resources").joinpath(
        "maryland_weather_locations.csv"
    )
    with resource.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    locations = [
        WeatherLocation(
            county_fips=str(row["county_fips"]).zfill(5),
            state_fips=str(row["state_fips"]).zfill(2),
            state=row["state"],
            county_name=row["county_name"],
            centroid_lat=float(row["centroid_lat"]),
            centroid_lon=float(row["centroid_lon"]),
            geography_source=row["geography_source"],
        )
        for row in rows
    ]

    fips = {row.county_fips for row in locations}
    expected = maryland_fips_set()
    if len(locations) != 24 or fips != expected:
        missing = sorted(expected - fips)
        extra = sorted(fips - expected)
        raise ValueError(
            "Weather location resource must match Maryland jurisdictions; "
            f"missing={missing}, extra={extra}, count={len(locations)}"
        )
    return locations
