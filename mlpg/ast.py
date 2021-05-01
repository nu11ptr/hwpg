from abc import abstractproperty, ABC
from dataclasses import dataclass
from typing import Any, List, Optional, Union

from lark import Token, Transformer


class Node(ABC):
    @abstractproperty
    def comment(self) -> str:
        pass


class NodeContainer(Node):
    pass


# rule_body
@dataclass
class Alternatives(NodeContainer):
    nodes: List[Node]

    @property
    def comment(self) -> str:
        return " | ".join([node.comment for node in self.nodes])


# rule_body
@dataclass
class MultipartBody(NodeContainer):
    nodes: List[Node]

    @property
    def comment(self) -> str:
        return " ".join([node.comment for node in self.nodes])


# rule_part
@dataclass
class ZeroOrMore(NodeContainer):
    node: Node

    @property
    def comment(self) -> str:
        # TODO: Generate parens for all containers, but to be really accurate, we'd
        # need to parse the parens and track whether we saw them or not
        if isinstance(self.node, NodeContainer):
            return f"({self.node.comment})*"
        else:
            return self.node.comment + "*"


# rule_part
@dataclass
class OneOrMore(NodeContainer):
    node: Node

    @property
    def comment(self) -> str:
        # TODO: Generate parens for all containers, but to be really accurate, we'd
        # need to parse the parens and track whether we saw them or not
        if isinstance(self.node, NodeContainer):
            return f"({self.node.comment})+"
        else:
            return self.node.comment + "+"


# rule_part
@dataclass
class ZeroOrOne(NodeContainer):
    node: Node
    brackets: bool

    @property
    def comment(self) -> str:
        if self.brackets:
            return "[" + self.node.comment + "]"
        else:
            # TODO: Generate parens for all containers, but to be really accurate, we'd
            # need to parse the parens and track whether we saw them or not
            if isinstance(self.node, NodeContainer):
                return f"({self.node.comment})?"
            else:
                return self.node.comment + "?"


# RULE_NAME
@dataclass
class RuleRef(Node):
    name: Token

    @property
    def comment(self) -> str:
        return self.name.value


# TOKEN_NAME
@dataclass
class TokenRef(Node):
    name: Token
    replaced_lit: Optional[Token] = None

    @property
    def comment(self) -> str:
        return self.name.value if not self.replaced_lit else self.replaced_lit.value


# TOKEN_LIT
@dataclass
class TokenLit(Node):
    literal: Token

    @property
    def comment(self) -> str:
        return '"' + self.literal.value + '"'


# rule
@dataclass
class Rule:
    name: Token
    node: Node

    @property
    def comment(self) -> str:
        return f"{self.name.value}: {self.node.comment}"


# token_rule
@dataclass
class TokenRule:
    name: Token
    literal: TokenLit  # For now, will evolve into more

    @property
    def comment(self) -> str:
        return f"{self.name.value}: {self.literal.comment}"


# grammar
@dataclass
class Grammar:
    rules: List[Rule]
    token_rules: List[TokenRule]


class ToAST(Transformer):
    def RULE_NAME(self, token: Token) -> RuleRef:
        return RuleRef(token)

    def TOKEN_NAME(self, token: Token) -> TokenRef:
        return TokenRef(token)

    def TOKEN_LIT(self, token: Token) -> TokenLit:
        return TokenLit(token)

    def grammar(self, rules: List[Union[Rule, TokenRule]]) -> Grammar:
        parse_rules, token_rules = [], []

        for rule in rules:
            if isinstance(rule, Rule):
                parse_rules.append(rule)
            elif isinstance(rule, TokenRule):
                token_rules.append(rule)
            else:
                raise AssertionError("Unknown object")

        return Grammar(parse_rules, token_rules)

    def entry(self, args: List[Union[Rule, TokenRule]]) -> Union[Rule, TokenRule]:
        return args[0]

    def token_rule(self, args: List[Any]) -> TokenRule:
        return TokenRule(args[0].name, args[1])

    def rule(self, args: List[Any]) -> Rule:
        return Rule(args[0].name, args[1])

    def rule_body(self, parts: List[Node]) -> Node:
        rules: List[Node] = []
        alts: List[Node] = []

        for part in parts:
            # When we hit a pipe in the stream, end current alternative
            if isinstance(part, Token) and "|" in part.value:
                # If multiple rules, nest inside multipartbody otherwise just node itself
                alts.append(MultipartBody(rules) if len(rules) > 1 else rules[0])
                rules = []
                continue

            rules.append(part)

        alts.append(MultipartBody(rules) if len(rules) > 1 else rules[0])
        return Alternatives(alts) if len(alts) > 1 else alts[0]

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
                return ZeroOrOne(rule_elem, brackets=False)

            raise AssertionError(f"Unknown suffix: {suffix}")
        # rule body in between square brackets
        elif rule_len == 3:
            return ZeroOrOne(args[1], brackets=True)

        raise AssertionError(f"Rule length isn't 1-3: {rule_len}")
