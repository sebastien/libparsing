#!/usr/bin/env python3
# encoding: utf8
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src")
from libparsing import (
    Grammar,
    Processor,
    tp,
)


def grammar(isVerbose=False):
    """Defines a grammar for simple artihmetic expressions calculation.

    Uses range-based tokens (PCRE-free) for all token definitions.
    """
    g = Grammar(isVerbose=isVerbose)
    s = g.symbols
    g.range_token("WS", tp.many(tp.space()))
    g.range_token(
        "NUMBER",
        tp.seq(
            tp.many(tp.digit()), tp.optional(tp.seq(tp.char("."), tp.many(tp.digit())))
        ),
    )
    g.range_token("VARIABLE", tp.many(tp.word()))
    g.range_token("OPERATOR", tp.set("+-*/"))
    g.group("Value", s.NUMBER, s.VARIABLE)
    g.rule("Suffix", s.OPERATOR._as("operator"), s.Value._as("value"))
    g.rule("Expression", s.Value, s.Suffix.zeroOrMore())
    g.axiom = s.Expression
    g.skip = s.WS
    return g


class Processor(Processor):
    def onNUMBER(self, match):
        return int(self.process(match)[0])

    def onVARIABLE(self, match):
        return self.process(match)[0]

    def onOPERATOR(self, match):
        return self.process(match)[0]

    def onValue(self, match):
        value = self.process(match[0])
        return value

    def onSuffix(self, match, value, operator):
        return (value, operator)

    def onExpression(self, match):
        value = self.process(match[0])
        suffixes = self.process(match[1])
        return [value] + list(suffixes)


EXAMPLES = ["10 + VAR"]

if __name__ == "__main__":
    g = grammar()
    g.prepare()
    p = Processor(g)
    result = g.parseString(EXAMPLES[0])
    print(p.process(result))

# EOF
