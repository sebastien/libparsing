#!/usr/bin/env python3
# encoding: utf8
"""
Simple Lisp Parser
==================

A Lisp (S-expression) parser implemented with libparsing. Parses Lisp source
code and transforms the parse tree into native Python objects (lists, ints,
floats, strings). Equivalent in structure to examples/json_parser.py.

Features:
    - Numbers (integers and floats, with optional sign)
    - Symbols (identifiers and operators like +, -, <=, string->number)
    - Strings (double-quoted with escape sequences)
    - Comments (; to end of line, automatically skipped)
    - Quote shorthand ('x desugars to ["quote", x])
    - Proper lists: (a b c)
    - Dotted pairs: (a . b), (a b . c)

Usage:
    python examples/lisp_parser.py <file.lsp>
    python examples/lisp_parser.py --test
"""

import sys
import os
import re

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/py"
)
from libparsing import Grammar, Processor, UNMATCHED


# --
# ## Dotted Pair Representation


class DottedPair(tuple):
    """Represents a Lisp dotted pair: (a . b) -> DottedPair(a, b)

    Distinguished from proper lists (Python list) by type.
    For (a b . c), returns DottedPair(a, b, c) where the last element
    is the cdr of the final cons cell.
    """

    def __repr__(self):
        return "DottedPair({0})".format(", ".join(repr(x) for x in self))


# --
# ## Grammar Definition


def grammar(isVerbose=False):
    """Defines a PEG grammar for Lisp S-expressions."""
    g = Grammar(isVerbose=isVerbose)
    s = g.symbols

    # -- Tokens
    # WS includes line comments (;...\n), consumed together with whitespace
    g.token("WS", r"(\s|;[^\n]*)+")
    # Numbers: optional sign, integer or decimal
    g.token("NUMBER", r"[+\-]?\d+(\.\d+)?")
    # Strings: double-quoted with backslash escape sequences
    g.token("STRING", r'"([^"\\]|\\.)*"')
    # Symbols: identifiers and operators
    # - Standard identifiers start with a letter or special char
    # - Standalone + and - are included via the initial character class
    # - ... (ellipsis) is a special symbol
    g.token(
        "SYMBOL",
        r"[a-zA-Z!$%&*+\-/:<=>?~_^][a-zA-Z0-9!$%&*+\-/:<=>?~_^.]*|\.\.\.",
    )

    # -- Words (literal delimiters)
    g.word("QUOTE", "'")
    g.word("DOT", ".")
    g.word("LP", "(")
    g.word("RP", ")")

    # -- Grammar rules
    g.group("Atom", s.NUMBER, s.SYMBOL, s.STRING)

    # Forward-declare Expr for recursion (lists contain exprs)
    g.group("Expr")

    g.rule("Quoted", s.QUOTE, s.Expr._as("expr"))
    g.rule("DottedTail", s.DOT, s.Expr._as("expr"))
    g.rule(
        "List",
        s.LP,
        s.Expr.zeroOrMore()._as("items"),
        s.DottedTail.optional()._as("dotted"),
        s.RP,
    )

    # Fill in Expr alternatives (order matters: Quoted first for ' prefix)
    s.Expr.set(s.Quoted, s.List, s.Atom)

    g.rule("Program", s.Expr.zeroOrMore()._as("expressions"))

    g.axiom = s.Program
    g.skip = s.WS
    return g


# --
# ## Lisp String Escape Handling

_ESCAPE_RE = re.compile(r'\\(["\\nrt])')
_ESCAPE_MAP = {'"': '"', "\\": "\\", "n": "\n", "r": "\r", "t": "\t"}


def decode_lisp_string(s):
    """Strip quotes and decode escape sequences from a Lisp string token."""
    inner = s[1:-1]
    if "\\" not in inner:
        return inner
    return _ESCAPE_RE.sub(lambda m: _ESCAPE_MAP.get(m.group(1), m.group(0)), inner)


# --
# ## Tree-to-Native Processor


class TreeToLisp(Processor):
    """Transforms a libparsing Lisp parse tree into native Python objects.

    - Numbers become int or float
    - Symbols become str
    - Strings become str (unquoted, escapes decoded)
    - Proper lists become Python list
    - Dotted pairs become DottedPair (a tuple subclass)
    - 'x is desugared to ["quote", x]
    - A program is a list of top-level expressions
    """

    def onNUMBER(self, match):
        text = match.group()[0]
        return float(text) if "." in text else int(text)

    def onSTRING(self, match):
        return decode_lisp_string(match.group()[0])

    def onSYMBOL(self, match):
        return match.group()[0]

    def onAtom(self, match):
        return self.process(match[0])

    def onQuoted(self, match, expr):
        return ["quote", self.process(expr)]

    def onDottedTail(self, match, expr):
        return self.process(expr)

    def onList(self, match, items, dotted):
        processed = self.process(items)
        elements = list(processed) if processed else []
        if dotted is not UNMATCHED:
            tail = self.process(dotted)
            return DottedPair(elements + [tail])
        return elements

    def onExpr(self, match):
        return self.process(match[0])

    def onProgram(self, match, expressions):
        result = self.process(expressions)
        return list(result) if result else []


# --
# ## Public API

_grammar = None
_processor = None


def _init():
    global _grammar, _processor
    if _grammar is None:
        _grammar = grammar()
        _grammar.prepare()
        _processor = TreeToLisp(_grammar)


def parse(text):
    """Parse Lisp source text and return a list of native Python objects.

    Each top-level expression becomes one element in the returned list.
    """
    _init()
    result = _grammar.parseString(text)
    if result.isFailure():
        raise ValueError("Lisp parse error: {0}".format(result.describe()))
    return _processor.process(result)


# --
# ## Test & CLI


def test():
    """Validate the parser against expected native Python structures."""
    cases = [
        # Atoms
        ("42", [42]),
        ("-17", [-17]),
        ("3.14", [3.14]),
        ('"hello"', ["hello"]),
        ("foo", ["foo"]),
        ("+", ["+"]),
        ("-", ["-"]),
        ("<=", ["<="]),
        ("string->number", ["string->number"]),
        ("...", ["..."]),
        # Simple lists
        ("(+ 1 2)", [["+", 1, 2]]),
        ("()", [[]]),
        ("(define x 42)", [["define", "x", 42]]),
        # Nested
        (
            "(define (square x) (* x x))",
            [["define", ["square", "x"], ["*", "x", "x"]]],
        ),
        (
            "(let ((a 1) (b 2)) (+ a b))",
            [["let", [["a", 1], ["b", 2]], ["+", "a", "b"]]],
        ),
        # Quote
        ("'x", [["quote", "x"]]),
        ("'(1 2 3)", [["quote", [1, 2, 3]]]),
        # Dotted pairs
        ("(1 . 2)", [DottedPair([1, 2])]),
        ("(a b . c)", [DottedPair(["a", "b", "c"])]),
        # Multiple top-level expressions
        ("1 2 3", [1, 2, 3]),
        # Comments
        ("; comment\n42", [42]),
        ("; line 1\n; line 2\n(+ 1 2)", [["+", 1, 2]]),
        # Strings with escapes
        (r'"hello \"world\""', ['hello "world"']),
        (r'"line1\nline2"', ["line1\nline2"]),
    ]

    for text, expected in cases:
        result = parse(text)
        assert result == expected, (
            "FAIL: parse({0!r})\n  got:      {1!r}\n  expected: {2!r}".format(
                text, result, expected
            )
        )

    print("OK - all {0} test cases passed".format(len(cases)))

    # Also parse the example file if available
    example_file = os.path.join(os.path.dirname(__file__), "lisp_parser.lsp")
    if os.path.exists(example_file):
        with open(example_file) as f:
            result = parse(f.read())
        print("OK - parsed {0} ({1} expressions)".format(example_file, len(result)))
        for expr in result:
            print("  {0!r}".format(expr))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--test":
        with open(sys.argv[1]) as f:
            result = parse(f.read())
        for expr in result:
            print(repr(expr))
    else:
        test()

# EOF
