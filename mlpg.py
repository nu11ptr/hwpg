from enum import Enum
import os
import sys
from typing import Tuple

import click
from lark import Lark, Tree

from mlpg.ast import Grammar, ToAST
from mlpg.parsergen import ParserGen
from mlpg.process import Process
from mlpg.runtime.python.emitter import PyCodeEmitter, PyParseTreeMaker

_PARSER = "mlpg.lark"


class Lang(str, Enum):
    PYTHON = "python"
    GO = "go"


def _parse_grammar(filename: str) -> Tree:
    # Read our grammar
    with open(_PARSER, "r") as f:
        parser = Lark(f, start="grammar", debug=True, parser="lalr")

    # Read and parse the user's grammar
    with open(filename, "r") as f:
        src = f.read()

    return parser.parse(src)


def _gen_parser(
    grammar: Grammar, lang: Lang, name: str, memoize: bool
) -> Tuple[str, str]:
    if lang == Lang.PYTHON:
        emitter = PyCodeEmitter(name, PyParseTreeMaker(), memoize)
    else:
        raise AssertionError(f"Unknown or unsupported language: {lang}")

    parser_str, _ = ParserGen(emitter).generate(grammar)
    return parser_str, emitter.parser_filename()


def _save_parser(parser: str, output: str, filename: str):

    try:
        os.mkdir(output)
    except FileExistsError:
        pass

    # Save parser
    output_file = os.path.join(output, filename)
    with open(output_file, "w") as f:
        f.write(parser)


@click.command()
@click.argument(
    "filename", metavar="<grammar.hwpg>", type=click.Path(exists=True, readable=True)
)
@click.option(
    "--lang",
    "-l",
    type=click.Choice([Lang.PYTHON, Lang.GO]),
    default=Lang.PYTHON,
    show_default=True,
    help="Language in which to generate the parser",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=True),
    help="The output directory in which to write the generated files. It defaults to "
    "using a folder in the current working directory with the base name of the grammar.",
)
@click.option(
    "--memoize",
    "-m",
    type=bool,
    default=True,
    show_default=True,
    help="Speed up the generated parser by memoizing parsing function calls.",
)
def hwpg(filename: str, lang: Lang, output: str, memoize: bool):
    """
    "hand written" parser generator - generate parsers that look like they were
    written by hand
    """

    if lang == Lang.GO:
        print("'go' is not yet supported.")
        sys.exit(1)

    # NOTE: We don't need the parse tree, but passing current transformer
    # directly into parser yields an exception - no big deal, keep as is for now
    # Parse the user's grammar
    tree = _parse_grammar(filename)

    # Then convert the user's parse tree into an AST
    grammar = ToAST().transform(tree)

    # Do post processing optimizing the AST and looking for errors
    new_grammar, errors = Process(grammar).process()
    if errors:
        err = "\n".join(errors)
        print(f"Errors:\n{err}")
        sys.exit(1)

    # Find the base name from the given grammar filename
    name, _ = os.path.splitext(os.path.basename(filename))

    # Generate code for the parser
    parser, parser_file = _gen_parser(new_grammar, lang, name, memoize)

    if not output:
        output = name

    # Finally, save the parser to the filesystem
    _save_parser(parser, output, parser_file)


if __name__ == "__main__":
    hwpg()  # pylint: disable=no-value-for-parameter
