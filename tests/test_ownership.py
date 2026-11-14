import unittest

from rplus.lexer import Lexer
from rplus.ownership import OwnershipChecker, OwnershipError
from rplus.parser import Parser


class OwnershipCheckerTests(unittest.TestCase):
    def check(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        OwnershipChecker().check(program)

    def test_copy_types_can_be_reused(self):
        self.check("let first = 41 let second = first println(first)")

    def test_moving_a_string_invalidates_the_source(self):
        with self.assertRaisesRegex(OwnershipError, "Use of moved value 'first'"):
            self.check('let first = "owned" let second = first println(first)')

    def test_moving_a_list_invalidates_the_source(self):
        with self.assertRaisesRegex(OwnershipError, "Use of moved value 'items'"):
            self.check("let items = [1, 2] let other = items println(items)")

    def test_function_arguments_move_non_copy_values(self):
        source = 'fn consume(text: String) -> Unit { return } let text = "owned" consume(text) println(text)'
        with self.assertRaisesRegex(OwnershipError, "Use of moved value 'text'"):
            self.check(source)


if __name__ == "__main__":
    unittest.main()
