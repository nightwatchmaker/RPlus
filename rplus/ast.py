"""Abstract syntax tree nodes for the R+ MVP."""

from dataclasses import dataclass, field
from typing import Any


class Node:
    pass


class Expression(Node):
    pass


class Statement(Node):
    pass


@dataclass
class Program(Node):
    statements: list[Statement] = field(default_factory=list)


@dataclass
class Literal(Expression):
    value: Any


@dataclass
class Variable(Expression):
    name: str


@dataclass
class Unary(Expression):
    operator: str
    right: Expression


@dataclass
class Binary(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass
class Call(Expression):
    callee: Expression
    arguments: list[Expression]


@dataclass
class ListLiteral(Expression):
    elements: list[Expression]


@dataclass
class VariableDeclaration(Statement):
    name: str
    initializer: Expression
    mutable: bool = False
    type_name: str | None = None


@dataclass
class Assignment(Statement):
    name: str
    value: Expression


@dataclass
class ExpressionStatement(Statement):
    expression: Expression


@dataclass
class Block(Statement):
    statements: list[Statement]


@dataclass
class FunctionDeclaration(Statement):
    name: str
    parameters: list[tuple[str, str | None]]
    body: Block
    return_type: str | None = None


@dataclass
class ReturnStatement(Statement):
    value: Expression | None = None


@dataclass
class IfStatement(Statement):
    condition: Expression
    then_branch: Block
    else_branch: Block | IfStatement | None = None


@dataclass
class BreakStatement(Statement):
    pass


@dataclass
class ContinueStatement(Statement):
    pass


@dataclass
class WhileStatement(Statement):
    condition: Expression
    body: Block


@dataclass
class ForStatement(Statement):
    name: str
    iterable: Expression
    body: Block


@dataclass
class ImportDeclaration(Statement):
    path: str


@dataclass
class StructDeclaration(Statement):
    name: str
    fields: list[tuple[str, str]]


@dataclass
class ImplDeclaration(Statement):
    target: str
    methods: list[FunctionDeclaration]


@dataclass
class StructLiteral(Expression):
    type_name: str
    fields: list[tuple[str, Expression]]


@dataclass
class IndexExpression(Expression):
    object: Expression
    index: Expression


@dataclass
class GetExpression(Expression):
    object: Expression
    name: str


@dataclass
class SetIndexStatement(Statement):
    object: Expression
    index: Expression
    value: Expression


@dataclass
class SetExpression(Statement):
    object: Expression
    name: str
    value: Expression

