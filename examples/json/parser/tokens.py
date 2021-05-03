from enum import auto, IntEnum
from typing import List, Optional, Protocol, Union


class TokenType(IntEnum):
    """
    All token types as found in the grammar
    """

    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    STRING = auto()
    NUMBER = auto()
    EOF = auto()
    ILLEGAL = auto()


class TreeNode(Protocol):
    """
    Represents a single node in the parse tree. It is implemented by 'Token'
    as well as any objects emitted by non-terminal parser rules.
    """

    nodes: List[Union[Optional["TreeNode"], List["TreeNode"]]]


class Token(TreeNode):

    """
    Represents a single token emitted by the lexer and consumed by the parser
    """

    token_type: TokenType


class Tokenizer(Protocol):
    """
    The interface required of the lexer that is consumed by the parser
    """

    def next_token(self) -> Token:
        ...
