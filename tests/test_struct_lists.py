import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class StructListTests(unittest.TestCase):
    def test_native_struct_list_iteration(self):
        source = '''
struct Point { x: Int }
let points = [Point { x: 1 }, Point { x: 2 }]
for point in points { println(point.x) }
'''
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        c_source = CCompiler().compile(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(c_source)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, "1\n2\n")


if __name__ == "__main__":
    unittest.main()
