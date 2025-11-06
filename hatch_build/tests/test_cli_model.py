import sys
from pathlib import Path
from typing import Dict, List, Literal, Optional
from unittest.mock import patch

from pydantic import BaseModel

from hatch_build.cli import hatchling, parse_extra_args_model


class SubModel(BaseModel, validate_assignment=True):
    sub_arg: int = 42
    sub_arg_with_value: str = "sub_default"


class MyTopLevelModel(BaseModel, validate_assignment=True):
    extra_arg: bool = False
    extra_arg_with_value: str = "default"
    extra_arg_with_value_equals: Optional[str] = "default_equals"
    extra_arg_literal: Literal["a", "b", "c"] = "a"

    list_arg: List[int] = [1, 2, 3]
    dict_arg: Dict[str, str] = {"key": "value"}
    path_arg: Path = Path(".")

    submodel: SubModel
    submodel2: SubModel = SubModel()
    submodel3: Optional[SubModel] = None


class TestCLIMdel:
    def test_get_arg_from_model(self):
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
                "--extra-arg-literal",
                "b",
                "--list-arg",
                "1,2,3",
                "--dict-arg",
                "key1=value1,key2=value2",
                "--path-arg",
                "/some/path",
                "--submodel.sub-arg",
                "100",
                "--submodel.sub-arg-with-value",
                "sub_value",
                "--submodel2.sub-arg",
                "200",
                "--submodel2.sub-arg-with-value",
                "sub_value2",
                "--submodel3.sub-arg",
                "300",
            ],
        ):
            assert hatchling() == 0
            model, extras = parse_extra_args_model(MyTopLevelModel(submodel=SubModel()))

        assert model.extra_arg is True
        assert model.extra_arg_with_value == "value"
        assert model.extra_arg_with_value_equals == "value2"
        assert model.extra_arg_literal == "b"
        assert model.list_arg == [1, 2, 3]
        assert model.dict_arg == {"key1": "value1", "key2": "value2"}
        assert model.path_arg == Path("/some/path")
        assert model.submodel.sub_arg == 100
        assert model.submodel.sub_arg_with_value == "sub_value"
        assert model.submodel2.sub_arg == 200
        assert model.submodel2.sub_arg_with_value == "sub_value2"
        assert model.submodel3.sub_arg == 300

        assert "--extra-arg-not-in-parser" in extras
