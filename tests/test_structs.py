import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.interpreter import Interpreter
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class StructTests(unittest.TestCase):
    source = '''
struct Player {
    health: Int,
    name: String
}
let player = Player { health: 100, name: "Ava" }
println(player.health)
println(player.name)
'''

    def program(self):
        return Parser(Lexer(self.source).tokenize()).parse()

    def test_interpreter_supports_struct_fields(self):
        output = []
        program = self.program()
        TypeChecker().check(program)
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [100, "Ava"])

    def test_native_backend_supports_struct_fields(self):
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
        self.assertEqual(result.stdout, "100\nAva\n")


if __name__ == "__main__":
    unittest.main()
