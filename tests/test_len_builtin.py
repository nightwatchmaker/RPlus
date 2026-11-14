import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.interpreter import Interpreter
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class LenBuiltinTests(unittest.TestCase):
    source = 'let values = [10, 20, 30] println(len(values)) println(len("abcd"))'

    def test_interpreter(self):
        program = Parser(Lexer(self.source).tokenize()).parse()
        TypeChecker().check(program)
        output = []
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [3, 4])

    def test_native(self):
        program = Parser(Lexer(self.source).tokenize()).parse()
        TypeChecker().check(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(CCompiler().compile(program))
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "3\n4\n")


if __name__ == "__main__":
    unittest.main()
