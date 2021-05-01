from typing import Dict, List, Optional, Tuple

from lark.lexer import Token

from mlpg.ast import (
    Alternatives,
    Grammar,
    MultipartBody,
    Node,
    NodeContainer,
    OneOrMore,
    Rule,
    RuleRef,
    TokenLit,
    TokenRef,
    TokenRule,
    ZeroOrMore,
    ZeroOrOne,
)


class Process:
    def __init__(self, grammar: Grammar):
        self._grammar = grammar

        self._literals: Dict[str, Tuple[Token, Optional[TokenRef]]] = {}
        self._errors: List[str] = []

    def _log_error(self, msg: str):
        self._errors.append(f"ERROR: {msg}")

    def process(self) -> Tuple[Grammar, List[str]]:
        # Process tokens first to ensure all literals are there by time parser
        # tree processing starts
        token_rules = [
            self._process_token_rule(rule) for rule in self._grammar.token_rules
        ]
        rules = [self._process_rule(rule) for rule in self._grammar.rules]
        return Grammar(rules, token_rules), self._errors

    def _process_token_rule(self, rule: TokenRule) -> TokenRule:
        # TODO: Adapt this as TokenRule evolves
        # Add to dict so we can validate against literals in our grammar
        self._literals[rule.literal.literal.value] = rule.name, None
        return rule

    def _process_rule(self, rule: Rule) -> Rule:
        body = self._process_node(rule.node)
        if body is rule.node:
            return rule

        return Rule(rule.name, body)

    def _process_node(self, node: Node, parent: Optional[NodeContainer] = None) -> Node:
        type_ = type(node)

        if type_ is Alternatives:
            return self._process_alternatives(node, parent)  # type: ignore
        elif type_ is MultipartBody:
            return self._process_multipart_body(node, parent)  # type: ignore
        elif type_ is ZeroOrMore:
            return self._process_zero_or_more(node, parent)  # type: ignore
        elif type_ is OneOrMore:
            return self._process_one_or_more(node, parent)  # type: ignore
        elif type_ is ZeroOrOne:
            return self._process_zero_or_one(node, parent)  # type: ignore
        elif type_ is RuleRef:
            return self._process_rule_ref(node, parent)  # type: ignore
        elif type_ is TokenRef:
            return self._process_token_ref(node, parent)  # type: ignore
        elif type_ is TokenLit:
            return self._process_token_lit(node, parent)  # type: ignore
        else:
            raise AssertionError(f"Unknown node type: {type_}")

    def _process_alternatives(
        self, alts: Alternatives, parent: Optional[NodeContainer]
    ) -> Alternatives:
        changed = False
        new_alts: List[Node] = []

        for alt in alts.nodes:
            new_alt = self._process_node(alt, parent=alts)
            if new_alt is not alt:
                changed = True
            new_alts.append(new_alt)

        if not changed:
            return alts

        return Alternatives(new_alts)

    def _process_multipart_body(
        self, body: MultipartBody, parent: Optional[NodeContainer]
    ) -> MultipartBody:
        changed = False
        new_parts: List[Node] = []

        for part in body.nodes:
            new_part = self._process_node(part, parent=body)
            if new_part is not part:
                changed = True
            new_parts.append(new_part)

        if not changed:
            return body

        return MultipartBody(new_parts)

    def _process_zero_or_more(
        self, zom: ZeroOrMore, parent: Optional[NodeContainer]
    ) -> ZeroOrMore:
        node = self._process_node(zom.node, parent=zom)
        if node is zom.node:
            return zom

        return ZeroOrMore(node)

    def _process_one_or_more(
        self, oom: OneOrMore, parent: Optional[NodeContainer]
    ) -> OneOrMore:
        node = self._process_node(oom.node, parent=oom)
        if node is oom.node:
            return oom

        return OneOrMore(node)

    def _process_zero_or_one(
        self, zoo: ZeroOrOne, parent: Optional[NodeContainer]
    ) -> ZeroOrOne:
        node = self._process_node(zoo.node, parent=zoo)
        if node is zoo.node:
            return zoo

        return ZeroOrOne(node, zoo.brackets)

    def _process_rule_ref(
        self, ref: RuleRef, parent: Optional[NodeContainer]
    ) -> RuleRef:
        return ref

    def _process_token_ref(
        self, ref: TokenRef, parent: Optional[NodeContainer]
    ) -> TokenRef:
        return ref

    def _process_token_lit(
        self, lit: TokenLit, parent: Optional[NodeContainer]
    ) -> Node:
        tup = self._literals.get(lit.literal)
        if not tup:
            self._log_error(
                f"Literal {lit.literal} does not have corresponding token rule"
            )
            return lit

        name, ref = tup
        # If TokenRef not already created, do so and store for future
        if not ref:
            ref = TokenRef(name, lit.literal)
            self._literals[lit.literal] = name, ref

        return ref
