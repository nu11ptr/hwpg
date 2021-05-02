from typing import List

from jinja2 import Template

from mlpg.parsergen import (
    BaseParserFuncCodeGen,
    ParserFuncCodeGen,
    Jinja2ParserCodeGen,
    TreeMaker,
)

_FUNC_START = '''    def {{ name }}(self) -> Optional[{{ ret_type }}]:
        """
        {{ comment }}
        """
        old_pos = self.pos


'''

_FUNC_END_EARLY_RET = """        self.pos = old_pos
        return None
"""

_FUNC_END = """        return Tree({{ vars }})
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


class PyParserFuncCodeGen(BaseParserFuncCodeGen):
    def __init__(
        self,
        name: str,
        ret_type: str,
        early_ret: bool,
        comment: str,
        tree_maker: TreeMaker,
    ):
        super().__init__(name, ret_type, early_ret, comment, tree_maker)

        templ = Template(_FUNC_START)
        self._func_parts.append(
            templ.render(name=name, ret_type=ret_type, comment=self.comment)
        )

    def _end_func(self):
        if self.early_ret:
            self._func_parts.append(_FUNC_END_EARLY_RET)
        else:
            templ = Template(_FUNC_END)
            self._func_parts.append(templ.render(vars=", ".join(self._vars)))

    @staticmethod
    def _strip_func_prefix(name: str) -> str:
        # Remove 'parse_' (6 chars) or '_parse_' prefix (7 chars)
        return name[6:] if name.startswith("parse_") else name[7:]

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
        var = self._new_var(self._strip_func_prefix(name))
        self._func_parts.append(
            templ.render(var=var, func=name, early_ret=self.early_ret, comment=comment)
        )

    def parse_rule_zero_or_one(self, name: str, comment: str):
        templ = Template(_MATCH_RULE_ZERO_OR_ONE)
        var = self._new_var(self._strip_func_prefix(name))
        self._func_parts.append(
            templ.render(var=var, func=name, early_ret=self.early_ret, comment=comment)
        )

    def parse_rule_zero_or_more(self, name: str, comment: str):
        templ = Template(_MATCH_RULE_ZERO_OR_MORE)
        temp_var = self._strip_func_prefix(name)
        var = self._new_var(temp_var + "_list")
        ret_type = self._tree_maker.return_type(name)

        self._func_parts.append(
            templ.render(
                temp_var=temp_var,
                var=var,
                func=name,
                early_ret=self.early_ret,
                ret_type=ret_type,
                comment=comment,
            )
        )

    def parse_rule_one_or_more(self, name: str, comment: str):
        templ = Template(_MATCH_RULE_ONE_OR_MORE)
        temp_var = self._strip_func_prefix(name)
        var = self._new_var(temp_var + "_list")
        ret_type = self._tree_maker.return_type(name)

        self._func_parts.append(
            templ.render(
                temp_var=temp_var,
                var=var,
                func=name,
                early_ret=self.early_ret,
                ret_type=ret_type,
                comment=comment,
            )
        )


class PyParserCodeGen(Jinja2ParserCodeGen):
    def __init__(self, name: str, tree_maker: TreeMaker, memoize: bool = True):
        super().__init__("templates/python", "parser.py.j2")
        self._tree_maker = tree_maker
        self.name = name
        self._vars["name"] = name.title()  # TODO: Make camel case
        self._vars["memoize"] = memoize

    def parser_filename(self) -> str:
        return "parser.py"

    @staticmethod
    def make_func_name(name: str, sub: int = 0, depth: int = 0) -> str:
        return f"_parse_{name}_sub{sub}_depth{depth}" if sub > 0 else f"parse_{name}"

    def start_func(self, name: str, early_ret: bool, comment: str) -> ParserFuncCodeGen:
        ret_type = self._tree_maker.return_type(name)
        return PyParserFuncCodeGen(name, ret_type, early_ret, comment, self._tree_maker)

    def end_func(self, codegen: ParserFuncCodeGen):
        self._funcs.append(codegen.generate())


class Tree:
    pass


class PyParseTreeMaker:
    def return_type(self, name: str) -> str:
        return "Tree"
