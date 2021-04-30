from enum import auto, Enum
from typing import Any, Dict, List, Protocol, Tuple

from jinja2 import Environment, FileSystemLoader

from mlpg.ast import (
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


class TreeMaker(Protocol):
    def return_type(self, name: str) -> str:
        ...


class FuncEmitter(Protocol):
    name: str
    ret_type: str
    early_ret: bool

    def emit(self) -> str:
        ...

    def match_token(self, name: str):
        ...

    def match_token_zero_or_one(self, name: str):
        ...

    def match_token_zero_or_more(self, name: str):
        ...

    def match_token_one_or_more(self, name: str):
        ...

    def parse_rule(self, name: str):
        ...

    def parse_rule_zero_or_one(self, name: str):
        ...

    def parse_rule_zero_or_more(self, name: str):
        ...

    def parse_rule_one_or_more(self, name: str):
        ...


class CodeEmitter(Protocol):
    def emit(self) -> str:
        ...

    @staticmethod
    def make_func_name(name: str, sub: int = 0, depth: int = 0) -> str:
        ...

    def parser_filename(self) -> str:
        ...

    def start_func(self, name: str, early_ret: bool) -> FuncEmitter:
        ...

    def end_func(self, emitter: FuncEmitter):
        ...


class BaseFuncEmitter:
    def __init__(
        self, name: str, ret_type: str, early_ret: bool, tree_maker: TreeMaker
    ):
        self.name = name
        self.ret_type = ret_type
        self.early_ret = early_ret
        self._tree_maker = tree_maker

        self._vars: List[str] = []
        self._func_parts: List[str] = []

    def _new_var(self, name: str) -> str:
        new_name = name
        idx = 1

        while new_name in self._vars:
            idx += 1
            new_name = name + str(idx)

        self._vars.append(new_name)
        return new_name

    def _end_func(self):
        pass

    def emit(self) -> str:
        self._end_func()
        return "".join(self._func_parts)


class Jinja2CodeEmitter:
    def __init__(self, templates: str, filename: str):
        loader = FileSystemLoader(templates)
        self._env = Environment(loader=loader)
        self._main_templ = self._env.get_template(filename)

        self._vars: Dict[str, Any] = {}
        self._funcs: List[str] = []

    def _end_code(self):
        pass

    def emit(self) -> str:
        self._end_code()
        self._vars["functions"] = self._funcs
        return self._main_templ.render(**self._vars)


class Match(Enum):
    ONCE = auto()
    ZERO_OR_ONCE = auto()
    ZERO_OR_MORE = auto()
    ONCE_OR_MORE = auto()


class _FuncGen:
    def __init__(
        self,
        name: str,
        emitter: CodeEmitter,
        debugs: List[str],
        sub: int = 0,
        depth: int = 0,
    ):
        self._name = name
        self._emitter = emitter
        self._debugs = debugs
        self._next_sub = sub
        self._depth = depth

        self._func_emitter: FuncEmitter
        self._debug_pieces: List[str] = []

    def _debug(self, msg: str):
        self._debug_pieces.append(" " * self._depth * 4)
        self._debug_pieces.append(msg)

    def generate(self, node: Node) -> Tuple[str, int]:
        """
        Generates a new parser function. It returns a tuple of the generated
        function string and the next sub #
        """
        # Start new code function
        func_name = self._emitter.make_func_name(
            self._name, self._next_sub, self._depth
        )
        # Only a multipart body disallows early return
        early_ret = not isinstance(node, MultipartBody)
        self._func_emitter = self._emitter.start_func(func_name, early_ret)
        func_name = self._func_emitter.name
        self._next_sub += 1
        self._debug_pieces = []
        self._debug(f"Start func: {func_name}\n")

        self._gen_node(node, top_level=True)

        # End new function
        self._debug(f"End func: {func_name}\n")
        self._emitter.end_func(self._func_emitter)

        # Store func str and debugs at the end so sub functions are added first
        self._debugs.append("".join(self._debug_pieces))
        return func_name, self._next_sub

    def _gen_node(self, node: Node, match: Match = Match.ONCE, top_level: bool = False):
        type_ = type(node)

        if type_ is Alternatives:
            if top_level:
                self._gen_alternatives(node)  # type: ignore
            else:
                # Always generate a sub-rule for nested alternative rules
                self._gen_sub_rule_ref(node, match)
        elif type_ is MultipartBody:
            if top_level:
                self._gen_multipart_body(node)  # type: ignore
            else:
                # Always generate a sub-rule for nested multipart rules
                self._gen_sub_rule_ref(node, match)
        elif type_ is ZeroOrMore:
            self._gen_zero_or_more(node)  # type: ignore
        elif type_ is OneOrMore:
            self._gen_one_or_more(node)  # type: ignore
        elif type_ is ZeroOrOne:
            self._gen_zero_or_one(node)  # type: ignore
        elif type_ is RuleRef:
            self._gen_rule_ref(node, match)  # type: ignore
        elif type_ is TokenRef:
            self._gen_token_ref(node, match)  # type: ignore
        elif type_ is TokenLit:
            self._gen_token_lit(node, match)  # type: ignore
        else:
            raise AssertionError(f"Unknown node type: {type_}")

    def _gen_alternatives(self, alts: Alternatives):
        for alt in alts.nodes:
            self._gen_node(alt, Match.ZERO_OR_ONCE)

    def _gen_multipart_body(self, body: MultipartBody):
        for part in body.nodes:
            self._gen_node(part, Match.ONCE)

    def _gen_zero_or_more(self, zom: ZeroOrMore):
        self._debug("ZeroOrMore\n")
        self._gen_node(zom.node, Match.ZERO_OR_MORE)

    def _gen_one_or_more(self, oom: OneOrMore):
        self._debug("OneOrMore\n")
        self._gen_node(oom.node, Match.ONCE_OR_MORE)

    def _gen_zero_or_one(self, zoo: ZeroOrOne):
        self._debug("ZeroOrOne\n")
        self._gen_node(zoo.node, Match.ZERO_OR_ONCE)

    def _emit_rule_match(self, name: str, match: Match):
        if match == Match.ONCE:
            self._func_emitter.parse_rule(name)
        elif match == Match.ZERO_OR_ONCE:
            self._func_emitter.parse_rule_zero_or_one(name)
        elif match == Match.ZERO_OR_MORE:
            self._func_emitter.parse_rule_zero_or_more(name)
        elif match == Match.ONCE_OR_MORE:
            self._func_emitter.parse_rule_one_or_more(name)
        else:
            raise AssertionError(f"Unknown match value: {match}")

    def _gen_sub_rule_ref(self, node: Node, match: Match):
        # Before handling current level, generate the nested function
        sub_func = _FuncGen(
            self._name,
            self._emitter,
            self._debugs,
            self._next_sub,
            self._depth + 1,
        )
        sub_name, self._next_sub = sub_func.generate(node)

        self._debug(f"Sub-rule {sub_name} ({match}\n")
        self._emit_rule_match(sub_name, match)

    def _gen_rule_ref(self, rr: RuleRef, match: Match):
        name = rr.name.value
        self._debug(f"RuleRef {name} ({match}\n")
        self._emit_rule_match(self._emitter.make_func_name(name), match)

    def _emit_token_match(self, name: str, match: Match):
        if match == Match.ONCE:
            self._func_emitter.match_token(name)
        elif match == Match.ZERO_OR_ONCE:
            self._func_emitter.match_token_zero_or_one(name)
        elif match == Match.ZERO_OR_MORE:
            self._func_emitter.match_token_zero_or_more(name)
        elif match == Match.ONCE_OR_MORE:
            self._func_emitter.match_token_one_or_more(name)
        else:
            raise AssertionError(f"Unknown match value: {match}")

    def _gen_token_ref(self, tr: TokenRef, match: Match):
        name = tr.name.value
        self._debug(f"TokenRef {name} ({match})\n")
        self._emit_token_match(name, match)

    def _gen_token_lit(self, tl: TokenLit, match: Match):
        raise AssertionError(
            "Token literals cannot be generated - they should be replaced during AST processing"
        )


class ParserGen:
    def __init__(self, emitter: CodeEmitter):
        self._emitter = emitter
        self._debugs: List[str] = []

    def generate(self, grammar: Grammar) -> Tuple[str, str]:
        """
        Generates a parser class/struct and associated parser functions. It
        returns a tuple of the parser and debug string
        """
        self._debugs = []
        self._gen_grammar(grammar)
        return self._emitter.emit(), "".join(self._debugs)

    def _gen_grammar(self, grammar: Grammar):
        self._debugs.append("Grammar\n")

        for rule in grammar.rules:
            self._gen_rule(rule)

    def _gen_rule(self, rule: Rule):
        name = rule.name.value
        self._debugs.append(f"\nRule start: {name}\n")

        func = _FuncGen(name, self._emitter, self._debugs)
        func.generate(rule.node)

        self._debugs.append(f"Rule end: {name}\n\n")
