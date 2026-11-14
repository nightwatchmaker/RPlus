import unittest

from rplus.lexer import Lexer
from rplus.ownership import OwnershipChecker, OwnershipError
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class MethodBorrowingTests(unittest.TestCase):
    def check(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        OwnershipChecker().check(program)

    def test_mutable_method_requires_mutable_receiver(self):
        source = '''
        struct Counter { value: Int }
        impl Counter {
            fn increment(self: &mut Counter) -> Unit {
                self.value = self.value + 1
            }
        }
        let counter = Counter { value: 0 }
        counter.increment()
        '''
        with self.assertRaisesRegex(OwnershipError, "Mutable borrow requires mutable variable 'counter'"):
            self.check(source)

    def test_mutable_method_accepts_mutable_receiver(self):
        source = '''
        struct Counter { value: Int }
        impl Counter {
            fn increment(self: &mut Counter) -> Unit {
                self.value = self.value + 1
            }
        }
        mut counter = Counter { value: 0 }
        counter.increment()
        '''
        self.check(source)

    def test_shared_method_does_not_move_receiver(self):
        source = '''
        struct Counter { value: Int }
        impl Counter {
            fn read(self: &Counter) -> Int { return self.value }
        }
        let counter = Counter { value: 4 }
        counter.read()
        counter.read()
        '''
        self.check(source)


if __name__ == "__main__":
    unittest.main()
