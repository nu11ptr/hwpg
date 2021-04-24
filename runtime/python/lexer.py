from abc import ABC, abstractmethod
from enum import IntEnum


class TokenType(IntEnum):
    pass


class Token(ABC):
    @abstractmethod
    def token_type(self) -> TokenType:
        pass


class Tokenizer(ABC):
    @abstractmethod
    def next_token(self) -> Token:
        pass
