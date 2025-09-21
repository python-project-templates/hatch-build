import argparse

from hatchling.cli.build import build_command


def hatchling() -> int:
    parser = argparse.ArgumentParser(prog="hatch-build", allow_abbrev=False)
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
        return 1

    # Wrap the parsed arguments in a dictionary
    kwargs = vars(kwargs)

    try:
        command = kwargs.pop("func")
    except KeyError:
        parser.print_help()
    else:
        command(**kwargs)

    return 0
