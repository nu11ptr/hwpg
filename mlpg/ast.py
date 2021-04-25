from dataclasses import dataclass
from typing import Any, List

from lark import Token, Transformer


@dataclass
class Node:
    pass


@dataclass
class NodeContainer(Node):
    pass


# rule_body
@dataclass
class RuleBody(NodeContainer):
    rules: List[List[Node]]


# rule_part
@dataclass
class ZeroOrMore(NodeContainer):
    node: Node


# rule_part
@dataclass
class OneOrMore(NodeContainer):
    node: Node


# rule_part
@dataclass
class ZeroOrOne(NodeContainer):
    node: Node


# RULE_NAME
@dataclass
class RuleRef(Node):
    name: str


# TOKEN_NAME
@dataclass
class TokenRef(Node):
    name: str


# TOKEN_LIT
@dataclass
class TokenLit(Node):
    literal: str


# rule
@dataclass
class Rule:
    name: str
    rules: RuleBody


# grammar
@dataclass
class Grammar:
    rules: List[Rule]


class ToAST(Transformer):
    def RULE_NAME(self, token: Token) -> RuleRef:
        return RuleRef(token.value)

    def TOKEN_NAME(self, token: Token) -> TokenRef:
        return TokenRef(token.value)

    def TOKEN_LIT(self, token: Token) -> TokenLit:
        return TokenLit(token.value)

    def grammar(self, rules: List[Rule]) -> Grammar:
        return Grammar(rules)

    def rule(self, args: List[Any]) -> Rule:
        return Rule(args[0].name, args[1])

    def rule_body(self, args: List[Node]) -> RuleBody:
        rules: List[Node] = []
        alternatives: List[List[Node]] = []

        for arg in args:
            # When we hit a pipe in the stream, end current alternative
            if isinstance(arg, Token) and arg.value == "|":
                alternatives.append(rules)
                rules = []
                continue

            rules.append(arg)

        alternatives.append(rules)
        return RuleBody(alternatives)

    def rule_part(self, args: List[Any]) -> Node:
        rule_len = len(args)

        # Has no suffix, nor in square brackets - return 'as-is'
        if rule_len == 1:
            return args[0]
        # rule element followed by suffix
        elif rule_len == 2:
            rule_elem, suffix = args
            if suffix == "+":
                return OneOrMore(rule_elem)
            if suffix == "*":
                return ZeroOrMore(rule_elem)
            if suffix == "?":
                return ZeroOrOne(rule_elem)

            raise AssertionError(f"Unknown suffix: {suffix}")
        # rule body in between square brackets
        elif rule_len == 3:
            return ZeroOrOne(args[1])

        raise AssertionError(f"Rule length isn't 1-3: {rule_len}")
