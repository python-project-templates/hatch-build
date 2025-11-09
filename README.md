# hatch build

A minimal CLI wrapper around hatchling build

[![Build Status](https://github.com/python-project-templates/hatch-build/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/python-project-templates/hatch-build/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/python-project-templates/hatch-build/branch/main/graph/badge.svg)](https://codecov.io/gh/python-project-templates/hatch-build)
[![License](https://img.shields.io/github/license/python-project-templates/hatch-build)](https://github.com/python-project-templates/hatch-build)
[![PyPI](https://img.shields.io/pypi/v/hatch-build.svg)](https://pypi.python.org/pypi/hatch-build)

## Overview

This library provides a minimal CLI `hatch-build`, equivalent to [`hatchling build`](https://hatch.pypa.io/latest/) except for [the enablement of passthrough arguments](https://github.com/pypa/hatch/pull/1743).

```bash
hatch-build -- --my-custom-plugin-arg
```

As a convenience, we provide an `argparse` wrapper to extract the extra args:

```python
from hatch_build import parse_extra_args

args, extras = parse_extra_args(my_argparse_parser)
```

### Configuration

If you manage your hatch plugin config as a pydantic model, a function is provided to automatically expose fields as command line arguments.

```python
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from pydantic import BaseModel


from hatch_build import parse_extra_args_model


class MyPluginConfig(BaseModel, validate_assignment=True):
    extra_arg: bool = False
    extra_arg_with_value: str = "default"
    extra_arg_literal: Literal["a", "b", "c"] = "a"

class MyHatchPlugin(BuildHookInterface[MyPluginConfig]):
    PLUGIN_NAME = "my-hatch-plugin"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        my_config_model = MyPluginConfig(**self.config)
        parse_extra_args_model(my_config_model)

        print(f"{my_config_model.extra_arg} {my_config_model.extra_arg_with_value} {my_config_model.extra_arg_literal}")

# > hatch-build -- --extra-arg --extra-arg-with-value "test" --extra-arg-literal b
# True test b
```

> [!NOTE]
> This library was generated using [copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template repository](https://github.com/python-project-templates/base).
