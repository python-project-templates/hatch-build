from argparse import ArgumentParser
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from hatchling.cli.build import build_command
from p2a import parse_extra_args_model as base_parse_extra_args_model

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = (
    "hatchling",
    "parse_extra_args",
    "parse_extra_args_model",
)
_extras = None


def parse_extra_args(subparser: Optional[ArgumentParser] = None) -> List[str]:
    if subparser is None:
        subparser = ArgumentParser(prog="hatch-build-extras", allow_abbrev=False)
    kwargs, extras = subparser.parse_known_args(_extras or [])
    return vars(kwargs), extras


def parse_extra_args_model(model: "BaseModel"):
    return base_parse_extra_args_model(model, _extras)


def _hatchling_internal() -> Tuple[Optional[Callable], Optional[dict], List[str]]:
    parser = ArgumentParser(prog="hatch-build", allow_abbrev=False)
    subparsers = parser.add_subparsers()

    defaults = {"metavar": ""}
    build_command(subparsers, defaults)

    # Replace parser with just the build one
    parser = subparsers.choices["build"]
    parser.prog = "hatch-build"

    # Parse known arguments
    kwargs, extras = parser.parse_known_args()

    # Extras can exist to be detected in custom hooks and plugins,
    # but they must be after a '--' separator
    if extras and extras[0] != "--":
        parser.print_help()
        return None, None, None

    # Wrap the parsed arguments in a dictionary
    kwargs = vars(kwargs)

    try:
        command = kwargs.pop("func")
    except KeyError:
        parser.print_help()
        return None, None, None
    return command, kwargs, extras[1:]  # Remove the '--' separator


def hatchling() -> int:
    global _extras

    command, kwargs, extras = _hatchling_internal()
    if command is None:
        return 1

    # Set so plugins can reference
    _extras = extras

    command(**kwargs)
    return 0
