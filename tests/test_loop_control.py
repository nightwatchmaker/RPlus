import os
import subprocess
import tempfile
import unittest

from rplus.compiler import CCompiler
from rplus.interpreter import Interpreter
from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker, TypeErrorRPlus


SOURCE = '''
mut count = 0
while count < 10 {
    count = count + 1
    if count == 2 { continue }
    if count == 5 { break }
    println(count)
}
'''


class LoopControlTests(unittest.TestCase):
    def test_interpreter(self):
        program = Parser(Lexer(SOURCE).tokenize()).parse()
        TypeChecker().check(program)
        output = []
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [1, 3, 4])

    def test_loop_control_outside_loop_is_rejected(self):
        for keyword in ("break", "continue"):
            program = Parser(Lexer(keyword).tokenize()).parse()
            with self.assertRaisesRegex(TypeErrorRPlus, "only valid inside a loop"):
                TypeChecker().check(program)

    def test_for_loop_control_interpreter(self):
        source = '''
        for value in [1, 2, 3, 4] {
            if value == 2 { continue }
            if value == 4 { break }
            println(value)
        }
        '''
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        output = []
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, [1, 3])

    def test_native(self):
        program = Parser(Lexer(SOURCE).tokenize()).parse()
        TypeChecker().check(program)
        with tempfile.TemporaryDirectory() as directory:
            c_path = os.path.join(directory, "program.c")
            binary_path = os.path.join(directory, "program")
            with open(c_path, "w", encoding="utf-8") as handle:
                handle.write(CCompiler().compile(program))
            subprocess.run(["clang", "-std=c11", "-Wall", "-Werror", c_path, "-o", binary_path], check=True)
            result = subprocess.run([binary_path], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, "1\n3\n4\n")


if __name__ == "__main__":
    unittest.main()
