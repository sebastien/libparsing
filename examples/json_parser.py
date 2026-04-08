#!/usr/bin/env python3
# encoding: utf8
"""
Simple JSON Parser
==================

A JSON parser implemented with libparsing, equivalent to the Lark JSON parser
example at deps/lark/examples/json_parser.py. Parses JSON text and transforms
the parse tree into native Python objects (dicts, lists, strings, numbers,
booleans, None).

Usage:
    python examples/json_parser.py <file.json>
"""

import sys
import os
import re

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/python"
)
from libparsing import Grammar, Processor, RangeToken, tp, UNMATCHED


# --
# ## Grammar Definition


def grammar(isVerbose=False):
    """Defines a PEG grammar for JSON using range-based tokens (PCRE-free)."""
    g = Grammar(isVerbose=isVerbose)
    g.setNoMemo()  # JSON grammar doesn't benefit from memoization
    g.setSkipWhitespace()  # Use fast hand-coded whitespace skip
    s = g.symbols

    # -- Tokens (range-based, no PCRE dependency)
    g.range_token("WS", tp.many(tp.space()))
    # NUMBER and STRING use hand-coded recognizers for complex patterns
    g.range_token("NUMBER", tp.many(tp.digit())).setJSONNumberRecognizer()
    g.range_token("STRING", tp.char('"')).setJSONStringRecognizer()
    g.range_token("TRUE", tp.literal("true"))
    g.range_token("FALSE", tp.literal("false"))
    g.range_token("NULL", tp.literal("null"))

    # -- Words (literal delimiters)
    g.word("LBRACE", "{")
    g.word("RBRACE", "}")
    g.word("LBRACKET", "[")
    g.word("RBRACKET", "]")
    g.word("COMMA", ",")
    g.word("COLON", ":")

    # -- Grammar rules
    # Forward-declare Value (needed for recursion in Object/Array)
    g.group("Value")

    # Object: { pair (, pair)* }
    g.rule("Pair", s.STRING._as("key"), s.COLON, s.Value._as("value"))
    g.rule("PairSuffix", s.COMMA, s.Pair._as("pair"))
    g.rule(
        "Object",
        s.LBRACE,
        s.Pair.optional()._as("first"),
        s.PairSuffix.zeroOrMore()._as("rest"),
        s.RBRACE,
    )

    # Array: [ value (, value)* ]
    g.rule("ValueSuffix", s.COMMA, s.Value._as("value"))
    g.rule(
        "Array",
        s.LBRACKET,
        s.Value.optional()._as("first"),
        s.ValueSuffix.zeroOrMore()._as("rest"),
        s.RBRACKET,
    )

    # Value alternatives (set after Object/Array are defined)
    s.Value.set(s.Object, s.Array, s.STRING, s.NUMBER, s.TRUE, s.FALSE, s.NULL)

    g.axiom = s.Value
    g.skip = s.WS
    return g


# --
# ## JSON String Escape Handling

# Matches JSON escape sequences: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
_ESCAPE_RE = re.compile(r'\\(["\\\/bfnrt]|u[0-9a-fA-F]{4})')
_ESCAPE_MAP = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _decode_escape(m):
    """Decode a single JSON escape sequence match."""
    seq = m.group(1)
    if seq[0] == "u":
        return chr(int(seq[1:], 16))
    return _ESCAPE_MAP[seq]


def decode_json_string(s):
    """Strip quotes and decode escape sequences from a JSON string token."""
    # Remove surrounding quotes
    inner = s[1:-1]
    # Fast path: most JSON strings have no escape sequences
    if "\\" not in inner:
        return inner
    return _ESCAPE_RE.sub(_decode_escape, inner)


# --
# ## Tree-to-JSON Processor


class TreeToJson(Processor):
    """Transforms a libparsing JSON parse tree into native Python objects."""

    def onSTRING(self, match):
        return decode_json_string(match.group()[0])

    def onNUMBER(self, match):
        return float(match.group()[0])

    def onTRUE(self, match):
        return True

    def onFALSE(self, match):
        return False

    def onNULL(self, match):
        return None

    def onPair(self, match, key, value):
        k = self.process(key)
        v = self.process(value)
        return (k, v)

    def onPairSuffix(self, match, pair):
        return self.process(pair)

    def onObject(self, match, first, rest):
        pairs = []
        if first is not UNMATCHED:
            f = self.process(first)
            if f is not None:
                pairs.append(f)
        r = self.process(rest)
        if r:
            pairs.extend(r)
        return dict(pairs)

    def onValueSuffix(self, match, value):
        return self.process(value)

    def onArray(self, match, first, rest):
        items = []
        if first is not UNMATCHED:
            items.append(self.process(first))
        r = self.process(rest)
        if r:
            items.extend(r)
        return items

    def onValue(self, match):
        return self.process(match[0])


# --
# ## Public API

_grammar = None
_processor = None


def _init():
    global _grammar, _processor
    if _grammar is None:
        _grammar = grammar()
        _grammar.prepare()
        _processor = TreeToJson(_grammar)


def parse(text):
    """Parse a JSON string and return native Python objects."""
    _init()
    result = _grammar.parseString(text)
    if result.isFailure():
        raise ValueError("JSON parse error: {0}".format(result.describe()))
    return _processor.process(result)


# --
# ## Test & CLI


def test():
    """Validate against Python's json.loads using the same test payload as lark."""
    import json

    test_json = """
        {
            "empty_object" : {},
            "empty_array"  : [],
            "booleans"     : { "YES" : true, "NO" : false },
            "numbers"      : [ 0, 1, -2, 3.3, 4.4e5, 6.6e-7 ],
            "strings"      : [ "This", [ "And" , "That", "And a \\"b" ] ],
            "nothing"      : null
        }
    """

    j = parse(test_json)
    expected = json.loads(test_json)
    assert j == expected, "Mismatch:\n  got:      {0}\n  expected: {1}".format(
        j, expected
    )
    print("OK - parsed JSON matches json.loads output")
    print(j)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--test":
        with open(sys.argv[1]) as f:
            print(parse(f.read()))
    else:
        test()

# EOF
