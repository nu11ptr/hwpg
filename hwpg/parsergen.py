from __future__ import annotations
from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template

from hwpg.ast import (
    Alternatives,
    Grammar,
    MultipartBody,
    Node,
    OneOrMore,
    Rule,
    RuleRef,
    TokenLit,
    TokenRef,
    ZeroOrMore,
    ZeroOrOne,
)

TemplData = Dict[str, Any]

if TYPE_CHECKING:
    from hwpg.config import Config


class ParserActions(Protocol):
    """Interface for user defined ParserActions classes"""

    def import_code(self) -> str:
        ...

    def init_code(self) -> str:
        ...


class ParserFuncCodeGen(Protocol):
    """Parser function code generator interface"""

    name: str
    comment: str
    ret_type: str
    early_ret: bool

    def generate(self) -> str:
        ...

    def match_token(self, name: str, comment: str):
        ...

    def match_token_zero_or_one(self, name: str, comment: str):
        ...

    def match_token_zero_or_more(self, name: str, comment: str):
        ...

    def match_token_one_or_more(self, name: str, comment: str):
        ...

    def parse_rule(self, name: str, comment: str):
        ...

    def parse_rule_zero_or_one(self, name: str, comment: str):
        ...

    def parse_rule_zero_or_more(self, name: str, comment: str):
        ...

    def parse_rule_one_or_more(self, name: str, comment: str):
        ...


class ParserCodeGen(Protocol):
    """Top level parser code generator interface"""

    def generate(self) -> str:
        ...

    @staticmethod
    def make_func_name(name: str, binding: str = "", sub: int = 0) -> str:
        ...

    @classmethod
    def parser_filename(self) -> str:
        ...

    def start_func(self, name: str, early_ret: bool, comment: str) -> ParserFuncCodeGen:
        ...

    def end_func(self, codegen: ParserFuncCodeGen):
        ...


class Jinja2ParserFuncCodeGen(ABC):
    """Base class for parser function code generator subclasses"""

    _default_action: Tuple[str, str]
    _func_start_templ: str
    _early_ret_templ: str
    _match_token_templ: str
    _match_token_zero_or_one_templ: str
    _match_token_zero_or_more_templ: str
    _match_token_one_or_more_templ: str
    _parse_rule_templ: str
    _parse_rule_zero_or_one_templ: str
    _parse_rule_zero_or_more_templ: str
    _parse_rule_one_or_more_templ: str

    def __init__(
        self,
        name: str,
        attr_name: str,
        early_ret: bool,
        make_parse_tree: bool,
        comment: str,
        actions: Optional[ParserActions],
    ):
        self.name = name
        self.early_ret = early_ret
        self.comment = comment
        self._actions = actions
        self._make_parse_tree = make_parse_tree
        self._action, self.ret_type = self._func_actions(attr_name)

        self._vars: List[str] = []
        self._func_parts: List[str] = []

        vars = self._start_func()
        self._render_templ(self._func_start_templ, vars)

    def _func_actions(self, name: str) -> Tuple[str, str]:
        if not self._actions:
            return self._default_action

        try:
            func = getattr(self._actions, name)
        except AttributeError:
            if not self._make_parse_tree:
                raise RuntimeError(f"Parser actions missing function '{name}'")

            return self._default_action

        return func()

    def _new_var(self, name: str) -> str:
        new_name = name
        idx = 1

        while new_name in self._vars:
            idx += 1
            new_name = name + str(idx)

        self._vars.append(new_name)
        return new_name

    @abstractmethod
    def _start_func(self) -> TemplData:
        pass

    @abstractmethod
    def _end_func(self) -> TemplData:
        pass

    @abstractmethod
    def _match_token(self, name: str, comment: str) -> TemplData:
        pass

    @abstractmethod
    def _match_token_zero_or_one(self, name: str, comment: str) -> TemplData:
        pass

    @abstractmethod
    def _match_token_zero_or_more(self, name: str, comment: str) -> TemplData:
        pass

    @abstractmethod
    def _match_token_one_or_more(self, name: str, comment: str) -> TemplData:
        pass

    @abstractmethod
    def _parse_rule(self, name: str, comment: str) -> TemplData:
        pass

    @abstractmethod
    def _parse_rule_zero_or_one(self, name: str, comment: str) -> TemplData:
        pass

    @abstractmethod
    def _parse_rule_zero_or_more(self, name: str, comment: str) -> TemplData:
        pass

    @abstractmethod
    def _parse_rule_one_or_more(self, name: str, comment: str) -> TemplData:
        pass

    def _render_templ(self, templ_str: str, vars: Dict[str, Any]):
        templ = Template(templ_str)
        self._func_parts.append(templ.render(**vars))

    def generate(self) -> str:
        if self.early_ret:
            self._func_parts.append(self._early_ret_templ)
        else:
            templ, vars = self._action, self._end_func()
            self._render_templ(templ, vars)

        return "".join(self._func_parts)

    def match_token(self, name: str, comment: str):
        vars = self._match_token(name, comment)
        self._render_templ(self._match_token_templ, vars)

    def match_token_zero_or_one(self, name: str, comment: str):
        vars = self._match_token_zero_or_one(name, comment)
        self._render_templ(self._match_token_zero_or_one_templ, vars)

    def match_token_zero_or_more(self, name: str, comment: str):
        vars = self._match_token_zero_or_more(name, comment)
        self._render_templ(self._match_token_zero_or_more_templ, vars)

    def match_token_one_or_more(self, name: str, comment: str):
        vars = self._match_token_one_or_more(name, comment)
        self._render_templ(self._match_token_one_or_more_templ, vars)

    def parse_rule(self, name: str, comment: str):
        vars = self._parse_rule(name, comment)
        self._render_templ(self._parse_rule_templ, vars)

    def parse_rule_zero_or_one(self, name: str, comment: str):
        vars = self._parse_rule_zero_or_one(name, comment)
        self._render_templ(self._parse_rule_zero_or_one_templ, vars)

    def parse_rule_zero_or_more(self, name: str, comment: str):
        vars = self._parse_rule_zero_or_more(name, comment)
        self._render_templ(self._parse_rule_zero_or_more_templ, vars)

    def parse_rule_one_or_more(self, name: str, comment: str):
        vars = self._parse_rule_one_or_more(name, comment)
        self._render_templ(self._parse_rule_one_or_more_templ, vars)


class Jinja2ParserCodeGen:
    """Base class for parser code generator subclasses"""

    _parser_func_codegen: Callable[
        [str, bool, bool, str, Optional[ParserActions]], ParserFuncCodeGen
    ]
    _templ_dir: str
    _parser_templ: str

    def __init__(self, name: str, cfg: Config):
        loader = FileSystemLoader(type(self)._templ_dir)
        self._env = Environment(loader=loader, undefined=StrictUndefined)
        self._main_templ = self._env.get_template(type(self)._parser_templ)
        self._actions = cfg.parser_actions
        self.name = name

        self._vars: Dict[str, Any] = {
            "make_parse_tree": cfg.make_parse_tree,
            "memoize": cfg.memoize,
            "name": self._name,
        }
        self._funcs: List[str] = []

    @classmethod
    def parser_filename(cls) -> str:
        return cls._parser_templ[:-3]

    @property
    def _name(self):
        return self.name

    def start_func(self, name: str, early_ret: bool, comment: str) -> ParserFuncCodeGen:
        return type(self)._parser_func_codegen(
            name, early_ret, self._vars["make_parse_tree"], comment, self._actions
        )

    def end_func(self, codegen: ParserFuncCodeGen):
        self._vars["ret_type"] = codegen.ret_type
        self._funcs.append(codegen.generate())

    def generate(self) -> str:
        self._vars["functions"] = self._funcs
        return self._main_templ.render(**self._vars)


class Match(Enum):
    ONCE = auto()
    ZERO_OR_ONCE = auto()
    ZERO_OR_MORE = auto()
    ONCE_OR_MORE = auto()


class _ParserFuncGen:
    """Language agnostic parser function generator"""

    def __init__(
        self,
        name: str,
        codegen: ParserCodeGen,
        debugs: List[str],
        sub: int = 0,
        depth: int = 0,
    ):
        self._name = name
        self._codegen = codegen
        self._debugs = debugs
        self._next_sub = sub
        self._depth = depth

        self._func_codegen: ParserFuncCodeGen
        self._debug_pieces: List[str] = []

    def _debug(self, msg: str):
        self._debug_pieces.append(" " * self._depth * 4)
        self._debug_pieces.append(msg)

    def generate(
        self, node: Node, comment: str, binding: Optional[str] = None
    ) -> Tuple[str, int]:
        """
        Generates a new parser function. It returns a tuple of the generated
        function string and the next sub #
        """
        # Figure out name for new function before starting function itself
        binding = node.binding.value if node.binding else ""
        func_name = self._codegen.make_func_name(self._name, binding, self._next_sub)

        # Only a multipart body disallows early return
        early_ret = not isinstance(node, MultipartBody)
        self._func_codegen = self._codegen.start_func(func_name, early_ret, comment)
        func_name = self._func_codegen.name
        self._next_sub += 1
        self._debug_pieces = []
        self._debug(f"Start func: {func_name}\n")

        self._gen_node(node, node.comment, top_level=True)

        # End new function
        self._debug(f"End func: {func_name}\n")
        self._codegen.end_func(self._func_codegen)

        # Store func str and debugs at the end so sub functions are added first
        self._debugs.append("".join(self._debug_pieces))
        return func_name, self._next_sub

    def _gen_node(
        self,
        node: Node,
        comment: str,
        match: Match = Match.ONCE,
        top_level: bool = False,
    ):
        type_ = type(node)

        if type_ is Alternatives:
            if top_level:
                self._gen_alternatives(node)  # type: ignore
            else:
                # Always generate a sub-rule for nested alternative rules
                self._gen_sub_rule_ref(node, match, comment)
        elif type_ is MultipartBody:
            if top_level:
                self._gen_multipart_body(node)  # type: ignore
            else:
                # Always generate a sub-rule for nested multipart rules
                self._gen_sub_rule_ref(node, match, comment)
        elif type_ is ZeroOrMore:
            self._gen_zero_or_more(node)  # type: ignore
        elif type_ is OneOrMore:
            self._gen_one_or_more(node)  # type: ignore
        elif type_ is ZeroOrOne:
            self._gen_zero_or_one(node)  # type: ignore
        elif type_ is RuleRef:
            self._gen_rule_ref(node, match, comment)  # type: ignore
        elif type_ is TokenRef:
            self._gen_token_ref(node, match, comment)  # type: ignore
        elif type_ is TokenLit:
            self._gen_token_lit(node, match, comment)  # type: ignore
        else:
            raise AssertionError(f"Unknown node type: {type_}")

    def _gen_alternatives(self, alts: Alternatives):
        for alt in alts.nodes:
            self._gen_node(alt, alt.comment, Match.ZERO_OR_ONCE)

    def _gen_multipart_body(self, body: MultipartBody):
        for part in body.nodes:
            self._gen_node(part, part.comment, Match.ONCE)

    def _gen_zero_or_more(self, zom: ZeroOrMore):
        self._debug("ZeroOrMore\n")
        self._gen_node(zom.node, zom.comment, Match.ZERO_OR_MORE)

    def _gen_one_or_more(self, oom: OneOrMore):
        self._debug("OneOrMore\n")
        self._gen_node(oom.node, oom.comment, Match.ONCE_OR_MORE)

    def _gen_zero_or_one(self, zoo: ZeroOrOne):
        self._debug("ZeroOrOne\n")
        self._gen_node(zoo.node, zoo.comment, Match.ZERO_OR_ONCE)

    def _gen_rule_match(self, name: str, match: Match, comment: str):
        if match == Match.ONCE:
            self._func_codegen.parse_rule(name, comment)
        elif match == Match.ZERO_OR_ONCE:
            self._func_codegen.parse_rule_zero_or_one(name, comment)
        elif match == Match.ZERO_OR_MORE:
            self._func_codegen.parse_rule_zero_or_more(name, comment)
        elif match == Match.ONCE_OR_MORE:
            self._func_codegen.parse_rule_one_or_more(name, comment)
        else:
            raise AssertionError(f"Unknown match value: {match}")

    def _gen_sub_rule_ref(self, node: Node, match: Match, comment: str):
        # Before handling current level, generate the nested function
        sub_func = _ParserFuncGen(
            self._name,
            self._codegen,
            self._debugs,
            self._next_sub,
            self._depth + 1,
        )
        sub_name, self._next_sub = sub_func.generate(node, node.comment)

        self._debug(f"Sub-rule {sub_name} ({match}\n")
        self._gen_rule_match(sub_name, match, comment)

    def _gen_rule_ref(self, rr: RuleRef, match: Match, comment: str):
        name = rr.name.value
        self._debug(f"RuleRef {name} ({match}\n")
        func_name = self._codegen.make_func_name(name)
        self._gen_rule_match(func_name, match, comment)

    def _gen_token_match(self, name: str, match: Match, comment: str):
        if match == Match.ONCE:
            self._func_codegen.match_token(name, comment)
        elif match == Match.ZERO_OR_ONCE:
            self._func_codegen.match_token_zero_or_one(name, comment)
        elif match == Match.ZERO_OR_MORE:
            self._func_codegen.match_token_zero_or_more(name, comment)
        elif match == Match.ONCE_OR_MORE:
            self._func_codegen.match_token_one_or_more(name, comment)
        else:
            raise AssertionError(f"Unknown match value: {match}")

    def _gen_token_ref(self, tr: TokenRef, match: Match, comment: str):
        name = tr.name.value
        self._debug(f"TokenRef {name} ({match})\n")
        self._gen_token_match(name, match, comment)

    def _gen_token_lit(self, tl: TokenLit, match: Match, comment: str):
        raise AssertionError(
            "Token literals cannot be generated - they should be replaced during AST processing"
        )


class ParserGen:
    """Language agnostic parser generator"""

    def __init__(self, codegen: ParserCodeGen):
        self._codegen = codegen
        self._debugs: List[str] = []

    def generate(self, grammar: Grammar) -> Tuple[str, str]:
        """
        Generates a parser class/struct and associated parser functions. It
        returns a tuple of the parser and debug string
        """
        self._debugs = []
        self._gen_grammar(grammar)
        return self._codegen.generate(), "".join(self._debugs)

    def _gen_grammar(self, grammar: Grammar):
        self._debugs.append("Grammar\n")

        for rule in grammar.rules:
            self._gen_rule(rule)

    def _gen_rule(self, rule: Rule):
        name = rule.name.value
        self._debugs.append(f"\nRule start: {name}\n")

        func = _ParserFuncGen(name, self._codegen, self._debugs)
        func.generate(rule.node, rule.comment)

        self._debugs.append(f"Rule end: {name}\n\n")
