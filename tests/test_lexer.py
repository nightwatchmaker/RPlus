import unittest

from rplus.lexer import Lexer, LexerError, Token, TokenType


class LexerTests(unittest.TestCase):
    def test_lexes_a_small_program(self):
        source = 'let answer = 40 + 2\nprintln("ok")'

        tokens = Lexer(source).tokenize()

        self.assertEqual(tokens, [
            Token(TokenType.LET, "let", 1, 1),
            Token(TokenType.IDENTIFIER, "answer", 1, 5),
            Token(TokenType.EQUAL, "=", 1, 12),
            Token(TokenType.INTEGER, "40", 1, 14),
            Token(TokenType.PLUS, "+", 1, 17),
            Token(TokenType.INTEGER, "2", 1, 19),
            Token(TokenType.IDENTIFIER, "println", 2, 1),
            Token(TokenType.LEFT_PAREN, "(", 2, 8),
            Token(TokenType.STRING, '\"ok\"', 2, 9),
            Token(TokenType.RIGHT_PAREN, ")", 2, 13),
            Token(TokenType.EOF, "", 2, 14),
        ])

    def test_lexes_keywords_compound_operators_and_comments(self):
        source = "fn add(a: Int, b: Int) -> Int { // sum\n return a >= b }"

        tokens = Lexer(source).tokenize()
        kinds = [token.type for token in tokens]

        self.assertEqual(kinds, [
            TokenType.FN, TokenType.IDENTIFIER, TokenType.LEFT_PAREN,
            TokenType.IDENTIFIER, TokenType.COLON, TokenType.IDENTIFIER,
            TokenType.COMMA, TokenType.IDENTIFIER, TokenType.COLON,
            TokenType.IDENTIFIER, TokenType.RIGHT_PAREN, TokenType.ARROW,
            TokenType.IDENTIFIER, TokenType.LEFT_BRACE, TokenType.RETURN,
            TokenType.IDENTIFIER, TokenType.GREATER_EQUAL, TokenType.IDENTIFIER,
            TokenType.RIGHT_BRACE, TokenType.EOF,
        ])

    def test_reports_unterminated_string_with_location(self):
        with self.assertRaisesRegex(LexerError, r"Unterminated string at 1:1"):
            Lexer('"oops').tokenize()


if __name__ == "__main__":
    unittest.main()
