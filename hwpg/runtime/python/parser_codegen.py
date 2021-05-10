from hwpg.config import Config
from typing import Optional

from hwpg.parsergen import (
    Jinja2ParserCodeGen,
    Jinja2ParserFuncCodeGen,
    ParserActions,
    TemplData,
)

_TEMPL_FOLDER = "templates/python"
_PARSER_TEMPL = "parser.py.j2"

_FUNC_START = '''    def {{ name }}(self) -> Optional[{{ ret_type }}]:
        """
        {{ comment }}
        """
        old_pos = self.pos


'''

_FUNC_END_EARLY_RET = """        self.pos = old_pos
        return None
"""

_MATCH_TOKEN = """        # {{ comment }}
        {{ var }} = self._match_token_or_rollback(TokenType.{{ name }}, old_pos)
{%- if early_ret %}
        return {{ var }} if {{ var }} else None
{% else %}
        if not {{ var }}:
            return None
{% endif %}

"""

_MATCH_TOKEN_ZERO_OR_ONE = """        # {{ comment }}
        {{ var }} = self._try_match_token(TokenType.{{ name }})
{%- if early_ret %}
        if {{ var }}:
            return {{ var }}
{% endif %}

"""

_MATCH_TOKEN_ZERO_OR_MORE = """        # {{ comment }}
        {{ var }} = self._try_match_tokens(TokenType.{{ name }})
{%- if early_ret %}
        if {{ var }}:
            return {{ var }}
{% endif %}

"""

_MATCH_TOKEN_ONE_OR_MORE = """        # {{ comment }}
        {{ var }} = self._match_tokens_or_rollback(TokenType.{{ name }}, old_pos)
{%- if early_ret %}
        return {{ var }} if {{ var }} else None
{% else %}
        if not {{ var }}:
            return None
{% endif %}

"""

_MATCH_RULE = """        # {{ comment }}
        {{ var }} = self.{{ func }}()
        if not {{ var }}:
            self.pos = old_pos
            return None
{% if early_ret %}
        return {{ var }}
{% endif %}

"""

_MATCH_RULE_ZERO_OR_ONE = """        # {{ comment }}
        {{ var }} = self.{{ func }}()
{%- if early_ret %}
        if {{ var }}:
            return {{ var }}
{% endif %}

"""

_MATCH_RULE_ZERO_OR_MORE = """        # {{ comment }}
        {{ var }}: List[{{ ret_type }}] = []
        while True:
            {{ temp_var }} = self.{{ func }}()
            if not {{ temp_var }}:
                break
            {{ var }}.append({{ temp_var }})
{% if early_ret %}
        if {{ var }}:
            return {{ var }}
{% endif %}

"""

_MATCH_RULE_ONE_OR_MORE = """        # {{ comment }}
        {{ var }}: List[{{ ret_type }}] = []
        while True:
            {{ temp_var }} = self.{{ func }}()
            if not {{ temp_var }}:
                break
            {{ var }}.append({{ temp_var }})

        if not {{ var }}:
            self.pos = old_pos
            return None
{% if early_ret %}
        return {{ var }}
{% endif %}

"""


def _strip_func_prefix(name: str) -> str:
    # Remove 'parse_' (6 chars) or '_parse_' prefix (7 chars)
    return name[6:] if name.startswith("parse_") else name[7:]


class PyParserFuncCodeGen(Jinja2ParserFuncCodeGen):
    _default_action = "        return ParserNode([{{ vars }}])", "TreeNode"
    _func_start_templ = _FUNC_START
    _early_ret_templ = _FUNC_END_EARLY_RET
    _match_token_templ = _MATCH_TOKEN
    _match_token_zero_or_one_templ = _MATCH_TOKEN_ZERO_OR_ONE
    _match_token_zero_or_more_templ = _MATCH_TOKEN_ZERO_OR_MORE
    _match_token_one_or_more_templ = _MATCH_TOKEN_ONE_OR_MORE
    _parse_rule_templ = _MATCH_RULE
    _parse_rule_zero_or_one_templ = _MATCH_RULE_ZERO_OR_ONE
    _parse_rule_zero_or_more_templ = _MATCH_RULE_ZERO_OR_MORE
    _parse_rule_one_or_more_templ = _MATCH_RULE_ONE_OR_MORE

    def __init__(
        self,
        name: str,
        early_ret: bool,
        make_parse_tree: bool,
        comment: str,
        actions: Optional[ParserActions],
    ):
        super().__init__(
            name, _strip_func_prefix(name), early_ret, make_parse_tree, comment, actions
        )

    def _start_func(self) -> TemplData:
        return dict(name=self.name, ret_type=self.ret_type, comment=self.comment)

    def _end_func(self) -> TemplData:
        return dict(vars=", ".join(self._vars))

    def _match_token(self, name: str, comment: str) -> TemplData:
        var = self._new_var(name.lower())
        return dict(name=name, var=var, early_ret=self.early_ret, comment=comment)

    def _match_token_zero_or_one(self, name: str, comment: str) -> TemplData:
        var = self._new_var(name.lower())
        return dict(name=name, var=var, early_ret=self.early_ret, comment=comment)

    def _match_token_zero_or_more(self, name: str, comment: str) -> TemplData:
        var = self._new_var(name.lower() + "_list")
        return dict(name=name, var=var, early_ret=self.early_ret, comment=comment)

    def _match_token_one_or_more(self, name: str, comment: str) -> TemplData:
        var = self._new_var(name.lower() + "_list")
        return dict(name=name, var=var, early_ret=self.early_ret, comment=comment)

    def _parse_rule(self, name: str, comment: str) -> TemplData:
        var = self._new_var(_strip_func_prefix(name))
        return dict(var=var, func=name, early_ret=self.early_ret, comment=comment)

    def _parse_rule_zero_or_one(self, name: str, comment: str) -> TemplData:
        var = self._new_var(_strip_func_prefix(name))
        return dict(var=var, func=name, early_ret=self.early_ret, comment=comment)

    def _parse_rule_zero_or_more(self, name: str, comment: str) -> TemplData:
        temp_var = _strip_func_prefix(name)
        var = self._new_var(temp_var + "_list")

        return dict(
            temp_var=temp_var,
            var=var,
            func=name,
            early_ret=self.early_ret,
            ret_type=self.ret_type,
            comment=comment,
        )

    def _parse_rule_one_or_more(self, name: str, comment: str) -> TemplData:
        temp_var = _strip_func_prefix(name)
        var = self._new_var(temp_var + "_list")

        return dict(
            temp_var=temp_var,
            var=var,
            func=name,
            early_ret=self.early_ret,
            ret_type=self.ret_type,
            comment=comment,
        )


class PyParserCodeGen(Jinja2ParserCodeGen):
    _parser_func_codegen = PyParserFuncCodeGen
    _templ_dir = _TEMPL_FOLDER
    _parser_templ = _PARSER_TEMPL

    def __init__(self, name: str, cfg: Config):
        super().__init__(name, cfg)

    @property
    def _name(self):
        return self.name.title()  # TODO: Make camel case

    @staticmethod
    def make_func_name(name: str, binding: str = "", sub: int = 0) -> str:
        prefix = "_parse_" if sub > 0 else "parse_"
        if binding:
            return f"{prefix}{name}_{binding}"

        return f"{prefix}{name}_inner{sub}" if sub > 0 else f"{prefix}{name}"
