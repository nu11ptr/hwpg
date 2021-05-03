from dataclasses import dataclass
from typing import List

from .parser import JsonParser, ParserNode
from .tokens import TokenType


@dataclass
class Token:
    data: str
    token_type: TokenType


class Tokenizer:
    def __init__(self, tokens: List[Token]):
        self._tokens = tokens
        self._idx = 0

    def next_token(self) -> Token:
        if self._idx >= len(self._tokens):
            return Token("", TokenType.EOF)
        tok = self._tokens[self._idx]
        self._idx += 1
        return tok


def test_parse_empty_json():
    lexer = Tokenizer([])
    parser = JsonParser(lexer)
    tree = parser.parse_value()

    assert not tree, "Tree was not empty"


def test_parse_json_string():
    string = Token("test", TokenType.STRING)
    lexer = Tokenizer([string])
    parser = JsonParser(lexer)
    tree = parser.parse_value()

    assert tree == string, "Not a string"


def test_parse_json_dict():
    lbrace = Token("{", TokenType.LBRACE)

    key1 = Token("key1", TokenType.STRING)
    colon1 = Token(":", TokenType.COLON)
    lbracket = Token("[", TokenType.LBRACKET)
    number = Token("456", TokenType.NUMBER)
    comma1 = Token(",", TokenType.COMMA)
    true = Token("true", TokenType.TRUE)
    rbracket = Token("]", TokenType.RBRACKET)

    comma2 = Token(",", TokenType.COMMA)

    key2 = Token("key2", TokenType.STRING)
    colon2 = Token(":", TokenType.COLON)
    null = Token("null", TokenType.NULL)

    rbrace = Token("}", TokenType.RBRACE)

    tokens = [
        lbrace,
        key1,
        colon1,
        lbracket,
        number,
        comma1,
        true,
        rbracket,
        comma2,
        key2,
        colon2,
        null,
        rbrace,
    ]
    lexer = Tokenizer(tokens)
    parser = JsonParser(lexer)
    actual = parser.parse_value()
    expected = ParserNode(
        nodes=[
            lbrace,
            ParserNode(
                nodes=[
                    ParserNode(
                        nodes=[
                            key1,
                            colon1,
                            ParserNode(
                                nodes=[
                                    lbracket,
                                    ParserNode(
                                        nodes=[number, ParserNode(nodes=[comma1, true])]
                                    ),
                                    rbracket,
                                ]
                            ),
                        ]
                    ),
                    ParserNode(nodes=[comma2, ParserNode(nodes=[key2, colon2, null])]),
                ]
            ),
            rbrace,
        ]
    )

    assert actual == expected, "Not a dict"
