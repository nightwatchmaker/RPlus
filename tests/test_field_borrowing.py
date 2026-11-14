import unittest

from rplus.lexer import Lexer
from rplus.ownership import OwnershipChecker, OwnershipError
from rplus.parser import Parser
from rplus.typechecker import TypeChecker, TypeErrorRPlus


class FieldBorrowingTests(unittest.TestCase):
    def check(self, source):
        program = Parser(Lexer(source).tokenize()).parse()
        TypeChecker().check(program)
        OwnershipChecker().check(program)

    def test_field_mutation_requires_mutable_binding(self):
        source = '''
        struct Counter { value: Int }
        let counter = Counter { value: 0 }
        counter.value = 1
        '''
        with self.assertRaisesRegex(TypeErrorRPlus, "Cannot mutate field on immutable variable 'counter'"):
            self.check(source)

    def test_mutable_receiver_can_mutate_fields(self):
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


if __name__ == "__main__":
    unittest.main()
