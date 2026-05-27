import pytest

from datetime import date

from tickbiterisk.etl.noaa import (
    NOAA_CDO_ENDPOINT,
    NOAA_GHCND_DAILY_TYPES,
    NoaaTokenMissingError,
    build_noaa_daily_data_url,
    build_noaa_station_url,
    fetch_noaa_daily_observations,
    fetch_noaa_stations,
    parse_noaa_daily_data_response,
    parse_noaa_station_response,
    select_long_coverage_stations,
    get_noaa_token,
)


def test_get_noaa_token_reads_provided_env_mapping() -> None:
    assert get_noaa_token({"NOAA_TOKEN": "  test-token  "}) == "test-token"


def test_get_noaa_token_raises_without_leaking_secret() -> None:
    fake_secret = "fake-noaa-secret-value"

    with pytest.raises(NoaaTokenMissingError) as exc_info:
        get_noaa_token({"NOAA_TOKEN": "   ", "OTHER_SECRET": fake_secret})

    message = str(exc_info.value)
    assert message == "NOAA_TOKEN is required for NOAA CDO validation"
    assert fake_secret not in message


def test_build_noaa_station_url_targets_county_ghcnd_stations() -> None:
    url = build_noaa_station_url(
        county_fips="24003",
        start_date=date(1992, 1, 1),
        end_date=date(2026, 5, 24),
    )

    assert url.startswith(f"{NOAA_CDO_ENDPOINT}/stations?")
    assert "datasetid=GHCND" in url
    assert "locationid=FIPS%3A24003" in url
    assert "startdate=1992-01-01" in url
    assert "enddate=2026-05-24" in url
    assert "limit=1000" in url


def test_build_noaa_daily_data_url_requests_expected_daily_types() -> None:
    url = build_noaa_daily_data_url(
        station_id="GHCND:USW00093721",
        start_date=date(1992, 5, 1),
        end_date=date(1992, 5, 7),
    )

    assert url.startswith(f"{NOAA_CDO_ENDPOINT}/data?")
    assert "datasetid=GHCND" in url
    assert "stationid=GHCND%3AUSW00093721" in url
    assert "startdate=1992-05-01" in url
    assert "enddate=1992-05-07" in url
    assert "units=standard" in url
    for datatype in NOAA_GHCND_DAILY_TYPES:
        assert f"datatypeid={datatype}" in url


def test_parse_noaa_station_response_maps_station_metadata() -> None:
    payload = {
        "results": [
            {
                "id": "GHCND:USW00093721",
                "name": "BALTIMORE WASHINGTON INTERNATIONAL AIRPORT, MD US",
                "latitude": 39.1733,
                "longitude": -76.684,
                "elevation": 47.5,
                "elevationUnit": "METERS",
                "mindate": "1939-07-01",
                "maxdate": "2026-05-20",
                "datacoverage": 0.9999,
            }
        ]
    }

    stations = parse_noaa_station_response(payload, county_fips="24003")

    assert len(stations) == 1
    assert stations[0].county_fips == "24003"
    assert stations[0].station_id == "GHCND:USW00093721"
    assert stations[0].name == "BALTIMORE WASHINGTON INTERNATIONAL AIRPORT, MD US"
    assert stations[0].mindate == date(1939, 7, 1)
    assert stations[0].maxdate == date(2026, 5, 20)
    assert stations[0].data_coverage == 0.9999


def test_select_long_coverage_stations_prioritizes_coverage_and_span() -> None:
    stations = parse_noaa_station_response(
        {
            "results": [
                {
                    "id": "GHCND:SHORT",
                    "name": "SHORT",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "2012-01-01",
                    "maxdate": "2026-01-01",
                    "datacoverage": 1.0,
                },
                {
                    "id": "GHCND:LOWCOVERAGE",
                    "name": "LOW COVERAGE",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "1939-01-01",
                    "maxdate": "2026-01-01",
                    "datacoverage": 0.40,
                },
                {
                    "id": "GHCND:BWI",
                    "name": "BWI",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "1939-01-01",
                    "maxdate": "2026-01-01",
                    "datacoverage": 0.9999,
                },
            ]
        },
        county_fips="24003",
    )

    selected = select_long_coverage_stations(
        stations,
        start_date=date(1992, 1, 1),
        end_date=date(2026, 1, 1),
        min_data_coverage=0.5,
    )

    assert [station.station_id for station in selected] == ["GHCND:BWI"]


def test_select_long_coverage_stations_can_allow_current_data_lag() -> None:
    stations = parse_noaa_station_response(
        {
            "results": [
                {
                    "id": "GHCND:BWI",
                    "name": "BWI",
                    "latitude": 39.0,
                    "longitude": -76.0,
                    "mindate": "1939-01-01",
                    "maxdate": "2026-05-20",
                    "datacoverage": 0.9999,
                }
            ]
        },
        county_fips="24003",
    )

    selected = select_long_coverage_stations(
        stations,
        start_date=date(1992, 1, 1),
        end_date=date(2026, 5, 24),
        max_end_lag_days=7,
    )

    assert [station.station_id for station in selected] == ["GHCND:BWI"]


def test_parse_noaa_daily_data_response_pivots_datatypes_by_date() -> None:
    payload = {
        "results": [
            {
                "date": "1992-05-01T00:00:00",
                "datatype": "TMAX",
                "station": "GHCND:USW00093721",
                "value": 72.0,
            },
            {
                "date": "1992-05-01T00:00:00",
                "datatype": "TMIN",
                "station": "GHCND:USW00093721",
                "value": 44.0,
            },
            {
                "date": "1992-05-01T00:00:00",
                "datatype": "PRCP",
                "station": "GHCND:USW00093721",
                "value": 0.01,
            },
            {
                "date": "1992-05-02T00:00:00",
                "datatype": "SNOW",
                "station": "GHCND:USW00093721",
                "value": 0.0,
            },
        ]
    }

    rows = parse_noaa_daily_data_response(
        payload,
        county_fips="24003",
        source_url="https://example.test/noaa",
    )

    assert len(rows) == 2
    assert rows[0].county_fips == "24003"
    assert rows[0].station_id == "GHCND:USW00093721"
    assert rows[0].date == date(1992, 5, 1)
    assert rows[0].tmax_f == 72.0
    assert rows[0].tmin_f == 44.0
    assert rows[0].prcp_inches == 0.01
    assert rows[0].snow_inches is None
    assert rows[0].source == "noaa_cdo_ghcnd_daily"
    assert len(rows[0].source_url_hash) == 64
    assert rows[1].snow_inches == 0.0


def test_fetch_noaa_stations_uses_injected_json_get() -> None:
    calls: list[tuple[str, str]] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append((url, token))
        return {
            "results": [
                {
                    "id": "GHCND:USW00093721",
                    "name": "BWI",
                    "latitude": 39.1733,
                    "longitude": -76.684,
                    "mindate": "1939-07-01",
                    "maxdate": "2026-05-20",
                    "datacoverage": 0.9999,
                }
            ]
        }

    rows = fetch_noaa_stations(
        "24003",
        date(1992, 1, 1),
        date(2026, 5, 24),
        token="token-value",
        json_get=fake_json_get,
    )

    assert calls[0][1] == "token-value"
    assert "stations?" in calls[0][0]
    assert rows[0].station_id == "GHCND:USW00093721"


def test_fetch_noaa_stations_paginates_metadata_resultset() -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        if "offset=3" in url:
            return {
                "metadata": {"resultset": {"offset": 3, "count": 3, "limit": 2}},
                "results": [
                    {
                        "id": "GHCND:THIRD",
                        "name": "THIRD",
                        "latitude": 39.3,
                        "longitude": -76.3,
                        "mindate": "1950-01-01",
                        "maxdate": "2026-01-01",
                        "datacoverage": 0.8,
                    }
                ],
            }
        return {
            "metadata": {"resultset": {"offset": 1, "count": 3, "limit": 2}},
            "results": [
                {
                    "id": "GHCND:FIRST",
                    "name": "FIRST",
                    "latitude": 39.1,
                    "longitude": -76.1,
                    "mindate": "1940-01-01",
                    "maxdate": "2026-01-01",
                    "datacoverage": 0.9,
                },
                {
                    "id": "GHCND:SECOND",
                    "name": "SECOND",
                    "latitude": 39.2,
                    "longitude": -76.2,
                    "mindate": "1945-01-01",
                    "maxdate": "2026-01-01",
                    "datacoverage": 0.85,
                },
            ],
        }

    rows = fetch_noaa_stations(
        "24003",
        date(1992, 1, 1),
        date(2026, 5, 24),
        token="token-value",
        json_get=fake_json_get,
    )

    assert len(calls) == 2
    assert [row.station_id for row in rows] == [
        "GHCND:FIRST",
        "GHCND:SECOND",
        "GHCND:THIRD",
    ]


def test_fetch_noaa_daily_observations_uses_injected_json_get() -> None:
    calls: list[tuple[str, str]] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append((url, token))
        return {
            "results": [
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": "GHCND:USW00093721",
                    "value": 72.0,
                }
            ]
        }

    rows = fetch_noaa_daily_observations(
        "24003",
        "GHCND:USW00093721",
        date(1992, 5, 1),
        date(1992, 5, 1),
        token="token-value",
        json_get=fake_json_get,
    )

    assert calls[0][1] == "token-value"
    assert "data?" in calls[0][0]
    assert rows[0].tmax_f == 72.0


def test_fetch_noaa_daily_observations_paginates_before_pivoting_datatypes() -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        if "offset=3" in url:
            return {
                "metadata": {"resultset": {"offset": 3, "count": 3, "limit": 2}},
                "results": [
                    {
                        "date": "1992-05-01T00:00:00",
                        "datatype": "PRCP",
                        "station": "GHCND:USW00093721",
                        "value": 0.01,
                    }
                ],
            }
        return {
            "metadata": {"resultset": {"offset": 1, "count": 3, "limit": 2}},
            "results": [
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": "GHCND:USW00093721",
                    "value": 72.0,
                },
                {
                    "date": "1992-05-01T00:00:00",
                    "datatype": "TMIN",
                    "station": "GHCND:USW00093721",
                    "value": 44.0,
                },
            ],
        }

    rows = fetch_noaa_daily_observations(
        "24003",
        "GHCND:USW00093721",
        date(1992, 5, 1),
        date(1992, 5, 1),
        token="token-value",
        json_get=fake_json_get,
    )

    assert len(calls) == 2
    assert len(rows) == 1
    assert rows[0].tmax_f == 72.0
    assert rows[0].tmin_f == 44.0
    assert rows[0].prcp_inches == 0.01


def test_fetch_noaa_daily_observations_splits_multi_year_requests() -> None:
    calls: list[str] = []

    def fake_json_get(url: str, token: str) -> dict:
        calls.append(url)
        if "startdate=1992-01-01" in url:
            return {
                "results": [
                    {
                        "date": "1992-05-01T00:00:00",
                        "datatype": "TMAX",
                        "station": "GHCND:USW00093721",
                        "value": 72.0,
                    }
                ]
            }
        return {
            "results": [
                {
                    "date": "1993-05-01T00:00:00",
                    "datatype": "TMAX",
                    "station": "GHCND:USW00093721",
                    "value": 75.0,
                }
            ]
        }

    rows = fetch_noaa_daily_observations(
        "24003",
        "GHCND:USW00093721",
        date(1992, 1, 1),
        date(1993, 12, 31),
        token="token-value",
        json_get=fake_json_get,
    )

    assert len(calls) == 2
    assert "startdate=1992-01-01" in calls[0]
    assert "enddate=1992-12-31" in calls[0]
    assert "startdate=1993-01-01" in calls[1]
    assert "enddate=1993-12-31" in calls[1]
    assert [row.date for row in rows] == [date(1992, 5, 1), date(1993, 5, 1)]
