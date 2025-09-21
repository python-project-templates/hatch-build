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

    # parser = subparsers.add_parser('build')
    # parser.add_argument(
    #     '-d', '--directory', dest='directory', help='The directory in which to build artifacts', **defaults
    # )
    # parser.add_argument(
    #     '-t',
    #     '--target',
    #     dest='targets',
    #     action='append',
    #     help='Comma-separated list of targets to build, overriding project defaults',
    #     **defaults,
    # )
    # parser.add_argument('--hooks-only', dest='hooks_only', action='store_true', default=None)
    # parser.add_argument('--no-hooks', dest='no_hooks', action='store_true', default=None)
    # parser.add_argument('-c', '--clean', dest='clean', action='store_true', default=None)
    # parser.add_argument('--clean-hooks-after', dest='clean_hooks_after', action='store_true', default=None)
    # parser.add_argument('--clean-only', dest='clean_only', action='store_true')
    # parser.add_argument('--app', dest='called_by_app', action='store_true', help=argparse.SUPPRESS)
    # parser.set_defaults(func=build_impl)
