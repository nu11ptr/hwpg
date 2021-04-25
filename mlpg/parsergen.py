from enum import auto, Enum
from typing import List, Protocol, Tuple

from mlpg.ast import (
    Grammar,
    Node,
    OneOrMore,
    Rule,
    RuleBody,
    RuleRef,
    TokenLit,
    TokenRef,
    ZeroOrMore,
    ZeroOrOne,
)


class TreeMaker(Protocol):
    def return_type(self, name: str) -> str:
        ...


class CodeEmitter(Protocol):
    def start(self, name: str) -> str:
        ...

    def end(self, name: str) -> str:
        ...

    def make_func_name(self, name: str, sub: int = 0, depth: int = 0) -> str:
        ...

    def start_rule(self, name: str) -> str:
        ...

    def end_rule(self, name: str) -> str:
        ...

    def match_token(self, name: str, ret: bool) -> str:
        ...

    def match_token_zero_or_one(self, name: str, ret: bool) -> str:
        ...

    def match_token_zero_or_more(self, name: str, ret: bool) -> str:
        ...

    def match_token_one_or_more(self, name: str, ret: bool) -> str:
        ...

    def match_rule(self, name: str, ret: bool) -> str:
        ...

    def match_rule_zero_or_one(self, name: str, ret: bool) -> str:
        ...

    def match_rule_zero_or_more(self, name: str, ret: bool) -> str:
        ...

    def match_rule_one_or_more(self, name: str, ret: bool) -> str:
        ...


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
        funcs: List[str],
        debugs: List[str],
        sub: int = 0,
        depth: int = 0,
    ):
        self._name = name
        self._emitter = emitter
        self._funcs = funcs
        self._debugs = debugs
        self._next_sub = sub
        self._depth = depth

        self._func_pieces: List[str] = []
        self._debug_pieces: List[str] = []

    def _debug(self, msg: str):
        self._debug_pieces.append(" " * self._depth * 4)
        self._debug_pieces.append(msg)

    def generate(self, nodes: List[List[Node]]) -> Tuple[str, int]:
        """
        Generates a new parser function (sub == 0) or sub-function (sub > 0). It
        returns a tuple of the generated function string and the next sub #
        """
        # Start new function
        func_name = self._emitter.make_func_name(
            self._name, self._next_sub, self._depth
        )
        func_start = self._emitter.start_rule(func_name)
        self._next_sub += 1
        self._func_pieces = [func_start]
        self._debug_pieces = []
        self._debug(f"Start func: {func_name}\n")

        self._gen_nodes(nodes)

        # End new function
        self._debug(f"End func: {func_name}\n")
        end = self._emitter.end_rule(func_name)
        self._func_pieces.append(end)

        # Store func str and debugs at the end so sub functions are added first
        self._funcs.append("\n".join(self._func_pieces))
        self._debugs.append("".join(self._debug_pieces))
        # print(self._debug_pieces)
        return func_name, self._next_sub

    def _gen_nodes(self, nodes: List[List[Node]]):
        num_alts = len(nodes)

        # Process all nodes
        for i, alt in enumerate(nodes):
            num_parts = len(alt)

            self._debug(f"Alternative {i}\n")

            # Early return on all but last alternative if we have a single seq
            last_alt = (num_alts - 1) == i
            ret = not last_alt and num_parts == 1

            # Sub-function needed? Only if multiple alternatives AND multiple parts
            if num_alts > 1 and num_parts > 1:
                sub_func = _FuncGen(
                    self._name,
                    self._emitter,
                    self._funcs,
                    self._debugs,
                    self._next_sub,
                    self._depth,
                )
                sub_name, self._next_sub = sub_func.generate([alt])
                match = Match.ZERO_OR_ONCE if not last_alt else Match.ONCE
                self._gen_sub_rule_ref(sub_name, match, ret)
            # Otherwise we can process each part independently
            else:
                for part in alt:
                    self._debug(f"Alt {i} Next Part (Return: {ret})\n")
                    self._gen_node(
                        part,
                        # NOTE: Only applies for a non-container
                        Match.ZERO_OR_ONCE if not last_alt else Match.ONCE,
                        ret,
                    )

    def _gen_node(self, node: Node, match: Match, ret: bool):
        type_ = type(node)

        if type_ is RuleBody:
            self._gen_rule_body(node, match, ret)  # type: ignore
        elif type_ is ZeroOrMore:
            self._gen_zero_or_more(node, ret)  # type: ignore
        elif type_ is OneOrMore:
            self._gen_one_or_more(node, ret)  # type: ignore
        elif type_ is ZeroOrOne:
            self._gen_zero_or_one(node, ret)  # type: ignore
        elif type_ is RuleRef:
            self._gen_rule_ref(node, match, ret)  # type: ignore
        elif type_ is TokenRef:
            self._gen_token_ref(node, match, ret)  # type: ignore
        elif type_ is TokenLit:
            self._gen_token_lit(node, match, ret)  # type: ignore
        else:
            raise AssertionError(f"Unknown node type: {type_}")

    def _gen_rule_body(self, body: RuleBody, match: Match, ret: bool):
        # Any time we process a new nested rule body, we need a new sub-function
        # FIXME: What if it has one part in one alt? (correct this before parser gen)

        sub_func = _FuncGen(
            self._name,
            self._emitter,
            self._funcs,
            self._debugs,
            self._next_sub,
            self._depth + 1,
        )
        sub_name, self._next_sub = sub_func.generate(body.rules)
        self._gen_sub_rule_ref(sub_name, match, ret)

    def _gen_zero_or_more(self, zom: ZeroOrMore, ret: bool):
        self._debug("ZeroOrMore\n")
        self._gen_node(zom.node, Match.ZERO_OR_MORE, ret)

    def _gen_one_or_more(self, oom: OneOrMore, ret: bool):
        self._debug("OneOrMore\n")
        self._gen_node(oom.node, Match.ONCE_OR_MORE, ret)

    def _gen_zero_or_one(self, zoo: ZeroOrOne, ret: bool):
        self._debug("ZeroOrOne\n")
        self._gen_node(zoo.node, Match.ZERO_OR_ONCE, ret)

    def _emit_rule_match(self, name: str, match: Match, ret: bool):
        if match == Match.ONCE:
            snippet = self._emitter.match_rule(name, ret)
        elif match == Match.ZERO_OR_ONCE:
            snippet = self._emitter.match_rule_zero_or_one(name, ret)
        elif match == Match.ZERO_OR_MORE:
            snippet = self._emitter.match_rule_zero_or_more(name, ret)
        elif match == Match.ONCE_OR_MORE:
            snippet = self._emitter.match_rule_one_or_more(name, ret)
        else:
            raise AssertionError(f"Unknown match value: {match}")

        self._func_pieces.append(snippet)

    def _gen_sub_rule_ref(self, name: str, match: Match, ret: bool):
        self._debug(f"Sub-rule {name} ({match} ret:{ret})\n")
        self._emit_rule_match(name, match, ret)

    def _gen_rule_ref(self, rr: RuleRef, match: Match, ret: bool):
        self._debug(f"RuleRef {rr.name} ({match} ret:{ret})\n")
        self._emit_rule_match(self._emitter.make_func_name(rr.name), match, ret)

    def _emit_token_match(self, name: str, match: Match, ret: bool):
        if match == Match.ONCE:
            snippet = self._emitter.match_token(name, ret)
        elif match == Match.ZERO_OR_ONCE:
            snippet = self._emitter.match_token_zero_or_one(name, ret)
        elif match == Match.ZERO_OR_MORE:
            snippet = self._emitter.match_token_zero_or_more(name, ret)
        elif match == Match.ONCE_OR_MORE:
            snippet = self._emitter.match_token_one_or_more(name, ret)
        else:
            raise AssertionError(f"Unknown match value: {match}")

        self._func_pieces.append(snippet)

    def _gen_token_ref(self, tr: TokenRef, match: Match, ret: bool):
        self._debug(f"TokenRef {tr.name} ({match} ret:{ret})\n")
        self._emit_token_match(tr.name, match, ret)

    def _gen_token_lit(self, tl: TokenLit, match: Match, ret: bool):
        self._debug(f"TokenLit {tl.literal} ({match} ret:{ret})\n")
        # TODO: Figure out how to map literal to token name (likely ahead of time)
        self._emit_token_match(f"<{tl.literal}>", match, ret)


class ParserGen:
    def __init__(self, emitter: CodeEmitter):
        self._emitter = emitter
        self._funcs: List[str] = []
        self._debugs: List[str] = []

    def generate(self, name: str, grammar: Grammar) -> Tuple[str, str]:
        """
        Generates a parser class/struct and associated parser functions. It
        returns a tuple of the parser and debug string
        """
        self._funcs = []
        self._debugs = []

        start, end = self._gen_grammar(name, grammar)
        pieces = [start]

        for func_pieces in self._funcs:
            pieces.append(func_pieces)

        pieces.append(end)

        return "\n\n".join(pieces), "".join(self._debugs)

    def _gen_grammar(self, name: str, grammar: Grammar) -> Tuple[str, str]:
        self._debugs.append(f"Grammar {name}\n")
        start = self._emitter.start(name)

        for rule in grammar.rules:
            self._gen_rule(rule)

        end = self._emitter.end(name)
        return start, end

    def _gen_rule(self, rule: Rule):
        self._debugs.append(f"\nRule start: {rule.name}\n")

        func = _FuncGen(rule.name, self._emitter, self._funcs, self._debugs)
        func.generate(rule.rules.rules)

        self._debugs.append(f"Rule end: {rule.name}\n\n")
