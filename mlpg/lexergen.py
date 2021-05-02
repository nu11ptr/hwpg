from typing import Any, Dict, List, Protocol, Tuple

from jinja2 import Environment, FileSystemLoader


class TokensCodeGen(Protocol):
    def generate(self, token_names: List[str]) -> str:
        ...

    @property
    def tokens_filename(self) -> str:
        ...


class Jinja2TokensCodeGen:
    def __init__(self, templates: str, filename: str):
        loader = FileSystemLoader(templates)
        self._env = Environment(loader=loader)
        self._main_templ = self._env.get_template(filename)
        self._vars: Dict[str, Any] = {}

    def generate(self, token_names: List[str]) -> str:
        self._vars["token_types"] = token_names
        return self._main_templ.render(**self._vars)


class TokensGen:
    def __init__(self, codegen: TokensCodeGen):
        self._codegen = codegen

    def generate(self, token_names: List[str]) -> Tuple[str, str]:
        """
        Generates a tokens file and basic interfaces. It
        returns the tokens code and filename
        """
        return self._codegen.generate(token_names), self._codegen.tokens_filename
