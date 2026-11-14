import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class DynamicListRuntimeTests(unittest.TestCase):
    def test_native_lists_use_owned_heap_storage(self):
        source = "let values = [1, 2, 3] for value in values { println(value) }"
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        c_source = CCompiler().compile(program)

        self.assertIn("typedef struct {", c_source)
        self.assertIn("malloc", c_source)
        self.assertIn("values.data", c_source)
        self.assertIn("free(values.data);", c_source)

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
