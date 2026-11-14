import unittest

from rplus.lexer import Lexer
from rplus.parser import Parser
from rplus.typechecker import TypeChecker, TypeErrorRPlus


class TypeCheckerTests(unittest.TestCase):
    def check(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)

    def test_accepts_inferred_values_and_function_calls(self):
        self.check("fn add(a: Int, b: Int) -> Int { return a + b } let answer: Int = add(20, 22)")

    def test_rejects_incompatible_annotation(self):
        with self.assertRaisesRegex(TypeErrorRPlus, "expected Int, got String"):
            self.check('let answer: Int = "nope"')

    def test_rejects_invalid_operator_types(self):
        with self.assertRaisesRegex(TypeErrorRPlus, "Operator '\+' requires matching numeric operands"):
            self.check('let broken = "a" + 1')

    def test_rejects_wrong_function_argument_type(self):
        with self.assertRaisesRegex(TypeErrorRPlus, "Argument 1 of 'add' expected Int, got String"):
            self.check('fn add(a: Int) -> Int { return a } add("nope")')


if __name__ == "__main__":
    unittest.main()
