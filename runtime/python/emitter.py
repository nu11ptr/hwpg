from jinja2 import Template

from mlpg.parsergen import BaseFuncEmitter, FuncEmitter, Jinja2CodeEmitter, TreeMaker

_FUNC_START = """    def {{ name }}(self) -> {{ ret_type }}:
        old_pos = self.pos


"""

_MATCH_TOKEN = """        {{ var }} = self._match_token_or_rollback(TokenType.{{ name }}, old_pos)
{%- if ret %}
        return {{ var }} if {{ var }} else None
{% else %}
        if not {{ var }}:
            return None
{% endif %}

"""

_MATCH_TOKEN_ZERO_OR_ONE = """        {{ var }} = self._try_match_token(TokenType.{{ name }})
{%- if ret %}
        if {{ var }}:
            return {{ var }}
{% endif %}

"""

_MATCH_TOKEN_ZERO_OR_MORE = """        {{ var }}_list = self._try_match_tokens(TokenType.{{ name }})
{%- if ret %}
        if {{ var }}_list:
            return {{ var }}_list
{% endif %}

"""

_MATCH_TOKEN_ONE_OR_MORE = """        {{ var }}_list = self._match_tokens_or_rollback(TokenType.{{ name }}, old_pos)
{%- if ret %}
        return {{ var }}_list if {{ var }}_list else None
{% else %}
        if not {{ var }}_list:
            return None
{% endif %}

"""

_MATCH_RULE = """        {{ var }} = self.{{ func }}(self)
        if not {{ var }}:
            self.pos = old_pos
            return None
{% if ret %}
        return {{ var }}
{% endif %}

"""

_MATCH_RULE_ZERO_OR_ONE = """        {{ var }} = self.{{ func }}(self)
{%- if ret %}
        if {{ var }}:
            return {{ var }}
{% endif %}

"""

_MATCH_RULE_ZERO_OR_MORE = """        {{ var }}_list: List[{{ ret_type }}] = []
        while True:
            {{ var }} = self.{{ func }}(self)
            if not {{ var }}:
                break
            {{ var }}_list.append(var)
{% if ret %}
        if {{ var }}_list:
            return {{ var }}_list
{% endif %}

"""

_MATCH_RULE_ONE_OR_MORE = """        {{ var }}_list: List[{{ ret_type }}] = []
        while True:
            {{ var }} = self.{{ func }}(self)
            if not {{ var }}:
                break
            {{ var }}_list.append(var)

        if not {{ var }}_list:
            self.pos = old_pos
            return None
{% if ret %}
        return {{ var }}_list
{% endif %}

"""


class PyFuncEmitter(BaseFuncEmitter):
    def __init__(self, name: str, ret_type: str, tree_maker: TreeMaker):
        super().__init__(name, ret_type)
        self._tree_maker = tree_maker

        templ = Template(_FUNC_START)
        self._func_parts.append(templ.render(name=name, ret_type=ret_type))

    @staticmethod
    def _strip_func_prefix(name: str) -> str:
        # Remove 'parse_' (6 chars) or '_parse_' prefix (7 chars)
        return name[6:] if name.startswith("parse_") else name[7:]

    def match_token(self, name: str, ret: bool):
        templ = Template(_MATCH_TOKEN)
        self._func_parts.append(templ.render(name=name, var=name.lower()))

    def match_token_zero_or_one(self, name: str, ret: bool):
        templ = Template(_MATCH_TOKEN_ZERO_OR_ONE)
        self._func_parts.append(templ.render(name=name, var=name.lower(), ret=ret))

    def match_token_zero_or_more(self, name: str, ret: bool):
        templ = Template(_MATCH_TOKEN_ZERO_OR_MORE)
        self._func_parts.append(templ.render(name=name, var=name.lower(), ret=ret))

    def match_token_one_or_more(self, name: str, ret: bool):
        templ = Template(_MATCH_TOKEN_ONE_OR_MORE)
        self._func_parts.append(templ.render(name=name, var=name.lower(), ret=ret))

    def match_rule(self, name: str, ret: bool):
        templ = Template(_MATCH_RULE)
        var = self._strip_func_prefix(name)
        self._func_parts.append(templ.render(var=var, func=name, ret=ret))

    def match_rule_zero_or_one(self, name: str, ret: bool):
        templ = Template(_MATCH_RULE_ZERO_OR_ONE)
        var = self._strip_func_prefix(name)
        self._func_parts.append(templ.render(var=var, func=name, ret=ret))

    def match_rule_zero_or_more(self, name: str, ret: bool):
        templ = Template(_MATCH_RULE_ZERO_OR_MORE)
        var = self._strip_func_prefix(name)
        ret_type = self._tree_maker.return_type(name)
        self._func_parts.append(
            templ.render(var=var, func=name, ret=ret, ret_type=ret_type)
        )

    def match_rule_one_or_more(self, name: str, ret: bool):
        templ = Template(_MATCH_RULE_ONE_OR_MORE)
        var = self._strip_func_prefix(name)
        ret_type = self._tree_maker.return_type(name)
        self._func_parts.append(
            templ.render(var=var, func=name, ret=ret, ret_type=ret_type)
        )


class PyCodeEmitter(Jinja2CodeEmitter):
    def __init__(self, tree_maker: TreeMaker, memoize: bool = True):
        super().__init__("templates/python", "parser.py.j2")
        self._tree_maker = tree_maker
        self._vars["memoize"] = memoize

    @staticmethod
    def make_func_name(name: str, sub: int = 0, depth: int = 0) -> str:
        return f"_parse_{name}_sub{sub}_depth{depth}" if sub > 0 else f"parse_{name}"

    def start_rule(self, name: str) -> FuncEmitter:
        ret_type = self._tree_maker.return_type(name)
        return PyFuncEmitter(name, ret_type, self._tree_maker)

    def end_rule(self, emitter: FuncEmitter):
        self._funcs.append(emitter.emit())


class Tree:
    pass


class PyParseTreeMaker:
    def return_type(self, name: str) -> str:
        return "Tree"
