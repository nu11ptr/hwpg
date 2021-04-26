import sys

from lark import Lark

from mlpg.ast import ToAST
from mlpg.parsergen import ParserGen
from runtime.python.emitter import PyCodeEmitter, PyParseTreeMaker

_PARSER = "mlpg.lark"


def _create_parser() -> Lark:
    with open(_PARSER, "r") as f:
        parser = Lark(f, start="grammar", debug=True, parser="lalr")

    return parser


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mlpg.py <grammar.mlpg>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        src = f.read()

    parser = _create_parser()

    # NOTE: We don't need the parse tree, but passing current transformer
    # directly into parser yields an exception - no big deal, keep as is for now
    tree = parser.parse(src)
    print("Parse Tree: ", tree)

    grammar = ToAST().transform(tree)
    print("AST: ", grammar)

    emitter = PyCodeEmitter(PyParseTreeMaker(), memoize=True)
    parser_str, debug = ParserGen(emitter).generate("TODO", grammar)

    # print(debug)
    print(parser_str)
