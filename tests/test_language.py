import unittest

from rplus.ast import Binary, FunctionDeclaration, VariableDeclaration
from rplus.interpreter import Interpreter, RuntimeErrorRPlus
from rplus.lexer import Lexer
from rplus.parser import Parser, ParseError


class ParserTests(unittest.TestCase):
    def parse(self, source):
        return Parser(Lexer(source).tokenize()).parse()

    def test_parses_variable_and_function_declarations(self):
        program = self.parse("let answer = 40 + 2 fn double(x: Int) -> Int { return x * 2 }")

        self.assertIsInstance(program.statements[0], VariableDeclaration)
        self.assertIsInstance(program.statements[0].initializer, Binary)
        self.assertIsInstance(program.statements[1], FunctionDeclaration)
        self.assertEqual(program.statements[1].name, "double")

    def test_rejects_missing_expression(self):
        with self.assertRaises(ParseError):
            self.parse("let broken =")


class InterpreterTests(unittest.TestCase):
    def run_program(self, source):
        interpreter = Interpreter()
        interpreter.execute(Parser(Lexer(source).tokenize()).parse())
        return interpreter

    def test_runs_functions_and_returns_values(self):
        interpreter = self.run_program("fn add(a: Int, b: Int) -> Int { return a + b } let result = add(20, 22)")
        self.assertEqual(interpreter.globals.get("result"), 42)

    def test_supports_mutation_and_if(self):
        interpreter = self.run_program("mut score = 1 if true { score = score + 4 }")
        self.assertEqual(interpreter.globals.get("score"), 5)

    def test_raises_for_unknown_variable(self):
        with self.assertRaisesRegex(RuntimeErrorRPlus, "Undefined variable 'missing'"):
            self.run_program("println(missing)")


if __name__ == "__main__":
    unittest.main()
