from hwpg.config import Config
from typing import Optional, Tuple

from jinja2 import Template

from hwpg.parsergen import (
    BaseParserFuncCodeGen,
    ParserFuncCodeGen,
    Jinja2ParserCodeGen,
    ParserActions,
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


class PyParserFuncCodeGen(BaseParserFuncCodeGen):
    def __init__(
        self,
        name: str,
        early_ret: bool,
        make_parse_tree: bool,
        comment: str,
        actions: Optional[ParserActions],
    ):
        super().__init__(name, early_ret, make_parse_tree, comment, actions)

        templ = Template(_FUNC_START)
        self._action, self.ret_type = self._func_actions()
        self._func_parts.append(
            templ.render(name=name, ret_type=self.ret_type, comment=self.comment)
        )

    # TODO: Move this into lang agnostic parsegen so it can be reused for all langs
    def _func_actions(self) -> Tuple[str, str]:
        default_tup = "        return ParserNode([{{ vars }}])", "TreeNode"
        if not self._actions:
            return default_tup

        attr_name = _strip_func_prefix(self.name)
        try:
            func = getattr(self._actions, attr_name)
        except AttributeError:
            if not self._make_parse_tree:
                raise RuntimeError(f"Parser actions missing function '{attr_name}'")

            return default_tup

        return func()

    def _end_func(self):
        if self.early_ret:
            self._func_parts.append(_FUNC_END_EARLY_RET)
        else:
            templ = Template(self._action)
            self._func_parts.append(templ.render(vars=", ".join(self._vars)))

    def match_token(self, name: str, comment: str):
        templ = Template(_MATCH_TOKEN)
        var = self._new_var(name.lower())
        self._func_parts.append(
            templ.render(name=name, var=var, early_ret=self.early_ret, comment=comment)
        )

    def match_token_zero_or_one(self, name: str, comment: str):
        templ = Template(_MATCH_TOKEN_ZERO_OR_ONE)
        var = self._new_var(name.lower())
        self._func_parts.append(
            templ.render(name=name, var=var, early_ret=self.early_ret, comment=comment)
        )

    def match_token_zero_or_more(self, name: str, comment: str):
        templ = Template(_MATCH_TOKEN_ZERO_OR_MORE)
        var = self._new_var(name.lower() + "_list")
        self._func_parts.append(
            templ.render(name=name, var=var, early_ret=self.early_ret, comment=comment)
        )

    def match_token_one_or_more(self, name: str, comment: str):
        templ = Template(_MATCH_TOKEN_ONE_OR_MORE)
        var = self._new_var(name.lower() + "_list")
        self._func_parts.append(
            templ.render(name=name, var=var, early_ret=self.early_ret, comment=comment)
        )

    def parse_rule(self, name: str, comment: str):
        templ = Template(_MATCH_RULE)
        var = self._new_var(_strip_func_prefix(name))
        self._func_parts.append(
            templ.render(var=var, func=name, early_ret=self.early_ret, comment=comment)
        )

    def parse_rule_zero_or_one(self, name: str, comment: str):
        templ = Template(_MATCH_RULE_ZERO_OR_ONE)
        var = self._new_var(_strip_func_prefix(name))
        self._func_parts.append(
            templ.render(var=var, func=name, early_ret=self.early_ret, comment=comment)
        )

    def parse_rule_zero_or_more(self, name: str, comment: str):
        templ = Template(_MATCH_RULE_ZERO_OR_MORE)
        temp_var = _strip_func_prefix(name)
        var = self._new_var(temp_var + "_list")

        self._func_parts.append(
            templ.render(
                temp_var=temp_var,
                var=var,
                func=name,
                early_ret=self.early_ret,
                ret_type=self.ret_type,
                comment=comment,
            )
        )

    def parse_rule_one_or_more(self, name: str, comment: str):
        templ = Template(_MATCH_RULE_ONE_OR_MORE)
        temp_var = _strip_func_prefix(name)
        var = self._new_var(temp_var + "_list")

        self._func_parts.append(
            templ.render(
                temp_var=temp_var,
                var=var,
                func=name,
                early_ret=self.early_ret,
                ret_type=self.ret_type,
                comment=comment,
            )
        )


class PyParserCodeGen(Jinja2ParserCodeGen):
    def __init__(self, name: str, cfg: Config):
        super().__init__(name, cfg, _TEMPL_FOLDER, _PARSER_TEMPL)
        self._vars["name"] = name.title()  # TODO: Make camel case

    @property
    def parser_filename(self) -> str:
        return "parser.py"

    @staticmethod
    def make_func_name(name: str, binding: str = "", sub: int = 0) -> str:
        prefix = "_parse_" if sub > 0 else "parse_"
        if binding:
            return f"{prefix}{name}_{binding}"

        return f"{prefix}{name}_inner{sub}" if sub > 0 else f"{prefix}{name}"

    def start_func(self, name: str, early_ret: bool, comment: str) -> ParserFuncCodeGen:
        return PyParserFuncCodeGen(
            name, early_ret, self._vars["make_parse_tree"], comment, self._actions
        )

    def end_func(self, codegen: ParserFuncCodeGen):
        self._vars["ret_type"] = codegen.ret_type
        self._funcs.append(codegen.generate())
