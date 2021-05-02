from dataclasses import dataclass
from enum import Enum
from importlib.util import module_from_spec, spec_from_file_location
from typing import Any, Optional


class Lang(str, Enum):
    PYTHON = "python"
    GO = "go"


class OutputType(str, Enum):
    BOTH = "both"
    PARSER = "parser"
    LEXER = "lexer"


@dataclass
class Config:
    lang: Lang = Lang.PYTHON
    output_type: OutputType = OutputType.PARSER

    parser_pkg: str = "."
    lexer_pkg: str = "."

    memoize: bool = True
    left_recursion: bool = True

    lexer_transformer: Optional[Any] = None
    parser_transformer: Optional[Any] = None


def load(filename: Optional[str]) -> Config:
    cfg = Config()

    if filename:
        # Load module from the path given
        spec = spec_from_file_location("", filename)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore

        var = cfg.__dict__

        # For each top level attr in the module, overwite attr in config
        for k, v in mod.__dict__.items():
            if k.startswith("__") and k.endswith("__"):
                continue
            var[k] = v

    return cfg
