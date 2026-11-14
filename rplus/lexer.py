"""The first R+ frontend stage: turn source text into tokens."""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    IDENTIFIER = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()

    IMPORT = auto()
    LET = auto()
    MUT = auto()
    FN = auto()
    STRUCT = auto()
    IMPL = auto()
    FOR = auto()
    WHILE = auto()
    BREAK = auto()
    CONTINUE = auto()
    IN = auto()
    IF = auto()
    ELSE = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    BANG = auto()
    BANG_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    ARROW = auto()
    AND_AND = auto()
    OR_OR = auto()
    AMPERSAND = auto()

    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()

    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int


class LexerError(Exception):
    """Raised when source cannot be converted into valid R+ tokens."""


class Lexer:
    KEYWORDS = {
        "import": TokenType.IMPORT,
        "let": TokenType.LET,
        "mut": TokenType.MUT,
        "fn": TokenType.FN,
        "struct": TokenType.STRUCT,
        "impl": TokenType.IMPL,
        "for": TokenType.FOR,
        "while": TokenType.WHILE,
        "break": TokenType.BREAK,
        "continue": TokenType.CONTINUE,
        "in": TokenType.IN,
        "if": TokenType.IF,
        "else": TokenType.ELSE,
        "return": TokenType.RETURN,
        "true": TokenType.TRUE,
        "false": TokenType.FALSE,
    }

    SIMPLE_TOKENS = {
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "*": TokenType.STAR,
        "/": TokenType.SLASH,
        "=": TokenType.EQUAL,
        "!": TokenType.BANG_EQUAL,  # validated below; bare ! is rejected
        "<": TokenType.LESS,
        ">": TokenType.GREATER,
        "(": TokenType.LEFT_PAREN,
        ")": TokenType.RIGHT_PAREN,
        "{": TokenType.LEFT_BRACE,
        "}": TokenType.RIGHT_BRACE,
        "[": TokenType.LEFT_BRACKET,
        "]": TokenType.RIGHT_BRACKET,
        ",": TokenType.COMMA,
        ":": TokenType.COLON,
        ".": TokenType.DOT,
        "&": TokenType.AMPERSAND,
    }

    def __init__(self, source: str):
        self.source = source
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.token_line = 1
        self.token_column = 1
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self.at_end():
            self.start = self.current
            self.token_line = self.line
            self.token_column = self.column
            self.scan_token()

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def scan_token(self) -> None:
        char = self.advance()

        if char in " \t\r":
            return
        if char == "\n":
            self.line += 1
            self.column = 1
            return
        if char == "/" and self.peek() == "/":
            while self.peek() not in ("\n", ""):
                self.advance()
            return
        if char.isalpha() or char == "_":
            self.identifier()
            return
        if char.isdigit():
            self.number()
            return
        if char == '"':
            self.string()
            return

        if char == "=" and self.match("="):
            self.add(TokenType.EQUAL_EQUAL)
        elif char == "!" and self.match("="):
            self.add(TokenType.BANG_EQUAL)
        elif char == "!":
            self.add(TokenType.BANG)
        elif char == "<" and self.match("="):
            self.add(TokenType.LESS_EQUAL)
        elif char == ">" and self.match("="):
            self.add(TokenType.GREATER_EQUAL)
        elif char == "&" and self.match("&"):
            self.add(TokenType.AND_AND)
        elif char == "|" and self.match("|"):
            self.add(TokenType.OR_OR)
        elif char == "-" and self.match(">"):
            self.add(TokenType.ARROW)
        elif char in self.SIMPLE_TOKENS and char != "!":
            self.add(self.SIMPLE_TOKENS[char])
        else:
            self.error(f"Unexpected character {char!r}")

    def identifier(self) -> None:
        while self.peek().isalnum() or self.peek() == "_":
            self.advance()
        lexeme = self.source[self.start:self.current]
        self.add(self.KEYWORDS.get(lexeme, TokenType.IDENTIFIER))

    def number(self) -> None:
        while self.peek().isdigit():
            self.advance()

        token_type = TokenType.INTEGER
        if self.peek() == "." and self.peek_next().isdigit():
            token_type = TokenType.FLOAT
            self.advance()
            while self.peek().isdigit():
                self.advance()
        self.add(token_type)

    def string(self) -> None:
        escaped = False
        while not self.at_end():
            char = self.peek()
            if char == "\n":
                self.error("Unterminated string")
            self.advance()
            if char == '"' and not escaped:
                self.add(TokenType.STRING)
                return
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        self.error("Unterminated string")

    def add(self, token_type: TokenType) -> None:
        lexeme = self.source[self.start:self.current]
        self.tokens.append(Token(token_type, lexeme, self.token_line, self.token_column))

    def advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        self.column += 1
        return char

    def match(self, expected: str) -> bool:
        if self.peek() != expected:
            return False
        self.advance()
        return True

    def peek(self) -> str:
        return "" if self.at_end() else self.source[self.current]

    def peek_next(self) -> str:
        return "" if self.current + 1 >= len(self.source) else self.source[self.current + 1]

    def at_end(self) -> bool:
        return self.current >= len(self.source)

    def error(self, message: str) -> None:
        raise LexerError(f"{message} at {self.token_line}:{self.token_column}")
