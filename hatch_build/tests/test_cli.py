import sys
from argparse import ArgumentParser
from unittest.mock import patch

import pytest

from hatch_build.cli import hatchling, parse_extra_args


@pytest.fixture
def ok_argv():
    tmp_argv = sys.argv
    sys.argv = ["hatch-build"]
    yield
    sys.argv = tmp_argv


@pytest.fixture
def help_argv():
    tmp_argv = sys.argv
    sys.argv = ["hatch-build", "--help"]
    yield
    sys.argv = tmp_argv


@pytest.fixture
def bad_argv():
    tmp_argv = sys.argv
    sys.argv = ["hatch-build", "unexpected_arg"]
    yield
    sys.argv = tmp_argv


@pytest.fixture
def bad_extra_argv():
    tmp_argv = sys.argv
    sys.argv = ["hatch-build", "--unexpected_arg"]
    yield
    sys.argv = tmp_argv


@pytest.fixture
def ok_extra_argv():
    tmp_argv = sys.argv
    sys.argv = ["hatch-build", "--", "--extra-arg"]
    yield
    sys.argv = tmp_argv


@pytest.fixture
def get_arg():
    with patch.object(
        sys,
        "argv",
        [
            "hatch-build",
            "--",
            "--extra-arg",
            "--extra-arg-with-value",
            "value",
            "--extra-arg-with-value-equals=value2",
            "--extra-arg-not-in-parser",
        ],
    ):
        parser = ArgumentParser()
        parser.add_argument("--extra-arg", action="store_true")
        parser.add_argument("--extra-arg-with-value")
        parser.add_argument("--extra-arg-with-value-equals")
        yield parser


class TestHatchBuild:
    def test_hatchling(self, ok_argv):
        assert hatchling() == 0

    def test_help(self, help_argv):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        f = StringIO()
        with patch("sys.exit"):
            with redirect_stdout(f), redirect_stderr(f):
                result = hatchling()
        output = f.getvalue()
        assert result == 0
        assert "usage: hatch-build [-h] [-d] [-t] [--hooks-only]" in output

    def test_bad(self, bad_argv):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        f = StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            result = hatchling()
        output = f.getvalue()
        assert result == 1
        assert "usage: hatch-build [-h] [-d] [-t]" in output

    def test_bad_extras(self, bad_extra_argv):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        f = StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            result = hatchling()
        output = f.getvalue()
        assert result == 1
        assert "usage: hatch-build [-h] [-d] [-t]" in output

    def test_ok_extras(self, ok_extra_argv):
        assert hatchling() == 0

    def test_get_arg(self, get_arg):
        assert hatchling() == 0
        args, _ = parse_extra_args(get_arg)
        assert args["extra_arg"] is True
        assert args["extra_arg_with_value"] == "value"
        assert args["extra_arg_with_value_equals"] == "value2"

    def test_get_arg_no_passthrough(self, get_arg):
        assert hatchling() == 0
        _, kwargs = parse_extra_args()
        assert "--extra-arg" in kwargs
        assert "--extra-arg-with-value" in kwargs
        assert kwargs[kwargs.index("--extra-arg-with-value") + 1] == "value"
