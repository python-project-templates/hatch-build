from argparse import ArgumentParser
from logging import Formatter, StreamHandler, getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Literal, Optional, Tuple, Type, Union, get_args, get_origin

from hatchling.cli.build import build_command

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = (
    "hatchling",
    "parse_extra_args",
    "parse_extra_args_model",
)
_extras = None

_log = getLogger(__name__)
_handler = StreamHandler()
_formatter = Formatter("[%(asctime)s][%(name)s][%(levelname)s]: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z")
_handler.setFormatter(_formatter)
_log.addHandler(_handler)


def parse_extra_args(subparser: Optional[ArgumentParser] = None) -> List[str]:
    if subparser is None:
        subparser = ArgumentParser(prog="hatch-build-extras", allow_abbrev=False)
    kwargs, extras = subparser.parse_known_args(_extras or [])
    return vars(kwargs), extras


def _recurse_add_fields(parser: ArgumentParser, model: Union["BaseModel", Type["BaseModel"]], prefix: str = ""):
    from pydantic import BaseModel
    from pydantic_core import PydanticUndefined

    # Model is required
    if model is None:
        raise ValueError("Model instance cannot be None")

    # Extract the fields from a model instance or class
    if isinstance(model, type):
        model_fields = model.model_fields
    else:
        model_fields = model.__class__.model_fields

    # For each available field, add an argument to the parser
    for field_name, field in model_fields.items():
        # Grab the annotation to map to type
        field_type = field.annotation
        # Build the argument name converting underscores to dashes
        arg_name = f"--{prefix.replace('_', '-')}{field_name.replace('_', '-')}"

        # If theres an instance, use that so we have concrete values
        model_instance = model if not isinstance(model, type) else None

        # If we have an instance, grab the field value
        field_instance = getattr(model_instance, field_name, None) if model_instance else None

        # MARK: Wrappers:
        #  - Optional[T]
        #  - Union[T, None]
        if get_origin(field_type) is Optional:
            field_type = get_args(field_type)[0]
        elif get_origin(field_type) is Union:
            non_none_types = [t for t in get_args(field_type) if t is not type(None)]
            if len(non_none_types) == 1:
                field_type = non_none_types[0]
            else:
                _log.warning(f"Unsupported Union type for argument '{field_name}': {field_type}")
                continue

        # Default value, promote PydanticUndefined to None
        if field.default is PydanticUndefined:
            default_value = None
        else:
            default_value = field.default

        # Handled types
        # - bool, str, int, float
        # - Path
        # - Nested BaseModel
        # - Literal
        # - List[T]
        #    - where T is bool, str, int, float
        #    - List[BaseModel] where we have an instance to recurse into
        # - Dict[str, T]
        #   - where T is bool, str, int, float
        #   - Dict[str, BaseModel] where we have an instance to recurse into
        if field_type is bool:
            #############
            # MARK: bool
            parser.add_argument(arg_name, action="store_true", default=default_value)
        elif field_type in (str, int, float):
            ########################
            # MARK: str, int, float
            try:
                parser.add_argument(arg_name, type=field_type, default=default_value)
            except TypeError:
                # TODO: handle more complex types if needed
                parser.add_argument(arg_name, type=str, default=default_value)
        elif isinstance(field_type, type) and issubclass(field_type, Path):
            #############
            # MARK: Path
            # Promote to/from string
            parser.add_argument(arg_name, type=str, default=str(default_value) if isinstance(default_value, Path) else None)
        elif isinstance(field_instance, BaseModel):
            ############################
            # MARK: instance(BaseModel)
            # Nested model, add its fields with a prefix
            _recurse_add_fields(parser, field_instance, prefix=f"{field_name}.")
        elif isinstance(field_type, Type) and issubclass(field_type, BaseModel):
            ########################
            # MARK: type(BaseModel)
            # Nested model class, add its fields with a prefix
            _recurse_add_fields(parser, field_type, prefix=f"{field_name}.")
        elif get_origin(field_type) is Literal:
            ################
            # MARK: Literal
            literal_args = get_args(field_type)
            if not all(isinstance(arg, (str, int, float, bool)) for arg in literal_args):
                # Only support simple literal types for now
                _log.warning(f"Only Literal types of str, int, float, or bool are supported - field `{field_name}` got {literal_args}")
                continue
            ####################################
            # MARK: Literal[str|int|float|bool]
            parser.add_argument(arg_name, type=type(literal_args[0]), choices=literal_args, default=default_value)
        elif get_origin(field_type) in (list, List):
            ################
            # MARK: List[T]
            if get_args(field_type) and get_args(field_type)[0] not in (str, int, float, bool):
                # If theres already something here, we can procede by adding the command with a positional indicator
                if field_instance:
                    ########################
                    # MARK: List[BaseModel]
                    for i, value in enumerate(field_instance):
                        _recurse_add_fields(parser, value, prefix=f"{field_name}.{i}.")
                    continue
                # If there's nothing here, we don't know how to address them
                # TODO: we could just prefill e.g. --field.0, --field.1 up to some limit
                _log.warning(f"Only lists of str, int, float, or bool are supported - field `{field_name}` got {get_args(field_type)[0]}")
                continue
            #################################
            # MARK: List[str|int|float|bool]
            parser.add_argument(arg_name, type=str, default=",".join(map(str, default_value)) if isinstance(field, str) else None)
        elif get_origin(field_type) in (dict, Dict):
            ######################
            # MARK: Dict[str, T]
            key_type, value_type = get_args(field_type)

            if key_type not in (str, int, float, bool) and not (
                get_origin(key_type) is Literal and all(isinstance(arg, (str, int, float, bool)) for arg in get_args(key_type))
            ):
                # Check Key type, must be str, int, float, bool
                _log.warning(f"Only dicts with str keys are supported - field `{field_name}` got key type {key_type}")
                continue

            if value_type not in (str, int, float, bool) and not field_instance:
                # Check Value type, must be str, int, float, bool if an instance isnt provided
                _log.warning(f"Only dicts with str values are supported - field `{field_name}` got value type {value_type}")
                continue

            # If theres already something here, we can procede by adding the command by keyword
            if field_instance:
                if all(isinstance(v, BaseModel) for v in field_instance.values()):
                    #############################
                    # MARK: Dict[str, BaseModel]
                    for key, value in field_instance.items():
                        _recurse_add_fields(parser, value, prefix=f"{field_name}.{key}.")
                    continue
                # If we have mixed, we don't support
                elif any(isinstance(v, BaseModel) for v in field_instance.values()):
                    _log.warning(f"Mixed dict value types are not supported - field `{field_name}` has mixed BaseModel and non-BaseModel values")
                    continue
                # If we have non BaseModel values, we can still add a parser by route
                if all(isinstance(v, (str, int, float, bool)) for v in field_instance.values()):
                    # We can set "known" values here
                    for key, value in field_instance.items():
                        ##########################################
                        # MARK: Dict[str, str|int|float|bool]
                        parser.add_argument(
                            f"{arg_name}.{key}",
                            type=type(value),
                            default=value,
                        )
                        # NOTE: don't continue to allow adding the full setter below
            # Finally add the full setter for unknown values
            ##########################################
            # MARK: Dict[str, str|int|float|bool|str]
            parser.add_argument(
                arg_name, type=str, default=",".join(f"{k}={v}" for k, v in default_value.items()) if isinstance(default_value, dict) else None
            )
        else:
            _log.warning(f"Unsupported field type for argument '{field_name}': {field_type}")
    return parser


def parse_extra_args_model(model: "BaseModel"):
    try:
        from pydantic import BaseModel, TypeAdapter, ValidationError
    except ImportError:
        raise ImportError("pydantic is required to use parse_extra_args_model")
    # Recursively parse fields from a pydantic model and its sub-models
    # and create an argument parser to parse extra args
    parser = ArgumentParser(prog="hatch-build-extras-model", allow_abbrev=False)
    parser = _recurse_add_fields(parser, model)

    # Parse the extra args and update the model
    args, kwargs = parse_extra_args(parser)
    for key, value in args.items():
        # Handle nested fields
        if "." in key:
            # We're going to walk down the model tree to get to the right sub-model
            parts = key.split(".")

            # Accounting
            sub_model = model
            parent_model = None

            for i, part in enumerate(parts[:-1]):
                if part.isdigit() and isinstance(sub_model, list):
                    # List index
                    index = int(part)

                    # Should never be out of bounds, but check to be sure
                    if index >= len(sub_model):
                        raise IndexError(f"Index {index} out of range for field '{parts[i - 1]}' on model '{parent_model.__class__.__name__}'")

                    # Grab the model instance from the list
                    model_to_set = sub_model[index]
                elif isinstance(sub_model, dict):
                    # Dict key
                    if part not in sub_model:
                        raise KeyError(f"Key '{part}' not found for field '{parts[i - 1]}' on model '{parent_model.__class__.__name__}'")

                    # Grab the model instance from the dict
                    model_to_set = sub_model[part]
                else:
                    model_to_set = getattr(sub_model, part)

                if model_to_set is None:
                    # Create a new instance of model
                    field = sub_model.__class__.model_fields[part]

                    # if field annotation is an optional or union with none, extract type
                    if get_origin(field.annotation) is Optional:
                        model_to_instance = get_args(field.annotation)[0]
                    elif get_origin(field.annotation) is Union:
                        non_none_types = [t for t in get_args(field.annotation) if t is not type(None)]
                        if len(non_none_types) == 1:
                            model_to_instance = non_none_types[0]

                    else:
                        model_to_instance = field.annotation
                    if not isinstance(model_to_instance, type) or not issubclass(model_to_instance, BaseModel):
                        raise ValueError(
                            f"Cannot create sub-model for field '{part}' on model '{sub_model.__class__.__name__}': - type is {model_to_instance}"
                        )
                    model_to_set = model_to_instance()
                    setattr(sub_model, part, model_to_set)

                parent_model = sub_model
                sub_model = model_to_set

            key = parts[-1]
        else:
            # Accounting
            sub_model = model
            parent_model = model
            model_to_set = model

        if not isinstance(model_to_set, BaseModel):
            if isinstance(model_to_set, dict):
                # We allow setting dict values directly
                # Grab the dict from the parent model, set the value, and continue
                if key in model_to_set:
                    model_to_set[key] = value
                elif key.replace("_", "-") in model_to_set:
                    # Argparse converts dashes back to underscores, so undo
                    model_to_set[key.replace("_", "-")] = value
                else:
                    # Raise
                    raise KeyError(f"Key '{key}' not found in dict field on model '{parent_model.__class__.__name__}'")

                # Now adjust our variable accounting to set the whole dict back on the parent model,
                # allowing us to trigger any validation
                key = part
                value = model_to_set
                model_to_set = parent_model
            else:
                _log.warning(f"Cannot set field '{key}' on non-BaseModel instance of type '{type(model_to_set).__name__}'")
                continue

        # Grab the field from the model class and make a type adapter
        field = model_to_set.__class__.model_fields[key]
        adapter = TypeAdapter(field.annotation)

        # Convert the value using the type adapter
        if get_origin(field.annotation) in (list, List):
            value = value or ""
            if isinstance(value, list):
                # Already a list, use as is
                pass
            elif isinstance(value, str):
                # Convert from comma-separated values
                value = value.split(",")
            else:
                # Unknown, raise
                raise ValueError(f"Cannot convert value '{value}' to list for field '{key}'")
        elif get_origin(field.annotation) in (dict, Dict):
            value = value or ""
            if isinstance(value, dict):
                # Already a dict, use as is
                pass
            elif isinstance(value, str):
                # Convert from comma-separated key=value pairs
                dict_items = value.split(",")
                dict_value = {}
                for item in dict_items:
                    if item:
                        k, v = item.split("=", 1)
                        dict_value[k] = v
                # Grab any previously existing dict to preserve other keys
                existing_dict = getattr(model_to_set, key, {}) or {}
                dict_value.update(existing_dict)
                value = dict_value
            else:
                # Unknown, raise
                raise ValueError(f"Cannot convert value '{value}' to dict for field '{key}'")
        try:
            if value is not None:
                value = adapter.validate_python(value)

                # Set the value on the model
                setattr(model_to_set, key, value)
        except ValidationError:
            _log.warning(f"Failed to validate field '{key}' with value '{value}' for model '{model_to_set.__class__.__name__}'")
            continue

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
