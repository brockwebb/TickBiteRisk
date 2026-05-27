from tickbiterisk import __version__
from tickbiterisk.etl.maryland import load_maryland_jurisdictions


def test_package_version_is_exposed() -> None:
    assert __version__ == "0.1.0"


def test_maryland_reference_has_24_jurisdictions() -> None:
    jurisdictions = load_maryland_jurisdictions()
    assert len(jurisdictions) == 24
    assert {row.county_fips for row in jurisdictions} >= {"24003", "24510"}


def test_anne_arundel_reference_supports_zip_21146_use_case() -> None:
    jurisdictions = load_maryland_jurisdictions()
    anne_arundel = next(row for row in jurisdictions if row.county_fips == "24003")
    assert anne_arundel.county_name == "Anne Arundel County"
    assert anne_arundel.state == "MD"
