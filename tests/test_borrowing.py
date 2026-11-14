import unittest

from rplus.lexer import Lexer
from rplus.ownership import OwnershipChecker, OwnershipError
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class BorrowingTests(unittest.TestCase):
    def check(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        OwnershipChecker().check(program)

    def test_shared_reference_does_not_move_value(self):
        source = 'fn show(text: &String) -> Unit { println(text) } let text = "owned" show(text) println(text)'
        self.check(source)

    def test_mutable_reference_does_not_move_value(self):
        source = 'fn edit(text: &mut String) -> Unit { println(text) } mut text = "owned" edit(text) println(text)'
        self.check(source)

    def test_mutable_reference_requires_mutable_source(self):
        source = 'fn edit(text: &mut String) -> Unit { println(text) } let text = "owned" edit(text)'
        with self.assertRaisesRegex(OwnershipError, "Mutable borrow requires mutable variable 'text'"):
            self.check(source)

    def test_borrowing_a_moved_value_is_still_rejected(self):
        source = 'fn show(text: &String) -> Unit { println(text) } let text = "owned" let moved = text show(text)'
        with self.assertRaisesRegex(OwnershipError, "Use of moved value 'text'"):
            self.check(source)


if __name__ == "__main__":
    unittest.main()
