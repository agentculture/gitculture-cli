"""stdout/stderr split + JSON envelope shape."""

from __future__ import annotations

import io
import json

from ghafi.cli._errors import EXIT_USER_ERROR, GhafiError
from ghafi.cli._output import emit_diagnostic, emit_error, emit_kv, emit_result, emit_table


def test_emit_result_text_appends_newline():
    out = io.StringIO()
    emit_result("hello", json_mode=False, stream=out)
    assert out.getvalue() == "hello\n"


def test_emit_result_text_preserves_trailing_newline():
    out = io.StringIO()
    emit_result("hello\n", json_mode=False, stream=out)
    assert out.getvalue() == "hello\n"


def test_emit_result_json_writes_dict():
    out = io.StringIO()
    emit_result({"a": 1}, json_mode=True, stream=out)
    assert json.loads(out.getvalue()) == {"a": 1}


def test_emit_error_text_shape():
    err = GhafiError(code=EXIT_USER_ERROR, message="msg", remediation="hint")
    stream = io.StringIO()
    emit_error(err, json_mode=False, stream=stream)
    assert stream.getvalue() == "error: msg\nhint: hint\n"


def test_emit_error_json_shape():
    err = GhafiError(code=EXIT_USER_ERROR, message="msg", remediation="hint")
    stream = io.StringIO()
    emit_error(err, json_mode=True, stream=stream)
    assert json.loads(stream.getvalue()) == {
        "code": 1,
        "message": "msg",
        "remediation": "hint",
    }


def test_emit_diagnostic_appends_newline():
    stream = io.StringIO()
    emit_diagnostic("progress", stream=stream)
    assert stream.getvalue() == "progress\n"


def test_emit_kv_renders_bullets():
    stream = io.StringIO()
    emit_kv([("a", 1), ("b", "two")], stream=stream)
    assert stream.getvalue() == "- **a:** 1\n- **b:** two\n"


def test_emit_table_renders_pipes():
    stream = io.StringIO()
    emit_table(headers=["x", "y"], rows=[(1, 2), (3, 4)], stream=stream)
    lines = stream.getvalue().splitlines()
    assert lines[0] == "| x | y |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 2 |"
    assert lines[3] == "| 3 | 4 |"
