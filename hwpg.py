import os
import sys
from typing import List, Tuple

import click
from lark import Lark, Tree

from hwpg.ast import Grammar, ToAST
from hwpg.config import Config, Lang, load, OutputType
from hwpg.lexergen import TokensGen
from hwpg.parsergen import ParserGen
from hwpg.process import Process
from hwpg.runtime.python.parser_codegen import PyParserCodeGen, PyParseTreeMaker
from hwpg.runtime.python.lexer_codegen import PyTokensCodeGen

_PARSER = "hwpg.lark"


def _parse_grammar(filename: str) -> Tree:
    # Read our grammar
    with open(_PARSER, "r") as f:
        parser = Lark(f, start="grammar", debug=True, parser="lalr")

    # Read and parse the user's grammar
    with open(filename, "r") as f:
        src = f.read()

    return parser.parse(src)


def _gen_parser(grammar: Grammar, name: str, cfg: Config) -> Tuple[str, str]:
    if cfg.lang == Lang.PYTHON:
        emitter = PyParserCodeGen(name, PyParseTreeMaker(), cfg.memoize)
    else:
        raise AssertionError(f"Unknown or unsupported language: {cfg.lang}")

    parser_str, _ = ParserGen(emitter).generate(grammar)
    return parser_str, emitter.parser_filename()


def _gen_tokens(token_names: List[str], cfg: Config) -> Tuple[str, str]:
    if cfg.lang == Lang.PYTHON:
        codegen = PyTokensCodeGen()
    else:
        raise AssertionError(f"Unknown or unsupported language: {cfg.lang}")

    return TokensGen(codegen).generate(token_names)


def _save_output(code: str, path: str, filename: str):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

    # Save parser
    output_file = os.path.join(path, filename)
    with open(output_file, "w") as f:
        f.write(code)


@click.command()
@click.argument(
    "filename", metavar="<grammar.hwpg>", type=click.Path(exists=True, readable=True)
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, readable=True),
    default=None,
    show_default=True,
    help="Optional python configuration file specifying overrides to the default configuration",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=True),
    help="The output directory in which to write the generated files. It defaults to "
    "a folder with the same base name as your grammer (located in the same folder "
    "as your grammar)",
)
def hwpg(filename: str, config: str, output: str):
    """
    "hand written" parser generator - generate parsers that look like they were
    written by hand
    """

    # First, load our configuration (either defaults or user supplied)
    cfg = load(config)

    if cfg.lang == Lang.GO:
        print("'Go' is not yet supported.")
        sys.exit(1)
    elif cfg.lang != Lang.PYTHON:
        print(f"Unsupported language: {cfg.lang}")
        sys.exit(1)

    if cfg.output_type != OutputType.PARSER:
        print("Only 'parser' generation is currently supported.")
        sys.exit(1)

    # NOTE: We don't need the parse tree, but passing current transformer
    # directly into parser yields an exception - no big deal, keep as is for now
    # Parse the user's grammar
    tree = _parse_grammar(filename)

    # Then convert the user's parse tree into an AST
    grammar = ToAST().transform(tree)

    # Do post processing optimizing the AST and looking for errors
    processor = Process(grammar)
    new_grammar, token_names, errors = processor.process()
    if errors:
        err = "\n".join(errors)
        print(f"Errors:\n{err}")
        sys.exit(1)

    # Find the base name from the given grammar filename
    name, _ = os.path.splitext(os.path.basename(filename))
    # If no output path specified, create new folder in the directory of our grammar
    # with the same name
    if not output:
        output = os.path.dirname(filename)
        output = os.path.join(output, name)

    # Special Python consideration, create __init__.py to make this a new package
    if cfg.lang == Lang.PYTHON:
        _save_output("", output, "__init__.py")

    # Create tokens
    tokens, tokens_file = _gen_tokens(token_names, cfg)
    _save_output(tokens, output, tokens_file)

    # Create Lexer, if needed
    if cfg.output_type == OutputType.BOTH or cfg.output_type == OutputType.LEXER:
        # TODO: Generate lexer here
        pass

    # Create parser, if needed
    if cfg.output_type == OutputType.BOTH or cfg.output_type == OutputType.PARSER:
        # Generate code for the parser
        parser, parser_file = _gen_parser(new_grammar, name, cfg)
        _save_output(parser, output, parser_file)


if __name__ == "__main__":
    hwpg()  # pylint: disable=no-value-for-parameter
