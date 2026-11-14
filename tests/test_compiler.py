import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class CompilerTests(unittest.TestCase):
    def compile_program(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        return CCompiler().compile(program)

    def test_emits_native_c_for_integer_program(self):
        c_source = self.compile_program("let answer: Int = 40 + 2 println(answer)")

        self.assertIn("int answer = (40 + 2);", c_source)
        self.assertIn("printf(\"%lld\\n\", (long long)(answer));", c_source)

    def test_generated_c_compiles_and_runs(self):
        c_source = self.compile_program("fn add(a: Int, b: Int) -> Int { return a + b } println(add(20, 22))")
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(c_source)
            subprocess.run(["clang", "-std=c11", "-O2", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, "42\n")


if __name__ == "__main__":
    unittest.main()
