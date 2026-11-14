"""Tree-walk interpreter used to validate the R+ language before native compilation."""

import random
from dataclasses import dataclass

from .ast import (
    Assignment, Binary, Block, Call, ExpressionStatement, FunctionDeclaration,
    ForStatement, WhileStatement, BreakStatement, ContinueStatement, GetExpression, IndexExpression, IfStatement, ListLiteral, Literal, Program, ReturnStatement, Unary,
    StructDeclaration, StructLiteral,
    ImplDeclaration, SetExpression, SetIndexStatement,
    Variable, VariableDeclaration,
)


class RuntimeErrorRPlus(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class ContinueSignal(Exception):
    pass


class BreakSignal(Exception):
    pass


@dataclass
class Binding:
    value: object
    mutable: bool


class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.values: dict[str, Binding] = {}

    def define(self, name, value, mutable=False):
        if name in self.values:
            raise RuntimeErrorRPlus(f"Variable '{name}' is already defined")
        self.values[name] = Binding(value, mutable)

    def get(self, name):
        if name in self.values:
            return self.values[name].value
        if self.parent:
            return self.parent.get(name)
        raise RuntimeErrorRPlus(f"Undefined variable '{name}'")

    def assign(self, name, value):
        if name in self.values:
            binding = self.values[name]
            if not binding.mutable:
                raise RuntimeErrorRPlus(f"Cannot assign to immutable variable '{name}'")
            binding.value = value
            return
        if self.parent:
            self.parent.assign(name, value)
            return
        raise RuntimeErrorRPlus(f"Undefined variable '{name}'")


@dataclass
class RStruct:
    type_name: str
    fields: dict[str, object]


@dataclass
class RFunction:
    declaration: FunctionDeclaration
    closure: Environment

    def call(self, interpreter, arguments):
        if len(arguments) != len(self.declaration.parameters):
            raise RuntimeErrorRPlus(
                f"Function '{self.declaration.name}' expected {len(self.declaration.parameters)} "
                f"arguments, got {len(arguments)}"
            )
        environment = Environment(self.closure)
        for (name, _), value in zip(self.declaration.parameters, arguments):
            environment.define(name, value)
        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnSignal as signal:
            return signal.value
        return None


class Interpreter:
    def __init__(self, output=None):
        self.globals = {}
        self.environment = Environment()
        self.output = output if output is not None else print
        self.methods = {}
        self.environment.define("println", self.output)
        self.environment.define("print", lambda value="": self.output(value, end=""))
        self.environment.define("randomize", lambda value: self.randomize(value))
        self.environment.define("input", lambda prompt="": self.read_input(prompt))
        self.environment.define("len", lambda value: len(value))

    def read_input(self, prompt=""):
        if prompt:
            self.output(prompt, end="")
        return input()

    @staticmethod
    def randomize(value):
        if not isinstance(value, str):
            raise RuntimeErrorRPlus("randomize expects a String")
        characters = list(value)
        random.SystemRandom().shuffle(characters)
        return "".join(characters)

    def execute(self, program: Program):
        for statement in program.statements:
            self.execute_statement(statement)

    def execute_statement(self, statement):
        if isinstance(statement, StructDeclaration):
            return
        if isinstance(statement, ImplDeclaration):
            for method in statement.methods:
                self.methods[(statement.target, method.name)] = RFunction(method, self.environment)
            return
        if isinstance(statement, VariableDeclaration):
            value = self.evaluate(statement.initializer)
            self.environment.define(statement.name, value, statement.mutable)
            self.sync_globals()
        elif isinstance(statement, Assignment):
            self.environment.assign(statement.name, self.evaluate(statement.value))
            self.sync_globals()
        elif isinstance(statement, SetIndexStatement):
            target = self.evaluate(statement.object)
            index = self.evaluate(statement.index)
            if not isinstance(index, int):
                raise RuntimeErrorRPlus("Index must be an Int")
            try:
                target[index] = self.evaluate(statement.value)
            except (IndexError, TypeError):
                raise RuntimeErrorRPlus("Index out of bounds")
        elif isinstance(statement, SetExpression):
            target = self.evaluate(statement.object)
            if not isinstance(target, RStruct):
                raise RuntimeErrorRPlus("Only structs have mutable fields")
            target.fields[statement.name] = self.evaluate(statement.value)
        elif isinstance(statement, ExpressionStatement):
            self.evaluate(statement.expression)
        elif isinstance(statement, Block):
            self.execute_block(statement, Environment(self.environment))
        elif isinstance(statement, FunctionDeclaration):
            self.environment.define(statement.name, RFunction(statement, self.environment))
            self.sync_globals()
        elif isinstance(statement, ReturnStatement):
            raise ReturnSignal(None if statement.value is None else self.evaluate(statement.value))
        elif isinstance(statement, IfStatement):
            if self.is_truthy(self.evaluate(statement.condition)):
                self.execute_block(statement.then_branch, Environment(self.environment))
            elif statement.else_branch:
                if isinstance(statement.else_branch, Block):
                    self.execute_block(statement.else_branch, Environment(self.environment))
                else:
                    self.execute_statement(statement.else_branch)
            self.sync_globals()
        elif isinstance(statement, BreakStatement):
            raise BreakSignal()
        elif isinstance(statement, ContinueStatement):
            raise ContinueSignal()
        elif isinstance(statement, WhileStatement):
            while self.is_truthy(self.evaluate(statement.condition)):
                try:
                    self.execute_block(statement.body, Environment(self.environment))
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            self.sync_globals()
        elif isinstance(statement, ForStatement):
            iterable = self.evaluate(statement.iterable)
            if not isinstance(iterable, list):
                raise RuntimeErrorRPlus("For loop requires a list")
            for value in iterable:
                loop_environment = Environment(self.environment)
                loop_environment.define(statement.name, value)
                try:
                    self.execute_block(statement.body, loop_environment)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            self.sync_globals()
        else:
            raise RuntimeErrorRPlus(f"Unknown statement {type(statement).__name__}")

    def execute_block(self, block, environment):
        previous = self.environment
        try:
            self.environment = environment
            for statement in block.statements:
                self.execute_statement(statement)
        finally:
            self.environment = previous

    def evaluate(self, expression):
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, Variable):
            return self.environment.get(expression.name)
        if isinstance(expression, StructLiteral):
            return RStruct(expression.type_name, {name: self.evaluate(value) for name, value in expression.fields})
        if isinstance(expression, IndexExpression):
            value = self.evaluate(expression.object)
            index = self.evaluate(expression.index)
            if not isinstance(index, int):
                raise RuntimeErrorRPlus("Index must be an Int")
            try:
                return value[index]
            except (IndexError, KeyError, TypeError):
                raise RuntimeErrorRPlus("Index out of bounds")
        if isinstance(expression, GetExpression):
            value = self.evaluate(expression.object)
            if not isinstance(value, RStruct) or expression.name not in value.fields:
                raise RuntimeErrorRPlus(f"Unknown field '{expression.name}'")
            return value.fields[expression.name]
        if isinstance(expression, ListLiteral):
            return [self.evaluate(element) for element in expression.elements]
        if isinstance(expression, Unary):
            value = self.evaluate(expression.right)
            if expression.operator == "-":
                return -value
            if expression.operator == "!":
                return not self.is_truthy(value)
        if isinstance(expression, Binary):
            return self.binary(expression)
        if isinstance(expression, Call):
            arguments = [self.evaluate(argument) for argument in expression.arguments]
            if isinstance(expression.callee, GetExpression):
                receiver = self.evaluate(expression.callee.object)
                if isinstance(receiver, RStruct):
                    method = self.methods.get((receiver.type_name, expression.callee.name))
                    if method:
                        return method.call(self, [receiver, *arguments])
            callee = self.evaluate(expression.callee)
            if isinstance(callee, RFunction):
                return callee.call(self, arguments)
            if callable(callee):
                return callee(*arguments)
            raise RuntimeErrorRPlus("Only functions can be called")
        raise RuntimeErrorRPlus(f"Unknown expression {type(expression).__name__}")

    def binary(self, expression):
        left = self.evaluate(expression.left)
        if expression.operator == "&&":
            return bool(left) and self.is_truthy(self.evaluate(expression.right))
        if expression.operator == "||":
            return bool(left) or self.is_truthy(self.evaluate(expression.right))
        right = self.evaluate(expression.right)
        operator = expression.operator
        if operator == "+": return left + right
        if operator == "-": return left - right
        if operator == "*": return left * right
        if operator == "/": return left / right
        if operator == "&&": return bool(left) and bool(right)
        if operator == "||": return bool(left) or bool(right)
        if operator == "==": return left == right
        if operator == "!=": return left != right
        if operator == ">": return left > right
        if operator == ">=": return left >= right
        if operator == "<": return left < right
        if operator == "<=": return left <= right
        raise RuntimeErrorRPlus(f"Unknown operator '{operator}'")

    @staticmethod
    def is_truthy(value):
        return bool(value)

    def sync_globals(self):
        self.globals = {name: binding.value for name, binding in self.environment.values.items()}
