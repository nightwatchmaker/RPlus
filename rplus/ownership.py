"""A first compile-time ownership pass for R+.

R+ values are borrowed conceptually by expressions. Directly binding or passing a
non-Copy value moves it, making the original name unavailable afterward.
"""

from dataclasses import dataclass

from .ast import (
    Assignment, Binary, Block, Call, ExpressionStatement, FunctionDeclaration,
    ForStatement, WhileStatement, BreakStatement, ContinueStatement, IfStatement, ListLiteral, Literal, Program, ReturnStatement, Unary, Variable,
    SetExpression, SetIndexStatement, StructDeclaration, ImplDeclaration, StructLiteral, GetExpression, IndexExpression,
    VariableDeclaration,
)


class OwnershipError(Exception):
    pass


@dataclass
class Binding:
    type_name: str
    moved: bool = False
    mutable: bool = False


class OwnershipEnvironment:
    def __init__(self, parent=None):
        self.parent = parent
        self.values: dict[str, Binding] = {}

    def define(self, name, type_name, mutable=False):
        self.values[name] = Binding(type_name, mutable=mutable)

    def get(self, name):
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        raise OwnershipError(f"Undefined value '{name}'")


class OwnershipChecker:
    COPY_TYPES = {"Int", "Float", "Bool", "Unit", "Any"}
    BUILTINS = {"print", "println", "randomize", "input", "len", "gui"}

    def __init__(self):
        self.environment = OwnershipEnvironment()
        self.functions: dict[str, FunctionDeclaration] = {}
        self.function_types: dict[str, tuple[list[str], str]] = {}
        self.method_types: dict[tuple[str, str], tuple[list[str], str]] = {}
        for builtin in self.BUILTINS:
            self.environment.define(builtin, "Any")

    def check(self, program: Program):
        for statement in program.statements:
            if isinstance(statement, FunctionDeclaration):
                self.functions[statement.name] = statement
                self.function_types[statement.name] = (
                    [type_name or "Any" for _, type_name in statement.parameters],
                    statement.return_type or "Any",
                )
            elif isinstance(statement, ImplDeclaration):
                for method in statement.methods:
                    self.method_types[(statement.target, method.name)] = (
                        [type_name or "Any" for _, type_name in method.parameters],
                        method.return_type or "Any",
                    )
        for statement in program.statements:
            self.check_statement(statement)

    def check_statement(self, statement):
        if isinstance(statement, StructDeclaration):
            return
        if isinstance(statement, ImplDeclaration):
            for method in statement.methods:
                previous = self.environment
                self.environment = OwnershipEnvironment(previous)
                for name, type_name in method.parameters:
                    self.environment.define(name, type_name or "Any")
                for body_statement in method.body.statements:
                    self.check_statement(body_statement)
                self.environment = previous
            return
        if isinstance(statement, VariableDeclaration):
            value_type = self.check_expression(statement.initializer, consume=True)
            self.environment.define(statement.name, statement.type_name or value_type, statement.mutable)
            return
        if isinstance(statement, Assignment):
            self.check_expression(statement.value, consume=True)
            return
        if isinstance(statement, SetIndexStatement):
            self.check_expression(statement.object)
            self.check_expression(statement.index)
            self.check_expression(statement.value, consume=True)
            return
        if isinstance(statement, SetExpression):
            self.check_expression(statement.object)
            self.check_expression(statement.value, consume=True)
            return
        if isinstance(statement, ExpressionStatement):
            self.check_expression(statement.expression)
            return
        if isinstance(statement, FunctionDeclaration):
            # Function bodies get their own ownership world; parameters are owned
            # by the callee and disappear when the call returns.
            previous = self.environment
            self.environment = OwnershipEnvironment(previous)
            for name, type_name in statement.parameters:
                self.environment.define(name, type_name or "Any")
            for body_statement in statement.body.statements:
                self.check_statement(body_statement)
            self.environment = previous
            return
        if isinstance(statement, ReturnStatement):
            if statement.value is not None:
                self.check_expression(statement.value, consume=True)
            return
        if isinstance(statement, IfStatement):
            self.check_expression(statement.condition)
            self.check_block(statement.then_branch)
            if statement.else_branch:
                if isinstance(statement.else_branch, Block):
                    self.check_block(statement.else_branch)
                else:
                    self.check_statement(statement.else_branch)
            return
        if isinstance(statement, (BreakStatement, ContinueStatement)):
            return
        if isinstance(statement, WhileStatement):
            self.check_expression(statement.condition)
            self.check_block(statement.body)
            return
        if isinstance(statement, ForStatement):
            self.check_expression(statement.iterable)
            previous = self.environment
            self.environment = OwnershipEnvironment(previous)
            self.environment.define(statement.name, "Any")
            for body_statement in statement.body.statements:
                self.check_statement(body_statement)
            self.environment = previous
            return
        if isinstance(statement, Block):
            self.check_block(statement)
            return
        raise OwnershipError(f"Unknown statement {type(statement).__name__}")

    def check_block(self, block):
        previous = self.environment
        self.environment = OwnershipEnvironment(previous)
        for statement in block.statements:
            self.check_statement(statement)
        self.environment = previous

    def check_expression(self, expression, consume=False):
        if isinstance(expression, Literal):
            if isinstance(expression.value, bool): return "Bool"
            if isinstance(expression.value, int): return "Int"
            if isinstance(expression.value, float): return "Float"
            if isinstance(expression.value, str): return "String"
            return "Any"
        if isinstance(expression, Variable):
            binding = self.environment.get(expression.name)
            if binding.moved:
                raise OwnershipError(f"Use of moved value '{expression.name}'")
            if consume and not self.is_copy(binding.type_name):
                binding.moved = True
            return binding.type_name
        if isinstance(expression, StructLiteral):
            for _, value in expression.fields:
                self.check_expression(value)
            return expression.type_name
        if isinstance(expression, IndexExpression):
            self.check_expression(expression.object)
            self.check_expression(expression.index)
            return "Any"
        if isinstance(expression, GetExpression):
            return self.check_expression(expression.object)
        if isinstance(expression, ListLiteral):
            for element in expression.elements:
                self.check_expression(element)
            return "List[Any]"
        if isinstance(expression, Unary):
            return self.check_expression(expression.right)
        if isinstance(expression, Binary):
            left = self.check_expression(expression.left)
            right = self.check_expression(expression.right)
            return "String" if left == right == "String" else left
        if isinstance(expression, Call):
            if isinstance(expression.callee, GetExpression) and isinstance(expression.callee.object, Variable):
                receiver = expression.callee.object
                receiver_type = self.check_expression(receiver)
                method = self.method_types.get((receiver_type, expression.callee.name))
                if method:
                    parameter_types, return_type = method
                    if parameter_types and parameter_types[0].startswith("&mut "):
                        binding = self.environment.get(receiver.name)
                        if not binding.mutable:
                            raise OwnershipError(
                                f"Mutable borrow requires mutable variable '{receiver.name}'"
                            )
                    for argument, parameter_type in zip(expression.arguments, parameter_types[1:]):
                        self.check_expression(argument, consume=not self.is_copy(parameter_type))
                    return return_type
                self.check_expression(expression.callee)
                for argument in expression.arguments:
                    self.check_expression(argument)
                return "Unit"
            if isinstance(expression.callee, Variable) and expression.callee.name in self.function_types:
                parameter_types, return_type = self.function_types[expression.callee.name]
                for argument, parameter_type in zip(expression.arguments, parameter_types):
                    if parameter_type.startswith("&mut ") and isinstance(argument, Variable):
                        binding = self.environment.get(argument.name)
                        if not binding.mutable:
                            raise OwnershipError(
                                f"Mutable borrow requires mutable variable '{argument.name}'"
                            )
                    self.check_expression(argument, consume=not self.is_copy(parameter_type))
                return return_type
            if isinstance(expression.callee, Variable) and expression.callee.name in self.BUILTINS:
                for argument in expression.arguments:
                    self.check_expression(argument)
                return "Unit"
            for argument in expression.arguments:
                self.check_expression(argument)
            return "Unit"
        raise OwnershipError(f"Unknown expression {type(expression).__name__}")

    def is_copy(self, type_name):
        return type_name.startswith("&") or type_name in self.COPY_TYPES

