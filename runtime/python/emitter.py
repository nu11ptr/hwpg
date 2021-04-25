from mlpg.parsergen import TreeMaker


class PyCodeEmitter:
    def __init__(self, tree_maker: TreeMaker):
        self._tree_maker = tree_maker

    def start(self, name: str) -> str:
        return f"class {name}:\n"

    def end(self, name: str) -> str:
        return "#end class\n"

    def make_func_name(self, name: str, sub: int = 0, depth: int = 0) -> str:
        return f"_{name}_sub{sub}_depth{depth}" if sub > 0 else name

    def start_rule(self, name: str) -> str:
        ret_type = self._tree_maker.return_type(name)
        return f"    def {name}(self) -> {ret_type}:\n"

    def end_rule(self, name: str) -> str:
        return "#   end_rule\n"

    def match_token(self, name: str, ret: bool) -> str:
        return f"        match_token(name={name}, ret={ret})\n"

    def match_token_zero_or_one(self, name: str, ret: bool) -> str:
        return f"        match_token_zero_or_one(name={name}, ret={ret})\n"

    def match_token_zero_or_more(self, name: str, ret: bool) -> str:
        return f"        match_token_zero_or_more(name={name}, ret={ret})\n"

    def match_token_one_or_more(self, name: str, ret: bool) -> str:
        return f"        match_token_one_or_more(name={name}, ret={ret})\n"

    def match_rule(self, name: str, ret: bool) -> str:
        return f"        match_rule(name={name}, ret={ret})\n"

    def match_rule_zero_or_one(self, name: str, ret: bool) -> str:
        return f"        match_rule_zero_or_one(name={name}, ret={ret})\n"

    def match_rule_zero_or_more(self, name: str, ret: bool) -> str:
        return f"        match_rule_zero_or_more(name={name}, ret={ret})\n"

    def match_rule_one_or_more(self, name: str, ret: bool) -> str:
        return f"        match_rule_one_or_more(name={name}, ret={ret})\n"


class Tree:
    pass


class PyParseTreeMaker:
    def return_type(self, name: str) -> str:
        return "Tree"
