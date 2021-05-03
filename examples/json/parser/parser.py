from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .tokens import Token, TokenType, Tokenizer, TreeNode


@dataclass
class ParserNode:
    nodes: List[Union[Optional[TreeNode], List[TreeNode]]]


class _Parser:
    """Parser base class containing helper functions"""

    def __init__(self, tokenizer: Tokenizer):
        self._tok = tokenizer
        self.pos = -1
        self._tokens: List[Token] = []
        self._next_token()

    def _curr_token(self) -> Token:
        return self._tokens[self.pos]

    def _next_token(self) -> Token:
        self.pos += 1

        if self.pos < len(self._tokens):
            return self._tokens[self.pos]

        tok = self._tok.next_token()
        self._tokens.append(tok)
        return tok

    def _match_token_or_rollback(self, tt: TokenType, old_pos: int) -> Optional[Token]:
        tok = self._curr_token()

        if tok.token_type != tt:
            self.pos = old_pos
            return None

        self._next_token()
        return tok

    def _match_tokens_or_rollback(self, tt: TokenType, old_pos: int) -> List[Token]:
        token = self._match_token_or_rollback(tt, old_pos)
        if not token:
            self.pos = old_pos
            return []

        tokens = self._try_match_tokens(tt)
        return [token, *tokens]

    def _try_match_token(self, tt: TokenType) -> Optional[Token]:
        tok = self._curr_token()

        if tok.token_type != tt:
            return None

        self._next_token()
        return tok

    def _try_match_tokens(self, tt: TokenType) -> List[Token]:
        tokens: List[Token] = []

        while True:
            tok = self._try_match_token(tt)
            if not tok:
                break
            tokens.append(tok)

        return tokens


def _memoize(func):
    def memoize_wrapper(self):
        pos = self.pos
        key = (func, pos)

        if key in self._memos:
            result, new_pos = self._memos[key]
            self.pos = new_pos
            return result

        result = func(self)
        key = (func, pos)
        self._memos[key] = result, self.pos
        return result

    return memoize_wrapper


class JsonParser(_Parser):
    """Primary parser class"""

    def __init__(self, tokenizer: Tokenizer):
        super().__init__(tokenizer)
        self._memos: Dict[Tuple[Callable, int], Any] = {}

    @_memoize
    def parse_value(self) -> Optional[TreeNode]:
        """
        value: dict | list | STRING | NUMBER | "true" | "false" | "null"
        """
        old_pos = self.pos

        # dict
        dict = self.parse_dict()
        if dict:
            return dict

        # list
        list = self.parse_list()
        if list:
            return list

        # STRING
        string = self._try_match_token(TokenType.STRING)
        if string:
            return string

        # NUMBER
        number = self._try_match_token(TokenType.NUMBER)
        if number:
            return number

        # "true"
        true = self._try_match_token(TokenType.TRUE)
        if true:
            return true

        # "false"
        false = self._try_match_token(TokenType.FALSE)
        if false:
            return false

        # "null"
        null = self._try_match_token(TokenType.NULL)
        if null:
            return null

        self.pos = old_pos
        return None

    @_memoize
    def _parse_list_sub2_depth2(self) -> Optional[TreeNode]:
        """
        "," value
        """
        old_pos = self.pos

        # ","
        comma = self._match_token_or_rollback(TokenType.COMMA, old_pos)
        if not comma:
            return None

        # value
        value = self.parse_value()
        if not value:
            self.pos = old_pos
            return None

        return ParserNode([comma, value])

    @_memoize
    def _parse_list_sub1_depth1(self) -> Optional[TreeNode]:
        """
        value ("," value)*
        """
        old_pos = self.pos

        # value
        value = self.parse_value()
        if not value:
            self.pos = old_pos
            return None

        # ("," value)*
        list_sub2_depth2_list: List[TreeNode] = []
        while True:
            list_sub2_depth2 = self._parse_list_sub2_depth2()
            if not list_sub2_depth2:
                break
            list_sub2_depth2_list.append(list_sub2_depth2)

        return ParserNode([value, *list_sub2_depth2_list])

    @_memoize
    def parse_list(self) -> Optional[TreeNode]:
        """
        list: "[" [value ("," value)*] "]"
        """
        old_pos = self.pos

        # "["
        lbracket = self._match_token_or_rollback(TokenType.LBRACKET, old_pos)
        if not lbracket:
            return None

        # [value ("," value)*]
        list_sub1_depth1 = self._parse_list_sub1_depth1()
        # "]"
        rbracket = self._match_token_or_rollback(TokenType.RBRACKET, old_pos)
        if not rbracket:
            return None

        return ParserNode([lbracket, list_sub1_depth1, rbracket])

    @_memoize
    def _parse_dict_sub2_depth2(self) -> Optional[TreeNode]:
        """
        "," pair
        """
        old_pos = self.pos

        # ","
        comma = self._match_token_or_rollback(TokenType.COMMA, old_pos)
        if not comma:
            return None

        # pair
        pair = self.parse_pair()
        if not pair:
            self.pos = old_pos
            return None

        return ParserNode([comma, pair])

    @_memoize
    def _parse_dict_sub1_depth1(self) -> Optional[TreeNode]:
        """
        pair ("," pair)*
        """
        old_pos = self.pos

        # pair
        pair = self.parse_pair()
        if not pair:
            self.pos = old_pos
            return None

        # ("," pair)*
        dict_sub2_depth2_list: List[TreeNode] = []
        while True:
            dict_sub2_depth2 = self._parse_dict_sub2_depth2()
            if not dict_sub2_depth2:
                break
            dict_sub2_depth2_list.append(dict_sub2_depth2)

        return ParserNode([pair, *dict_sub2_depth2_list])

    @_memoize
    def parse_dict(self) -> Optional[TreeNode]:
        """
        dict: "{" [pair ("," pair)*] "}"
        """
        old_pos = self.pos

        # "{"
        lbrace = self._match_token_or_rollback(TokenType.LBRACE, old_pos)
        if not lbrace:
            return None

        # [pair ("," pair)*]
        dict_sub1_depth1 = self._parse_dict_sub1_depth1()
        # "}"
        rbrace = self._match_token_or_rollback(TokenType.RBRACE, old_pos)
        if not rbrace:
            return None

        return ParserNode([lbrace, dict_sub1_depth1, rbrace])

    @_memoize
    def parse_pair(self) -> Optional[TreeNode]:
        """
        pair: STRING ":" value
        """
        old_pos = self.pos

        # STRING
        string = self._match_token_or_rollback(TokenType.STRING, old_pos)
        if not string:
            return None

        # ":"
        colon = self._match_token_or_rollback(TokenType.COLON, old_pos)
        if not colon:
            return None

        # value
        value = self.parse_value()
        if not value:
            self.pos = old_pos
            return None

        return ParserNode([string, colon, value])
