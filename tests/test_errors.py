"""Exit-code constants + GhafiError shape."""

from __future__ import annotations

from ghafi.cli._errors import (
    EXIT_API_ERROR,
    EXIT_AUTH_ERROR,
    EXIT_ENV_ERROR,
    EXIT_SUCCESS,
    EXIT_USER_ERROR,
    GhafiError,
)


def test_exit_codes_are_distinct_small_ints():
    codes = {EXIT_SUCCESS, EXIT_USER_ERROR, EXIT_ENV_ERROR, EXIT_AUTH_ERROR, EXIT_API_ERROR}
    assert codes == {0, 1, 2, 3, 4}


def test_ghafi_error_carries_message_and_remediation():
    err = GhafiError(code=EXIT_USER_ERROR, message="bad flag", remediation="use --help")
    assert err.code == 1
    assert err.message == "bad flag"
    assert err.remediation == "use --help"
    assert str(err) == "bad flag"


def test_ghafi_error_to_dict_shape():
    err = GhafiError(code=EXIT_AUTH_ERROR, message="401", remediation="check token")
    assert err.to_dict() == {"code": 3, "message": "401", "remediation": "check token"}


def test_ghafi_error_default_remediation_is_empty_string():
    err = GhafiError(code=EXIT_API_ERROR, message="500")
    assert err.remediation == ""
    assert err.to_dict()["remediation"] == ""
