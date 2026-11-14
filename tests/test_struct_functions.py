import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.interpreter import Interpreter
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class StructFunctionTests(unittest.TestCase):
    source = '''
struct Player { health: Int, name: String }
fn health_of(player: Player) -> Int { return player.health }
let player = Player { health: 100, name: "Ava" }
println(health_of(player))
'''

    def test_interpreter_passes_structs_to_functions(self):
        program = Parser(Lexer(self.source).tokenize()).parse()
        TypeChecker().check(program)
        output = []
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [100])

    def test_native_backend_passes_structs_to_functions(self):
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
        self.assertEqual(result.stdout, "100\n")


if __name__ == "__main__":
    unittest.main()
