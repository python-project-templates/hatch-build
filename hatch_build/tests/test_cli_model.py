import sys
from typing import Dict, List
from unittest.mock import patch

from pydantic import BaseModel

from hatch_build.cli import hatchling, parse_extra_args_model


class SubModel(BaseModel, validate_assignment=True):
    sub_arg: int = 42
    sub_arg_with_value: str = "sub_default"


class MyTopLevelModel(BaseModel, validate_assignment=True):
    extra_arg: bool = False
    extra_arg_with_value: str = "default"
    extra_arg_with_value_equals: str = "default_equals"

    list_arg: List[int] = [1, 2, 3]
    dict_arg: Dict[str, str] = {"key": "value"}

    submodel: SubModel
    submodel2: SubModel = SubModel()


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
                "--list-arg",
                "1,2,3",
                "--dict-arg",
                "key1=value1,key2=value2",
                "--submodel.sub-arg",
                "100",
                "--submodel.sub-arg-with-value",
                "sub_value",
                "--submodel2.sub-arg",
                "200",
                "--submodel2.sub-arg-with-value",
                "sub_value2",
            ],
        ):
            assert hatchling() == 0
            model, extras = parse_extra_args_model(MyTopLevelModel(submodel=SubModel()))

        assert model.extra_arg is True
        assert model.extra_arg_with_value == "value"
        assert model.extra_arg_with_value_equals == "value2"
        assert model.list_arg == [1, 2, 3]
        assert model.dict_arg == {"key1": "value1", "key2": "value2"}
        assert model.submodel.sub_arg == 100
        assert model.submodel.sub_arg_with_value == "sub_value"
        assert model.submodel2.sub_arg == 200
        assert model.submodel2.sub_arg_with_value == "sub_value2"
