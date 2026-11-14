"""Command-line entry point: python -m rplus program.rp"""

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import fields, is_dataclass
from pathlib import Path

from .ast import Call, FunctionDeclaration, GetExpression, ImportDeclaration, Program, Variable
from .compiler import CCompiler
from .interpreter import Interpreter, RuntimeErrorRPlus
from .lexer import Lexer, LexerError
from .ownership import OwnershipChecker, OwnershipError
from .parser import ParseError, Parser
from .typechecker import TypeChecker, TypeErrorRPlus


def _rewrite_addon_calls(node, local_functions, modules):
    if isinstance(node, Call):
        if isinstance(node.callee, GetExpression) and isinstance(node.callee.object, Variable):
            module = modules.get(node.callee.object.name, set())
            if node.callee.name in module:
                node.callee = Variable(f"{node.callee.object.name}__{node.callee.name}")
        elif isinstance(node.callee, Variable) and node.callee.name in local_functions:
            node.callee.name = local_functions[node.callee.name]
    if is_dataclass(node):
        for field in fields(node):
            value = getattr(node, field.name)
            if isinstance(value, list):
                for item in value:
                    _rewrite_addon_calls(item, local_functions, modules)
            else:
                _rewrite_addon_calls(value, local_functions, modules)
    return node


def _load_rplus_program(source_path, seen=None, namespace=None):
    seen = set() if seen is None else seen
    source_path = source_path.resolve()
    if source_path in seen:
        raise OSError(f"Circular or duplicate R+ import: {source_path}")
    seen.add(source_path)
    text = source_path.read_text(encoding="utf-8")
    program = Parser(Lexer(text).tokenize()).parse()
    statements = []
    local_statements = []
    modules = {}
    for statement in program.statements:
        if isinstance(statement, ImportDeclaration):
            imported_path = (source_path.parent / statement.path)
            if imported_path.suffix != ".rpa":
                imported_path = imported_path.with_suffix(".rpa")
            child_namespace = re.sub(r"[^A-Za-z0-9_]", "_", imported_path.stem)
            child_statements, child_exports, child_modules = _load_rplus_program(imported_path, seen, child_namespace)
            statements.extend(child_statements)
            modules[child_namespace] = child_exports
            modules.update(child_modules)
        else:
            statements.append(statement)
            local_statements.append(statement)
    local_map = {}
    if namespace:
        for statement in local_statements:
            if isinstance(statement, FunctionDeclaration):
                local_map[statement.name] = f"{namespace}__{statement.name}"
        for statement in local_statements:
            if isinstance(statement, FunctionDeclaration):
                statement.name = local_map[statement.name]
    for statement in local_statements:
        _rewrite_addon_calls(statement, local_map, modules)
    exports = {name.split("__", 1)[-1] for name in local_map}
    return statements, exports, modules


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rplus", description="The R+ programming language")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("file", nargs="?", help="R+ source file")
    source.add_argument("-e", "--eval", dest="snippet", help="evaluate an R+ snippet")
    parser.add_argument("--check", action="store_true", help="type-check without running")
    parser.add_argument("--native", metavar="OUTPUT", help="compile to a native executable with clang")
    args = parser.parse_args(argv)

    try:
        if args.snippet is not None:
            program = Parser(Lexer(args.snippet).tokenize()).parse()
        else:
            program = Program(_load_rplus_program(Path(args.file))[0])
        TypeChecker().check(program)
        OwnershipChecker().check(program)
        if args.native:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".c", encoding="utf-8") as c_file:
                c_file.write(CCompiler().compile(program))
                c_file.flush()
                subprocess.run(
                    ["clang", "-std=c11", "-O2", c_file.name, "-o", args.native],
                    check=True,
                )
        elif not args.check:
            Interpreter().execute(program)
    except (OSError, subprocess.CalledProcessError, LexerError, ParseError, RuntimeErrorRPlus, TypeErrorRPlus, OwnershipError) as error:
        print(f"rplus: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
