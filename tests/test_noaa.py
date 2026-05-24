import pytest

from tickbiterisk.etl.noaa import NoaaTokenMissingError, get_noaa_token


def test_get_noaa_token_reads_provided_env_mapping() -> None:
    assert get_noaa_token({"NOAA_TOKEN": "  test-token  "}) == "test-token"


def test_get_noaa_token_raises_without_leaking_secret() -> None:
    fake_secret = "fake-noaa-secret-value"

    with pytest.raises(NoaaTokenMissingError) as exc_info:
        get_noaa_token({"NOAA_TOKEN": "   ", "OTHER_SECRET": fake_secret})

    message = str(exc_info.value)
    assert message == "NOAA_TOKEN is required for NOAA CDO validation"
    assert fake_secret not in message
