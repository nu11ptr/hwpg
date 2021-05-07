from typing import Dict, List, Optional, Tuple

from lark.lexer import Token

from hwpg.ast import (
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

_EOF = "EOF"
_ILLEGAL = "ILLEGAL"


class Process:
    def __init__(self, grammar: Grammar):
        self._grammar = grammar

        # A set would be better, but I want to keep ordering as much as possible
        self._token_names: List[str] = []
        self._literals: Dict[str, Tuple[Token, Optional[TokenRef]]] = {}
        self._errors: List[str] = []

    def _log_error(self, msg: str):
        self._errors.append(f"ERROR: {msg}")

    def process(self) -> Tuple[Grammar, List[str], List[str]]:
        # Process tokens first to ensure all literals are there by time parser
        # tree processing starts
        token_rules = [
            self._process_token_rule(rule) for rule in self._grammar.token_rules
        ]
        rules = [self._process_rule(rule) for rule in self._grammar.rules]

        # Ensure these special tokens are always in the list
        if _EOF not in self._token_names:
            self._token_names.append(_EOF)

        if _ILLEGAL not in self._token_names:
            self._token_names.append(_ILLEGAL)

        return Grammar(rules, token_rules), self._token_names, self._errors

    def _process_token_rule(self, rule: TokenRule) -> TokenRule:
        # TODO: Adapt this as TokenRule evolves
        # Add to dict so we can validate against literals in our grammar
        # Strip quotes - either ' or " before compare
        lit_str = rule.literal.literal.value[1:-1]
        self._literals[lit_str] = rule.name, None

        # Add names to master token name list
        self._token_names.append(rule.name.value)
        return rule

    def _process_rule(self, rule: Rule) -> Rule:
        body = self._process_node(rule.node)
        if body is rule.node:
            return rule

        return Rule(rule.name, body)

    def _process_node(self, node: Node, parent: Optional[NodeContainer] = None) -> Node:
        # Top level bindings don't work right now (and I can't think what good
        # they do? Just change the rule name....), so disallow them
        if not parent and node.binding:
            self._log_error(f"Top level binding '{node.binding.value}' is not allowed")

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

        return Alternatives(alts.binding, new_alts)

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

        return MultipartBody(body.binding, new_parts)

    def _process_zero_or_more(
        self, zom: ZeroOrMore, parent: Optional[NodeContainer]
    ) -> ZeroOrMore:
        node = self._process_node(zom.node, parent=zom)
        if node is zom.node:
            return zom

        return ZeroOrMore(zom.binding, node)

    def _process_one_or_more(
        self, oom: OneOrMore, parent: Optional[NodeContainer]
    ) -> OneOrMore:
        node = self._process_node(oom.node, parent=oom)
        if node is oom.node:
            return oom

        return OneOrMore(oom.binding, node)

    def _process_zero_or_one(
        self, zoo: ZeroOrOne, parent: Optional[NodeContainer]
    ) -> ZeroOrOne:
        node = self._process_node(zoo.node, parent=zoo)
        if node is zoo.node:
            return zoo

        return ZeroOrOne(zoo.binding, node, zoo.brackets)

    def _process_rule_ref(
        self, ref: RuleRef, parent: Optional[NodeContainer]
    ) -> RuleRef:
        return ref

    def _process_token_ref(
        self, ref: TokenRef, parent: Optional[NodeContainer]
    ) -> TokenRef:
        # Add to our master token name list if first time seen
        token_name = ref.name.value
        if token_name not in self._token_names:
            self._token_names.append(token_name)

        return ref

    def _process_token_lit(
        self, lit: TokenLit, parent: Optional[NodeContainer]
    ) -> Node:
        # Strip quotes - either ' or " before compare
        lit_str = lit.literal[1:-1]
        tup = self._literals.get(lit_str)
        if not tup:
            self._log_error(
                f"Literal {lit.literal} does not have corresponding token rule"
            )
            return lit

        name, ref = tup
        # If TokenRef not already created, do so and store for future
        if not ref:
            ref = TokenRef(lit.binding, name, lit.literal)
            self._literals[lit_str] = name, ref

        return ref
