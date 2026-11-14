import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class GenericNativeListTests(unittest.TestCase):
    def compile_and_run(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        c_source = CCompiler().compile(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(c_source)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            return subprocess.run([binary_path], check=True, capture_output=True, text=True).stdout

    def test_native_float_list_iteration(self):
        output = self.compile_and_run("let values = [1.5, 2.5] for value in values { println(value) }")
        self.assertEqual(output, "1.5\n2.5\n")

    def test_native_string_list_iteration(self):
        output = self.compile_and_run('let values = ["a", "b"] for value in values { println(value) }')
        self.assertEqual(output, "a\nb\n")


if __name__ == "__main__":
    unittest.main()
