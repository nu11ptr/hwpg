from typing import Dict, List, Optional, Tuple

from mlpg.ast import (
    Grammar,
    Node,
    NodeContainer,
    OneOrMore,
    Rule,
    RuleBody,
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

        self._literals: Dict[str, Tuple[str, Optional[TokenRef]]] = {}
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
        self._literals[rule.literal] = rule.name, None
        return rule

    def _process_rule(self, rule: Rule) -> Rule:
        body = self._process_rule_body(rule.rules)
        if body is rule.rules:
            return rule

        return Rule(rule.name, body)

    def _process_node(self, node: Node, parent: NodeContainer) -> Node:
        type_ = type(node)

        if type_ is RuleBody:
            return self._process_rule_body(node, parent)  # type: ignore
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

        return node

    def _process_rule_body(
        self, body: RuleBody, parent: Optional[NodeContainer] = None
    ) -> RuleBody:
        alts = body.rules  # type: ignore

        # If only 1 alternative and 1 part we don't need the RuleBody
        # so optimize it away
        # TODO: Make sure this is safe without parent before enabling
        if len(alts) == 1 and len(alts[0]) == 1 and parent is not None:
            return self._process_node(alts[0][0], parent=body)  # type: ignore

        new_alts: List[List[Node]] = []

        for alt in alts:
            nodes = [self._process_node(node, parent=body) for node in alt]
            new_alts.append(nodes)

        return RuleBody(new_alts)

    def _process_zero_or_more(
        self, zom: ZeroOrMore, parent: NodeContainer
    ) -> ZeroOrMore:
        node = self._process_node(zom.node, parent=zom)
        if node is zom.node:
            return zom

        return ZeroOrMore(node)

    def _process_one_or_more(self, oom: OneOrMore, parent: NodeContainer) -> OneOrMore:
        node = self._process_node(oom.node, parent=oom)
        if node is oom.node:
            return oom

        return OneOrMore(node)

    def _process_zero_or_one(self, zoo: ZeroOrOne, parent: NodeContainer) -> ZeroOrOne:
        node = self._process_node(zoo.node, parent=zoo)
        if node is zoo.node:
            return zoo

        return ZeroOrOne(node)

    def _process_rule_ref(self, ref: RuleRef, parent: NodeContainer) -> RuleRef:
        return ref

    def _process_token_ref(self, ref: TokenRef, parent: NodeContainer) -> TokenRef:
        return ref

    def _process_token_lit(self, lit: TokenLit, parent: NodeContainer) -> Node:
        tup = self._literals.get(lit.literal)
        if not tup:
            self._log_error(
                f"Literal {lit.literal} does not have corresponding token rule"
            )
            return lit

        name, ref = tup
        # If TokenRef not already created, do so and store for future
        if not ref:
            ref = TokenRef(name)
            self._literals[lit.literal] = name, ref

        return ref
