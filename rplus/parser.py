"""Recursive-descent parser for R+ source tokens."""

from .ast import (
    Assignment, Binary, Block, Call, ExpressionStatement, FunctionDeclaration, ImportDeclaration,
    ForStatement, WhileStatement, GetExpression, IndexExpression, IfStatement, ListLiteral, Literal, Program, ReturnStatement,
    StructDeclaration, StructLiteral, Unary, BreakStatement, ContinueStatement,
    ImplDeclaration,
    SetExpression, SetIndexStatement,
    Variable, VariableDeclaration,
)
from .lexer import Token, TokenType


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0
        self.struct_names = set()

    def parse(self) -> Program:
        statements = []
        while not self.check(TokenType.EOF):
            statements.append(self.declaration())
        return Program(statements)

    def declaration(self):
        if self.match(TokenType.IMPORT):
            return self.import_declaration()
        if self.match(TokenType.LET, TokenType.MUT):
            return self.variable_declaration(self.previous().type == TokenType.MUT)
        if self.match(TokenType.FN):
            return self.function_declaration()
        if self.match(TokenType.STRUCT):
            return self.struct_declaration()
        if self.match(TokenType.IMPL):
            return self.impl_declaration()
        return self.statement()

    def import_declaration(self):
        if self.match(TokenType.STRING):
            return ImportDeclaration(self.previous().lexeme[1:-1])
        start_line = self.peek().line
        parts = []
        allowed = {TokenType.IDENTIFIER, TokenType.DOT, TokenType.SLASH}
        while not self.check(TokenType.EOF) and self.peek().line == start_line and self.peek().type in allowed:
            parts.append(self.advance().lexeme)
        if not parts:
            raise ParseError("Expected .rpa path after import")
        return ImportDeclaration("".join(parts))

    def struct_declaration(self):
        name = self.consume(TokenType.IDENTIFIER, "Expected struct name")
        self.consume(TokenType.LEFT_BRACE, "Expected '{' after struct name")
        fields = []
        while not self.check(TokenType.RIGHT_BRACE):
            field = self.consume(TokenType.IDENTIFIER, "Expected field name")
            self.consume(TokenType.COLON, "Expected ':' after field name")
            field_type = self.optional_type_after_colon()
            fields.append((field.lexeme, field_type))
            if not self.match(TokenType.COMMA):
                break
        self.consume(TokenType.RIGHT_BRACE, "Expected '}' after struct fields")
        self.struct_names.add(name.lexeme)
        return StructDeclaration(name.lexeme, fields)

    def impl_declaration(self):
        target = self.consume(TokenType.IDENTIFIER, "Expected type name after impl")
        self.consume(TokenType.LEFT_BRACE, "Expected '{' after impl type")
        methods = []
        while not self.check(TokenType.RIGHT_BRACE):
            self.consume(TokenType.FN, "Expected 'fn' in impl block")
            methods.append(self.function_declaration())
        self.consume(TokenType.RIGHT_BRACE, "Expected '}' after impl block")
        return ImplDeclaration(target.lexeme, methods)

    def variable_declaration(self, mutable: bool):
        name = self.consume(TokenType.IDENTIFIER, "Expected variable name")
        type_name = self.optional_type()
        self.consume(TokenType.EQUAL, "Expected '=' after variable name")
        initializer = self.expression()
        return VariableDeclaration(name.lexeme, initializer, mutable, type_name)

    def function_declaration(self):
        name = self.consume(TokenType.IDENTIFIER, "Expected function name")
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after function name")
        parameters = []
        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                parameter = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
                parameters.append((parameter.lexeme, self.optional_type()))
                if not self.match(TokenType.COMMA):
                    break
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters")
        return_type = None
        if self.match(TokenType.ARROW):
            return_type = self.consume(TokenType.IDENTIFIER, "Expected return type").lexeme
        body = self.block()
        return FunctionDeclaration(name.lexeme, parameters, body, return_type)

    def statement(self):
        if self.match(TokenType.RETURN):
            value = None if self.check(TokenType.RIGHT_BRACE, TokenType.EOF) else self.expression()
            return ReturnStatement(value)
        if self.match(TokenType.BREAK):
            return BreakStatement()
        if self.match(TokenType.CONTINUE):
            return ContinueStatement()
        if self.match(TokenType.IF):
            return self.if_statement()
        if self.match(TokenType.FOR):
            return self.for_statement()
        if self.match(TokenType.WHILE):
            return WhileStatement(self.expression(), self.block())
        if self.match(TokenType.LEFT_BRACE):
            return self.block(already_open=True)
        if self.check(TokenType.IDENTIFIER):
            target = self.expression()
            if self.match(TokenType.EQUAL):
                value = self.expression()
                if isinstance(target, Variable):
                    return Assignment(target.name, value)
                if isinstance(target, GetExpression):
                    return SetExpression(target.object, target.name, value)
                if isinstance(target, IndexExpression):
                    return SetIndexStatement(target.object, target.index, value)
                raise ParseError("Invalid assignment target")
            return ExpressionStatement(target)
        return ExpressionStatement(self.expression())

    def if_statement(self):
        condition = self.expression()
        then_branch = self.block()
        else_branch = None
        if self.match(TokenType.ELSE):
            else_branch = self.if_statement() if self.match(TokenType.IF) else self.block()
        return IfStatement(condition, then_branch, else_branch)

    def for_statement(self):
        name = self.consume(TokenType.IDENTIFIER, "Expected loop variable name")
        self.consume(TokenType.IN, "Expected 'in' after loop variable")
        iterable = self.expression()
        return ForStatement(name.lexeme, iterable, self.block())

    def block(self, already_open=False):
        if not already_open:
            self.consume(TokenType.LEFT_BRACE, "Expected '{'")
        statements = []
        while not self.check(TokenType.RIGHT_BRACE) and not self.check(TokenType.EOF):
            statements.append(self.declaration())
        self.consume(TokenType.RIGHT_BRACE, "Expected '}' after block")
        return Block(statements)

    def expression(self):
        return self.logical_or()

    def logical_or(self):
        expr = self.logical_and()
        while self.match(TokenType.OR_OR):
            expr = Binary(expr, "||", self.logical_and())
        return expr

    def logical_and(self):
        expr = self.equality()
        while self.match(TokenType.AND_AND):
            expr = Binary(expr, "&&", self.equality())
        return expr

    def equality(self):
        expr = self.comparison()
        while self.match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            operator = self.previous().lexeme
            expr = Binary(expr, operator, self.comparison())
        return expr

    def comparison(self):
        expr = self.term()
        while self.match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL):
            operator = self.previous().lexeme
            expr = Binary(expr, operator, self.term())
        return expr

    def term(self):
        expr = self.factor()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous().lexeme
            expr = Binary(expr, operator, self.factor())
        return expr

    def factor(self):
        expr = self.unary()
        while self.match(TokenType.STAR, TokenType.SLASH):
            operator = self.previous().lexeme
            expr = Binary(expr, operator, self.unary())
        return expr

    def unary(self):
        if self.match(TokenType.MINUS, TokenType.BANG):
            return Unary(self.previous().lexeme, self.unary())
        return self.call()

    def call(self):
        expr = self.primary()
        while True:
            if self.match(TokenType.LEFT_PAREN):
                arguments = []
                if not self.check(TokenType.RIGHT_PAREN):
                    while True:
                        arguments.append(self.expression())
                        if not self.match(TokenType.COMMA):
                            break
                self.consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments")
                expr = Call(expr, arguments)
            elif self.match(TokenType.LEFT_BRACKET):
                index = self.expression()
                self.consume(TokenType.RIGHT_BRACKET, "Expected ']' after index")
                expr = IndexExpression(expr, index)
            elif self.match(TokenType.DOT):
                name = self.consume(TokenType.IDENTIFIER, "Expected property name after '.'")
                expr = GetExpression(expr, name.lexeme)
            else:
                break
        return expr

    def primary(self):
        if self.match(TokenType.INTEGER):
            return Literal(int(self.previous().lexeme))
        if self.match(TokenType.FLOAT):
            return Literal(float(self.previous().lexeme))
        if self.match(TokenType.STRING):
            raw = self.previous().lexeme[1:-1]
            return Literal(bytes(raw, "utf-8").decode("unicode_escape"))
        if self.match(TokenType.TRUE):
            return Literal(True)
        if self.match(TokenType.FALSE):
            return Literal(False)
        if self.match(TokenType.IDENTIFIER):
            name = self.previous().lexeme
            if name in self.struct_names and self.match(TokenType.LEFT_BRACE):
                fields = []
                if not self.check(TokenType.RIGHT_BRACE):
                    while True:
                        field = self.consume(TokenType.IDENTIFIER, "Expected field name")
                        self.consume(TokenType.COLON, "Expected ':' after field name")
                        fields.append((field.lexeme, self.expression()))
                        if not self.match(TokenType.COMMA):
                            break
                self.consume(TokenType.RIGHT_BRACE, "Expected '}' after struct literal")
                return StructLiteral(name, fields)
            return Variable(name)
        if self.match(TokenType.LEFT_BRACKET):
            elements = []
            if not self.check(TokenType.RIGHT_BRACKET):
                while True:
                    elements.append(self.expression())
                    if not self.match(TokenType.COMMA):
                        break
            self.consume(TokenType.RIGHT_BRACKET, "Expected ']' after list")
            return ListLiteral(elements)
        if self.match(TokenType.LEFT_PAREN):
            expr = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after expression")
            return expr
        token = self.peek()
        raise ParseError(f"Expected expression at {token.line}:{token.column}")

    def optional_type(self):
        if not self.match(TokenType.COLON):
            return None
        reference = self.match(TokenType.AMPERSAND)
        mutable_reference = reference and self.match(TokenType.MUT)
        name = self.consume(TokenType.IDENTIFIER, "Expected type name").lexeme
        if mutable_reference:
            return f"&mut {name}"
        if reference:
            return f"&{name}"
        return name

    def optional_type_after_colon(self):
        reference = self.match(TokenType.AMPERSAND)
        mutable_reference = reference and self.match(TokenType.MUT)
        name = self.consume(TokenType.IDENTIFIER, "Expected type name").lexeme
        if mutable_reference:
            return f"&mut {name}"
        if reference:
            return f"&{name}"
        return name

    def consume(self, token_type, message):
        if self.check(token_type):
            return self.advance()
        token = self.peek()
        raise ParseError(f"{message} at {token.line}:{token.column}")

    def match(self, *types):
        for token_type in types:
            if self.check(token_type):
                self.advance()
                return True
        return False

    def check(self, *token_types):
        current_type = self.peek().type
        return any(current_type == token_type for token_type in token_types)

    def check_next(self, token_type):
        return self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].type == token_type

    def advance(self):
        if not self.at_end():
            self.current += 1
        return self.previous()

    def at_end(self):
        return self.peek().type == TokenType.EOF

    def peek(self):
        return self.tokens[self.current]

    def previous(self):
        return self.tokens[self.current - 1]
