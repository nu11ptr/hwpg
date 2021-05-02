from hwpg.lexergen import Jinja2TokensCodeGen


class PyTokensCodeGen(Jinja2TokensCodeGen):
    def __init__(self, make_parse_tree: bool):
        super().__init__(make_parse_tree, "templates/python", "tokens.py.j2")

    @property
    def tokens_filename(self) -> str:
        return "tokens.py"
