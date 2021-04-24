from dataclasses import dataclass
from typing import Any, List

from lark import Token, Transformer


@dataclass
class Node:
    pass


# rule_body
@dataclass
class RuleBody(Node):
    rules: List[List[Node]]


# rule_part
@dataclass
class ZeroOrMore(Node):
    node: Node


# rule_part
@dataclass
class OneOrMore(Node):
    node: Node


# rule_part
@dataclass
class ZeroOrOne(Node):
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

    def rule_body(self, args: List[List[Node]]) -> RuleBody:
        return RuleBody(args)

    def rule_part(self, args: List[Any]) -> Node:
        # Has no suffix - return 'as-is'
        rule_len = len(args)
        if rule_len == 1:
            return args[0]

        assert rule_len == 2, f"Rule length isn't 1 or 2: {rule_len}"

        rule_elem, suffix = args
        if suffix == "+":
            return OneOrMore(rule_elem)
        if suffix == "*":
            return ZeroOrMore(rule_elem)
        if suffix == "?":
            return ZeroOrOne(rule_elem)

        raise AssertionError(f"Unknown suffix: {suffix}")
