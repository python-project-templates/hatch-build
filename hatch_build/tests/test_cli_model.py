import sys
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union
from unittest.mock import patch

from p2a.model import _initlog
from pydantic import BaseModel

from hatch_build import __version__
from hatch_build.cli import hatchling, parse_extra_args_model


class MyEnum(Enum):
    OPTION_A = "option_a"
    OPTION_B = "option_b"
    OPTION_C = "option_c"


class SubModel(BaseModel, validate_assignment=True):
    sub_arg: int = 42
    sub_arg_with_value: str = "sub_default"
    sub_arg_enum: MyEnum = MyEnum.OPTION_A
    sub_arg_literal: Literal["x", "y", "z"] = "x"


class MyTopLevelModel(BaseModel, validate_assignment=True):
    extra_arg: bool = False
    extra_arg_with_value: str = "default"
    extra_arg_with_value_equals: Optional[str] = "default_equals"
    extra_arg_literal: Literal["a", "b", "c"] = "a"

    enum_arg: MyEnum = MyEnum.OPTION_A
    list_arg: List[int] = [1, 2, 3]
    dict_arg: Dict[str, str] = {}
    dict_arg_default_values: Dict[str, str] = {"existing-key": "existing-value"}
    path_arg: Path = Path(".")

    list_literal: List[Literal["a", "b", "c"]] = ["a"]
    dict_literal_key: Dict[Literal["a", "b", "c"], str] = {"a": "first"}
    dict_literal_value: Dict[str, Literal["a", "b", "c"]] = {"first": "a"}

    list_enum: List[MyEnum] = [MyEnum.OPTION_A]
    dict_enum: Dict[str, MyEnum] = {"first": MyEnum.OPTION_A}
    dict_enum_key: Dict[MyEnum, str] = {MyEnum.OPTION_A: "first"}
    dict_enum_key_model_value: Dict[MyEnum, SubModel] = {MyEnum.OPTION_A: SubModel()}

    submodel: SubModel
    submodel2: SubModel = SubModel(sub_args=84, sub_arg_with_value="predefined", sub_arg_enum=MyEnum.OPTION_B, sub_arg_literal="z")
    submodel3: Optional[SubModel] = None

    submodel_list_instanced: List[SubModel] = [SubModel()]
    submodel_dict_instanced: Dict[str, SubModel] = {"a": SubModel()}

    unsupported_literal: Literal[b"test"] = b"test"
    unsupported_dict: Dict[SubModel, str] = {}
    unsupported_dict_mixed_types: Dict[str, Union[str, SubModel]] = {}
    unsupported_random_type: Optional[set] = None

    unsupported_submodel_list: List[SubModel] = []
    unsupported_submodel_dict: Dict[str, SubModel] = {}


class TestCLIMdel:
    def test_get_arg_from_model(self):
        with (
            patch.object(
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
                    "--extra-arg-literal",
                    "b",
                    "--enum-arg",
                    "option_b",
                    "--list-arg",
                    "1,2,3",
                    "--dict-arg",
                    "key1=value1,key2=value2",
                    "--dict-arg-default-values.existing-key",
                    "new-value",
                    "--path-arg",
                    "/some/path",
                    "--list-literal",
                    "a,b",
                    "--dict-literal-key.a",
                    "first",
                    "--dict-literal-value.first",
                    "a",
                    "--list-enum",
                    "option_a,option_b",
                    "--dict-enum.first",
                    "option_b",
                    "--dict-enum-key.option_b",
                    "second",
                    "--dict-enum-key.OPTION_C",
                    "third",
                    "--dict-enum-key-model-value.option-a.sub-arg",
                    "600",
                    "--submodel.sub-arg",
                    "100",
                    "--submodel.sub-arg-with-value",
                    "sub_value",
                    "--submodel.sub-arg-enum",
                    "option_a",
                    "--submodel.sub-arg-literal",
                    "y",
                    "--submodel2.sub-arg",
                    "200",
                    "--submodel2.sub-arg-with-value",
                    "sub_value2",
                    "--submodel3.sub-arg",
                    "300",
                    "--submodel-list-instanced.0.sub-arg",
                    "400",
                    "--submodel-list-instanced.0.sub-arg-with-value",
                    "list_value",
                    "--submodel-list-instanced.0.sub-arg-enum",
                    "option_b",
                    "--submodel-list-instanced.0.sub-arg-literal",
                    "z",
                    "--submodel-dict-instanced.a.sub-arg",
                    "500",
                ],
            ),
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            _initlog("DEBUG")
            assert hatchling() == 0
            model, extras = parse_extra_args_model(MyTopLevelModel(submodel=SubModel()))

        assert len(extras) == 1
        assert "--extra-arg-not-in-parser" in extras

        assert model.extra_arg is True
        assert model.extra_arg_with_value == "value"
        assert model.extra_arg_with_value_equals == "value2"
        assert model.extra_arg_literal == "b"

        assert model.enum_arg == MyEnum.OPTION_B
        assert model.list_arg == [1, 2, 3]
        assert model.dict_arg == {"key1": "value1", "key2": "value2"}
        assert model.dict_arg_default_values == {"existing-key": "new-value"}
        assert model.path_arg == Path("/some/path")

        assert model.list_literal == ["a", "b"]
        assert model.dict_literal_key == {"a": "first"}
        assert model.dict_literal_value == {"first": "a"}

        assert model.list_enum == [MyEnum.OPTION_A, MyEnum.OPTION_B]
        assert model.dict_enum == {"first": MyEnum.OPTION_B}
        assert model.dict_enum_key == {MyEnum.OPTION_A: "first", MyEnum.OPTION_B: "second", MyEnum.OPTION_C: "third"}
        assert model.dict_enum_key_model_value[MyEnum.OPTION_A].sub_arg == 600

        assert model.submodel.sub_arg == 100
        assert model.submodel.sub_arg_with_value == "sub_value"
        assert model.submodel.sub_arg_enum == MyEnum.OPTION_A
        assert model.submodel.sub_arg_literal == "y"
        assert model.submodel2.sub_arg == 200
        assert model.submodel2.sub_arg_with_value == "sub_value2"
        assert model.submodel2.sub_arg_enum == MyEnum.OPTION_B
        assert model.submodel2.sub_arg_literal == "z"

        assert model.submodel3.sub_arg == 300
        assert model.submodel_list_instanced[0].sub_arg == 400
        assert model.submodel_list_instanced[0].sub_arg_with_value == "list_value"
        assert model.submodel_list_instanced[0].sub_arg_enum == MyEnum.OPTION_B
        assert model.submodel_list_instanced[0].sub_arg_literal == "z"
        assert model.submodel_dict_instanced["a"].sub_arg == 500

        stderr = mock_stderr.getvalue()
        for text in (
            f"[sdist]\ndist/hatch_build-{__version__}.tar.gz",
            f"[wheel]\ndist/hatch_build-{__version__}-py3-none-any.whl",
            "[p2a][WARNING]: Only lists of str, int, float, or bool are supported - field `unsupported_submodel_list` got <class 'test_cli_model.SubModel'>",
            "[p2a][WARNING]: Only dicts with str, int, float, bool, or enum values are supported - field `unsupported_submodel_dict` got value type <class 'test_cli_model.SubModel'>",
            "[p2a][WARNING]: Only Literal types of str, int, float, or bool are supported - field `unsupported_literal` got (b'test',)",
            "[p2a][WARNING]: Only dicts with str, int, float, bool, or enum keys are supported - field `unsupported_dict` got key type <class 'test_cli_model.SubModel'>",
            "[p2a][WARNING]: Only dicts with str, int, float, bool, or enum values are supported - field `unsupported_dict_mixed_types` got value type typing.Union[str, test_cli_model.SubModel]",
            "[p2a][WARNING]: Unsupported field type for argument 'unsupported_random_type': <class 'set'>",
        ):
            assert text in stderr
            stderr = stderr.replace(text, "")
        if "[p2a][WARNING]" in stderr.strip():
            for line in stderr.strip().splitlines():
                if "[p2a][WARNING]" in line:
                    print("UNEXPECTED WARNING:", line)
            assert False
