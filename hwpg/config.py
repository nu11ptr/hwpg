from dataclasses import dataclass
from enum import Enum
from importlib.util import module_from_spec, spec_from_file_location
from typing import Any, Optional

from hwpg.lexergen import LexerActions
from hwpg.parsergen import ParserActions


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

    # Parser options
    make_parse_tree: bool = True
    memoize: bool = True
    left_recursion: bool = True

    lexer_actions: Optional[LexerActions] = None
    parser_actions: Optional[ParserActions] = None


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
