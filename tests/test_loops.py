import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class LoopTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def test_interpreter_iterates_lists(self):
        program = self.parse("let values = [1, 2, 3] for value in values { println(value) }")
        TypeChecker().check(program)
        output = []
        from rplus.interpreter import Interpreter
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [1, 2, 3])

    def test_native_backend_compiles_list_iteration(self):
        source = "let values = [1, 2, 3] for value in values { println(value) }"
        program = self.parse(source)
        TypeChecker().check(program)
        c_source = CCompiler().compile(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(c_source)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, "1\n2\n3\n")


if __name__ == "__main__":
    unittest.main()
