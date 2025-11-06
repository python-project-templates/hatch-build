from argparse import ArgumentParser
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple, Type, get_args, get_origin

from hatchling.cli.build import build_command

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = (
    "hatchling",
    "parse_extra_args",
)
_extras = None


def parse_extra_args(subparser: Optional[ArgumentParser] = None) -> List[str]:
    if subparser is None:
        subparser = ArgumentParser(prog="hatch-build-extras", allow_abbrev=False)
    kwargs, extras = subparser.parse_known_args(_extras or [])
    return vars(kwargs), extras


def recurse_add_fields(parser: ArgumentParser, model: "BaseModel", prefix: str = ""):
    from pydantic import BaseModel

    for field_name, field in model.__class__.model_fields.items():
        field_type = field.annotation
        arg_name = f"--{prefix}{field_name.replace('_', '-')}"
        if field_type is bool:
            parser.add_argument(arg_name, action="store_true", default=field.default)
        elif isinstance(field_type, Type) and issubclass(field_type, BaseModel):
            # Nested model, add its fields with a prefix
            recurse_add_fields(parser, getattr(model, field_name), prefix=f"{field_name}.")
        elif get_origin(field_type) in (list, List):
            # TODO: if list arg is complex type, raise as not implemented for now
            if get_args(field_type) and get_args(field_type)[0] not in (str, int, float, bool):
                raise NotImplementedError("Only lists of str, int, float, or bool are supported")
            parser.add_argument(arg_name, type=str, default=",".join(map(str, field.default)))
        elif get_origin(field_type) in (dict, Dict):
            # TODO: if key args are complex type, raise as not implemented for now
            key_type, value_type = get_args(field_type)
            if key_type not in (str, int, float, bool):
                raise NotImplementedError("Only dicts with str keys are supported")
            if value_type not in (str, int, float, bool):
                raise NotImplementedError("Only dicts with str values are supported")
            parser.add_argument(arg_name, type=str, default=",".join(f"{k}={v}" for k, v in field.default.items()))
        else:
            try:
                parser.add_argument(arg_name, type=field_type, default=field.default)
            except TypeError:
                # TODO: handle more complex types if needed
                parser.add_argument(arg_name, type=str, default=field.default)
    return parser


def parse_extra_args_model(model: "BaseModel"):
    try:
        from pydantic import TypeAdapter
    except ImportError:
        raise ImportError("pydantic is required to use parse_extra_args_model")
    # Recursively parse fields from a pydantic model and its sub-models
    # and create an argument parser to parse extra args
    parser = ArgumentParser(prog="hatch-build-extras-model", allow_abbrev=False)
    parser = recurse_add_fields(parser, model)

    # Parse the extra args and update the model
    args, kwargs = parse_extra_args(parser)
    for key, value in args.items():
        # Handle nested fields
        if "." in key:
            parts = key.split(".")
            sub_model = model
            for part in parts[:-1]:
                model_to_set = getattr(sub_model, part)
            key = parts[-1]
        else:
            model_to_set = model

        # Grab the field from the model class and make a type adapter
        field = model_to_set.__class__.model_fields[key]
        adapter = TypeAdapter(field.annotation)

        # Convert the value using the type adapter
        if get_origin(field.annotation) in (list, List):
            value = adapter.validate_python(value.split(","))
        elif get_origin(field.annotation) in (dict, Dict):
            dict_items = value.split(",")
            dict_value = {}
            for item in dict_items:
                k, v = item.split("=", 1)
                dict_value[k] = v
            value = adapter.validate_python(dict_value)
        else:
            value = adapter.validate_python(value)

        # Set the value on the model
        setattr(model_to_set, key, value)
    return model, kwargs


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
