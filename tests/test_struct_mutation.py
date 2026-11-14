import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.interpreter import Interpreter
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker, TypeErrorRPlus


class StructMutationTests(unittest.TestCase):
    source = '''
struct Counter { value: Int }
mut counter = Counter { value: 1 }
counter.value = counter.value + 4
println(counter.value)
'''

    def test_interpreter_updates_mutable_struct_field(self):
        program = Parser(Lexer(self.source).tokenize()).parse()
        TypeChecker().check(program)
        output = []
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [5])

    def test_immutable_struct_rejects_field_mutation(self):
        source = "struct Counter { value: Int } let counter = Counter { value: 1 } counter.value = 2"
        program = Parser(Lexer(source).tokenize()).parse()
        with self.assertRaisesRegex(TypeErrorRPlus, "Cannot mutate field on immutable variable 'counter'"):
            TypeChecker().check(program)

    def test_native_backend_updates_mutable_struct_field(self):
        program = Parser(Lexer(self.source).tokenize()).parse()
        TypeChecker().check(program)
        c_source = CCompiler().compile(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(c_source)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, "5\n")


if __name__ == "__main__":
    unittest.main()
