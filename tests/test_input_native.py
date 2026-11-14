import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class InputNativeTests(unittest.TestCase):
    def test_input_compiles_and_reads_a_line(self):
        program = Parser(Lexer('println(input("Name: "))').tokenize()).parse()
        TypeChecker().check(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(CCompiler().compile(program))
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], input="Ada\n", capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "Name: Ada\n")


if __name__ == "__main__":
    unittest.main()
