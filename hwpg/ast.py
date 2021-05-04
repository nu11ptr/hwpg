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
        return " ".join(
            [
                f"({node.comment})" if isinstance(node, Alternatives) else node.comment
                for node in self.nodes
            ]
        )


# rule_part
@dataclass
class ZeroOrMore(NodeContainer):
    binding: Optional[Token]
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
    binding: Optional[Token]
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
    binding: Optional[Token]
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
    binding: Optional[Token]
    name: Token

    @property
    def comment(self) -> str:
        return self.name.value


# TOKEN_NAME
@dataclass
class TokenRef(Node):
    binding: Optional[Token]
    name: Token
    replaced_lit: Optional[Token] = None

    @property
    def comment(self) -> str:
        return self.name.value if not self.replaced_lit else self.replaced_lit.value


# TOKEN_LIT
@dataclass
class TokenLit(Node):
    binding: Optional[Token]
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


def _wrap_token(binding: Optional[Token], node: Any) -> Node:
    if isinstance(node, Token):
        if node.type == "RULE_NAME":
            return RuleRef(binding, node)
        if node.type == "TOKEN_NAME":
            return TokenRef(binding, node)
        if node.type == "TOKEN_LIT":
            return TokenLit(binding, node)

        raise AssertionError(f"Unknown token type: {node.type}")

    return node


class ToAST(Transformer):
    def RULE_NAME(self, token: Token) -> Token:
        return token

    def TOKEN_NAME(self, token: Token) -> Token:
        return token

    def TOKEN_LIT(self, token: Token) -> Token:
        return token

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
        return TokenRule(args[0], TokenLit(None, args[1]))

    def rule(self, args: List[Any]) -> Rule:
        return Rule(args[0], args[1])

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

    def binding(self, args: List[Token]) -> List[Token]:
        return args

    def rule_part(self, args: List[Any]) -> Node:
        rule_len = len(args)

        remaining, next_idx = rule_len, 0
        binding: Optional[Token] = None

        # Has binding?
        if isinstance(args[0], List):
            binding = args[0][0]
            remaining, next_idx = rule_len - 1, 1

        # Has no suffix, nor in square brackets - return wrapped (if token)
        if remaining == 1:
            return _wrap_token(binding, args[next_idx])
        elif remaining == 2:
            rule_elem, suffix = args[next_idx:]
            if suffix == "+":
                return OneOrMore(binding, _wrap_token(None, rule_elem))
            if suffix == "*":
                return ZeroOrMore(binding, _wrap_token(None, rule_elem))
            if suffix == "?":
                return ZeroOrOne(binding, _wrap_token(None, rule_elem), brackets=False)

            raise AssertionError(f"Unknown suffix: {suffix}")
        # rule body in between square brackets
        elif remaining == 3:
            return ZeroOrOne(
                binding, _wrap_token(None, args[next_idx + 1]), brackets=True
            )

        raise AssertionError(f"Invalid rule length {rule_len}")
