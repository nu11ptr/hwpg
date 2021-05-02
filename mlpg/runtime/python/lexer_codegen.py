from mlpg.lexergen import Jinja2TokensCodeGen


class PyTokensCodeGen(Jinja2TokensCodeGen):
    def __init__(self):
        super().__init__("templates/python", "tokens.py.j2")

    @property
    def tokens_filename(self) -> str:
        return "tokens.py"
