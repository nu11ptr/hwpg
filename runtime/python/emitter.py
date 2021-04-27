from mlpg.parsergen import BaseFuncEmitter, FuncEmitter, Jinja2CodeEmitter, TreeMaker


class PyFuncEmitter(BaseFuncEmitter):
    def __init__(self, name: str, ret_type: str):
        super().__init__(name, ret_type)
        self._func_parts.append(f"    def {name}(self) -> {ret_type}:\n")

    def match_token(self, name: str, ret: bool):
        self._func_parts.append(f"        match_token(name={name}, ret={ret})\n")

    def match_token_zero_or_one(self, name: str, ret: bool):
        self._func_parts.append(
            f"        match_token_zero_or_one(name={name}, ret={ret})\n"
        )

    def match_token_zero_or_more(self, name: str, ret: bool):
        self._func_parts.append(
            f"        match_token_zero_or_more(name={name}, ret={ret})\n"
        )

    def match_token_one_or_more(self, name: str, ret: bool):
        self._func_parts.append(
            f"        match_token_one_or_more(name={name}, ret={ret})\n"
        )

    def match_rule(self, name: str, ret: bool):
        self._func_parts.append(f"        match_rule(name={name}, ret={ret})\n")

    def match_rule_zero_or_one(self, name: str, ret: bool):
        self._func_parts.append(
            f"        match_rule_zero_or_one(name={name}, ret={ret})\n"
        )

    def match_rule_zero_or_more(self, name: str, ret: bool):
        self._func_parts.append(
            f"        match_rule_zero_or_more(name={name}, ret={ret})\n"
        )

    def match_rule_one_or_more(self, name: str, ret: bool):
        self._func_parts.append(
            f"        match_rule_one_or_more(name={name}, ret={ret})\n"
        )


class PyCodeEmitter(Jinja2CodeEmitter):
    def __init__(self, tree_maker: TreeMaker, memoize: bool = True):
        super().__init__("templates/python", "parser.py.j2")
        self._tree_maker = tree_maker
        self._vars["memoize"] = memoize

    @staticmethod
    def make_func_name(name: str, sub: int = 0, depth: int = 0) -> str:
        return f"_parse_{name}_sub{sub}_depth{depth}" if sub > 0 else f"parse_{name}"

    def start_rule(self, name: str) -> FuncEmitter:
        ret_type = self._tree_maker.return_type(name)
        return PyFuncEmitter(name, ret_type)

    def end_rule(self, emitter: FuncEmitter):
        self._funcs.append(emitter.emit())


class Tree:
    pass


class PyParseTreeMaker:
    def return_type(self, name: str) -> str:
        return "Tree"
