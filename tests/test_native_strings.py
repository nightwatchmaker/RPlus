import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class NativeStringTests(unittest.TestCase):
    def test_native_string_declaration_and_print(self):
        program = Parser(Lexer('let greeting = "hello R+" println(greeting)').tokenize()).parse()
        TypeChecker().check(program)
        c_source = CCompiler().compile(program)

        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(c_source)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], check=True, capture_output=True, text=True)

        self.assertEqual(result.stdout, "hello R+\n")


if __name__ == "__main__":
    unittest.main()
