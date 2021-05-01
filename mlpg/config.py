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

    # If blank, these names are chosen by language specific codegen
    parser_name: str = ""
    lexer_name: str = ""
    # 'token_name' only applies if 'output_type' is 'parser'. Otherwise, tokens
    # and lexer are combined in one file ('lexer_name' would thus apply)
    token_name: str = ""
    stubs_name: str = ""  # Only used if 'MAKE_STUBS' is True

    parser_pkg: str = "."
    lexer_pkg: str = "."
    # TOKEN_BASE_NAME only applies if 'OUTPUT_TYPE' is 'parser'. Otherwise, tokens
    # and lexer are combined in one file (LEXER_PKG would thus apply)
    token_pkg: str = "token"
    stubs_pkg: str = "lexer"

    memoize: bool = True
    left_recursion: bool = True
    make_stubs: bool = False

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
