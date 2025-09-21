import sys
from unittest.mock import patch

import pytest

from hatch_build.cli import hatchling


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
