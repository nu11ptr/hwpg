from typing import List, Optional

from .lexer import Token, TokenType, Tokenizer


class Parser:
    def __init__(self, tokenizer: Tokenizer):
        self._tok = tokenizer
        self.pos = -1
        self._tokens: List[Token] = []

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

        if tok.token_type() != tt:
            self.pos = old_pos
            return None

        self._next_token()
        return tok

    def _try_match_token(self, tt: TokenType) -> Optional[Token]:
        tok = self._curr_token()

        if tok.token_type() != tt:
            return None

        self._next_token()
        return tok