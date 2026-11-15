"""Static type checking for the R+ MVP."""

from dataclasses import dataclass

from .ast import (
    Assignment, Binary, Block, Call, ExpressionStatement, FunctionDeclaration,
    ForStatement, WhileStatement, BreakStatement, ContinueStatement, GetExpression, IndexExpression, IfStatement, ListLiteral, Literal, Program, ReturnStatement, Unary, Variable,
    StructDeclaration, StructLiteral,
    ImplDeclaration,
    SetExpression, SetIndexStatement,
    VariableDeclaration,
)


class TypeErrorRPlus(Exception):
    pass


ANY = "Any"


@dataclass(frozen=True)
class FunctionType:
    parameters: tuple[str, ...]
    return_type: str


@dataclass(frozen=True)
class ModuleType:
    fields: dict[str, FunctionType]


@dataclass
class Binding:
    type_name: str | FunctionType | ModuleType
    mutable: bool = False


class TypeEnvironment:
    def __init__(self, parent=None):
        self.parent = parent
        self.values: dict[str, Binding] = {}

    def define(self, name, type_name, mutable=False):
        self.values[name] = Binding(type_name, mutable)

    def get(self, name):
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        raise TypeErrorRPlus(f"Undefined variable '{name}'")

    def find(self, name):
        if name in self.values:
            return self
        if self.parent:
            return self.parent.find(name)
        return None


class TypeChecker:
    def __init__(self):
        self.environment = TypeEnvironment()
        self.return_type = None
        self.loop_depth = 0
        self.structs = {}
        self.methods = {}
        self.environment.define("println", FunctionType((ANY,), "Unit"))
        self.environment.define("print", FunctionType((ANY,), "Unit"))
        self.environment.define("randomize", FunctionType(("String",), "String"))
        self.environment.define("input", FunctionType(("String",), "String"))
        self.environment.define("len", FunctionType((ANY,), "Int"))
        self.environment.define("gui", ModuleType({
            "open": FunctionType(("String", "Int", "Int"), "Unit"),
            "close": FunctionType((), "Unit"),
            "poll": FunctionType((), "Unit"),
            "clear": FunctionType(("Int", "Int", "Int"), "Unit"),
            "rectangle": FunctionType(("Int", "Int", "Int", "Int", "Int", "Int"), "Unit"),
            "present": FunctionType((), "Unit"),
            "should_close": FunctionType((), "Bool"),
            "key_down": FunctionType(("String",), "Bool"),
        }))

    def check(self, program: Program):
        for statement in program.statements:
            if isinstance(statement, StructDeclaration):
                self.structs[statement.name] = dict(statement.fields)
        for statement in program.statements:
            if isinstance(statement, ImplDeclaration):
                for method in statement.methods:
                    parameters = tuple(type_name or ANY for _, type_name in method.parameters)
                    self.methods[(statement.target, method.name)] = FunctionType(parameters, method.return_type or ANY)
        for statement in program.statements:
            if isinstance(statement, FunctionDeclaration):
                parameters = tuple(type_name or ANY for _, type_name in statement.parameters)
                self.environment.define(
                    statement.name,
                    FunctionType(parameters, statement.return_type or ANY),
                )
        for statement in program.statements:
            self.check_statement(statement)

    def check_statement(self, statement):
        if isinstance(statement, StructDeclaration):
            return
        if isinstance(statement, VariableDeclaration):
            actual = self.check_expression(statement.initializer)
            if statement.type_name and not self.compatible(statement.type_name, actual):
                self.fail(f"Variable '{statement.name}' expected {statement.type_name}, got {actual}")
            self.environment.define(statement.name, statement.type_name or actual, statement.mutable)
            return
        if isinstance(statement, Assignment):
            binding = self.environment.get(statement.name)
            if not binding.mutable:
                self.fail(f"Cannot assign to immutable variable '{statement.name}'")
            actual = self.check_expression(statement.value)
            if isinstance(binding.type_name, str) and not self.compatible(binding.type_name, actual):
                self.fail(f"Variable '{statement.name}' expected {binding.type_name}, got {actual}")
            return
        if isinstance(statement, SetIndexStatement):
            if isinstance(statement.object, Variable):
                binding = self.environment.get(statement.object.name)
                if not binding.mutable:
                    self.fail(f"Cannot mutate index on immutable variable '{statement.object.name}'")
            object_type = self.check_expression(statement.object)
            index_type = self.check_expression(statement.index)
            if index_type not in ("Int", ANY):
                self.fail(f"List index expected Int, got {index_type}")
            if not object_type.startswith("List["):
                self.fail(f"Cannot index {object_type}")
            expected = object_type[5:-1]
            actual = self.check_expression(statement.value)
            if not self.compatible(expected, actual):
                self.fail(f"List element expected {expected}, got {actual}")
            return
        if isinstance(statement, SetExpression):
            if isinstance(statement.object, Variable):
                binding = self.environment.get(statement.object.name)
                if not binding.mutable and not (isinstance(binding.type_name, str) and binding.type_name.startswith("&mut ")):
                    self.fail(f"Cannot mutate field on immutable variable '{statement.object.name}'")
            object_type = self.check_expression(statement.object)
            object_type = object_type.removeprefix("&mut ").removeprefix("&")
            if object_type not in self.structs or statement.name not in self.structs[object_type]:
                self.fail(f"Unknown field '{statement.name}' on '{object_type}'")
            actual = self.check_expression(statement.value)
            expected = self.structs[object_type][statement.name]
            if not self.compatible(expected, actual):
                self.fail(f"Field '{statement.name}' expected {expected}, got {actual}")
            return
        if isinstance(statement, ExpressionStatement):
            self.check_expression(statement.expression)
            return
        if isinstance(statement, ImplDeclaration):
            for method in statement.methods:
                function = self.methods[(statement.target, method.name)]
                previous_return = self.return_type
                previous_environment = self.environment
                self.return_type = function.return_type
                self.environment = TypeEnvironment(previous_environment)
                for (name, declared_type), parameter_type in zip(method.parameters, function.parameters):
                    self.environment.define(name, declared_type or parameter_type)
                self.check_block_contents(method.body)
                self.environment = previous_environment
                self.return_type = previous_return
            return
        if isinstance(statement, FunctionDeclaration):
            function = self.environment.get(statement.name).type_name
            previous_return = self.return_type
            previous_environment = self.environment
            self.return_type = function.return_type
            self.environment = TypeEnvironment(previous_environment)
            for (name, declared_type), parameter_type in zip(statement.parameters, function.parameters):
                self.environment.define(name, declared_type or parameter_type)
            self.check_block_contents(statement.body)
            self.environment = previous_environment
            self.return_type = previous_return
            return
        if isinstance(statement, ReturnStatement):
            if self.return_type is None:
                self.fail("Cannot return outside a function")
            actual = "Unit" if statement.value is None else self.check_expression(statement.value)
            if not self.compatible(self.return_type, actual):
                self.fail(f"Function expected {self.return_type}, got {actual}")
            return
        if isinstance(statement, IfStatement):
            condition = self.check_expression(statement.condition)
            if condition not in ("Bool", ANY):
                self.fail(f"If condition expected Bool, got {condition}")
            self.check_block(statement.then_branch)
            if statement.else_branch:
                if isinstance(statement.else_branch, Block):
                    self.check_block(statement.else_branch)
                else:
                    self.check_statement(statement.else_branch)
            return
        if isinstance(statement, (BreakStatement, ContinueStatement)):
            if self.loop_depth == 0:
                self.fail(f"'{type(statement).__name__.replace('Statement', '').lower()}' is only valid inside a loop")
            return
        if isinstance(statement, WhileStatement):
            condition = self.check_expression(statement.condition)
            if condition not in ("Bool", ANY, "Int"):
                self.fail(f"While condition expected Bool, got {condition}")
            self.loop_depth += 1
            self.check_block(statement.body)
            self.loop_depth -= 1
            return
        if isinstance(statement, ForStatement):
            iterable_type = self.check_expression(statement.iterable)
            if not iterable_type.startswith("List["):
                self.fail(f"For loop expected a list, got {iterable_type}")
            element_type = iterable_type[5:-1]
            previous = self.environment
            self.environment = TypeEnvironment(previous)
            self.environment.define(statement.name, element_type)
            self.loop_depth += 1
            self.check_block_contents(statement.body)
            self.loop_depth -= 1
            self.environment = previous
            return
        if isinstance(statement, Block):
            self.check_block(statement)
            return
        raise TypeErrorRPlus(f"Unknown statement {type(statement).__name__}")

    def check_block(self, block):
        previous = self.environment
        self.environment = TypeEnvironment(previous)
        self.check_block_contents(block)
        self.environment = previous

    def check_block_contents(self, block):
        for statement in block.statements:
            self.check_statement(statement)

    def check_expression(self, expression):
        if isinstance(expression, Literal):
            if expression.value is None: return "Unit"
            if isinstance(expression.value, bool): return "Bool"
            if isinstance(expression.value, int): return "Int"
            if isinstance(expression.value, float): return "Float"
            if isinstance(expression.value, str): return "String"
            return ANY
        if isinstance(expression, Variable):
            type_name = self.environment.get(expression.name).type_name
            return type_name if isinstance(type_name, str) else type_name
        if isinstance(expression, StructLiteral):
            if expression.type_name not in self.structs:
                self.fail(f"Unknown struct '{expression.type_name}'")
            expected_fields = self.structs[expression.type_name]
            provided = dict(expression.fields)
            if set(provided) != set(expected_fields):
                self.fail(f"Struct '{expression.type_name}' fields do not match declaration")
            for field_name, value in expression.fields:
                actual = self.check_expression(value)
                if not self.compatible(expected_fields[field_name], actual):
                    self.fail(f"Field '{field_name}' expected {expected_fields[field_name]}, got {actual}")
            return expression.type_name
        if isinstance(expression, IndexExpression):
            object_type = self.check_expression(expression.object)
            index_type = self.check_expression(expression.index)
            if index_type not in ("Int", ANY):
                self.fail(f"List index expected Int, got {index_type}")
            if object_type.startswith("List["):
                return object_type[5:-1]
            self.fail(f"Cannot index {object_type}")
        if isinstance(expression, GetExpression):
            object_type = self.check_expression(expression.object)
            if isinstance(object_type, ModuleType):
                if expression.name not in object_type.fields:
                    self.fail(f"Unknown function '{expression.name}' on module")
                return object_type.fields[expression.name]
            base_type = object_type.removeprefix("&mut ").removeprefix("&")
            method = self.methods.get((base_type, expression.name))
            if method:
                return FunctionType(method.parameters[1:], method.return_type)
            if base_type not in self.structs or expression.name not in self.structs[base_type]:
                self.fail(f"Unknown field '{expression.name}' on '{base_type}'")
            return self.structs[base_type][expression.name]
        if isinstance(expression, ListLiteral):
            element_types = [self.check_expression(element) for element in expression.elements]
            if not element_types:
                return "List[Any]"
            first = element_types[0]
            if any(not self.compatible(first, other) for other in element_types[1:]):
                self.fail("List elements must have the same type")
            return f"List[{first}]"
        if isinstance(expression, Unary):
            right = self.check_expression(expression.right)
            if expression.operator == "!":
                if right not in ("Bool", ANY):
                    self.fail(f"Unary '!' requires a Bool operand, got {right}")
                return "Bool"
            if expression.operator == "-" and right not in ("Int", "Float", ANY):
                self.fail(f"Unary '-' requires a numeric operand, got {right}")
            return right
        if isinstance(expression, Binary):
            return self.check_binary(expression)
        if isinstance(expression, Call):
            callee_type = self.check_expression(expression.callee)
            if not isinstance(callee_type, FunctionType):
                self.fail("Only functions can be called")
            if len(expression.arguments) != len(callee_type.parameters):
                self.fail(f"Expected {len(callee_type.parameters)} arguments, got {len(expression.arguments)}")
            for index, (argument, expected) in enumerate(zip(expression.arguments, callee_type.parameters), 1):
                actual = self.check_expression(argument)
                if not self.compatible(expected, actual):
                    name = expression.callee.name if isinstance(expression.callee, Variable) else "function"
                    self.fail(f"Argument {index} of '{name}' expected {expected}, got {actual}")
            return callee_type.return_type
        raise TypeErrorRPlus(f"Unknown expression {type(expression).__name__}")

    def check_binary(self, expression):
        left = self.check_expression(expression.left)
        right = self.check_expression(expression.right)
        if expression.operator in ("&&", "||"):
            if left not in ("Bool", ANY) or right not in ("Bool", ANY):
                self.fail(f"Operator '{expression.operator}' requires Bool operands")
            return "Bool"
        if expression.operator in ("==", "!=", ">", ">=", "<", "<="):
            if not self.compatible(left, right):
                self.fail(f"Cannot compare {left} and {right}")
            return "Bool"
        if expression.operator == "+" and left == right == "String":
            return "String"
        if expression.operator in ("+", "-", "*", "/"):
            if left in ("Int", "Float", ANY) and right in ("Int", "Float", ANY):
                return "Float" if "Float" in (left, right) else "Int"
            self.fail(f"Operator '{expression.operator}' requires matching numeric operands")
        self.fail(f"Unknown operator '{expression.operator}'")

    @staticmethod
    def compatible(expected, actual):
        if expected == ANY or actual == ANY:
            return True
        if isinstance(expected, FunctionType) or isinstance(actual, FunctionType):
            return expected == actual
        expected_base = expected.removeprefix("&mut ").removeprefix("&") if isinstance(expected, str) else expected
        actual_base = actual.removeprefix("&mut ").removeprefix("&") if isinstance(actual, str) else actual
        return expected_base == actual_base

    @staticmethod
    def fail(message):
        raise TypeErrorRPlus(message)
