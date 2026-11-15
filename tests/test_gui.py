import unittest

from rplus.compiler import CCompiler, CompileError
from rplus.interpreter import Interpreter
from rplus.lexer import Lexer
from rplus.ownership import OwnershipChecker
from rplus.parser import Parser
from rplus.typechecker import TypeChecker


class GuiTests(unittest.TestCase):
    source = 'if gui.should_close() { println("closed") }'

    def test_gui_module_typechecks_and_runs_without_opening_window(self):
        program = Parser(Lexer(self.source).tokenize()).parse()
        TypeChecker().check(program)
        OwnershipChecker().check(program)
        output = []
        Interpreter(output=output.append).execute(program)
        self.assertEqual(output, ["closed"])

    def test_native_backend_rejects_gui_explicitly(self):
        program = Parser(Lexer('gui.open("Demo", 320, 240)').tokenize()).parse()
        TypeChecker().check(program)
        OwnershipChecker().check(program)
        with self.assertRaisesRegex(CompileError, "interpreter mode only"):
            CCompiler().compile(program)


if __name__ == "__main__":
    unittest.main()
