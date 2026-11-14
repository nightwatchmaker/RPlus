import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.interpreter import Interpreter
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


SOURCE = '''
struct Counter { value: Int }
impl Counter {
    fn add(self: &Counter, amount: Int) -> Int {
        return self.value + amount
    }
}
let counter = Counter { value: 3 }
println(counter.add(4))
'''


class ImmutableMethodTests(unittest.TestCase):
    def program(self):
        return Parser(Lexer(SOURCE).tokenize()).parse()

    def test_interpreter_supports_method_arguments_and_return_values(self):
        program = self.program()
        TypeChecker().check(program)
        output = []
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [7])

    def test_native_supports_method_arguments_and_return_values(self):
        program = self.program()
        TypeChecker().check(program)
        c_source = CCompiler().compile(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(c_source)
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, "7\n")


if __name__ == "__main__":
    unittest.main()
