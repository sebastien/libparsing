#!/usr/bin/env python2.7
# encoding: utf8
import os, sys ; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/python")
from libparsing import *
from indent import grammarIndent

__doc__ = """
Grammar for the shell of a Python-like language. The grammar defines very
simple expressions in the form of a space-separated sequence of names
or numbers, structured together with `if‥elif‥else`, `for` and `while`
structures that can be nested together.


```
do something ; do something else 10
if this is true:
	do this
else if this is not true:
	do this ; and that
else:
	do nothing
and here is another statement
```
"""

def grammar(verbose=False):
	g = Grammar(isVerbose = verbose)
	s = g.symbols
	g.token    ("NAME",        "\w+")
	g.token    ("NUMBER",      "\d+")
	g.token    ("INDENT",      "\t*")
	g.token    ("WHITESPACE",  "[ ]+")
	g.token    ("TABS",        "\s*")
	g.word     ("COLON",       ":")
	g.word     ("SEMICOLON",   ";")
	g.word     ("EOL",         "\n")
	g.word     ("COMMENT",     "#[^\n]+")
	g.word     ("IF",          "if")
	g.word     ("ELIF",        "elif")
	g.word     ("ELSE",        "else")
	g.word     ("FOR",         "for")
	g.word     ("while",       "while")

	# We merge the indentation grammar
	grammarIndent(g)

	g.group("Value",     s.NAME,   s.NUMBER)
	g.rule("Expression", s.Value.oneOrMore())
	#g.rule("Statement",  s.Indent, s.Expression, g.rule(s.SEMICOLON, s.Expression).zeroOrMore(), s.EOL)
	g.rule("Statement",  s.Indent, s.Expression, s.EOL)
	g.rule("Comment",    s.Indent, s.COMMENT, s.EOL)

	g.group("Block")
	g.rule("IfBlock", s.Indent, s.IF, s.Expression, s.COLON, s.EOL,
		s.INDENT, s.Block.oneOrMore(), s.DEDENT
	)
	g.rule("ElifBlock", s.Indent, s.ELIF, s.Expression, s.COLON, s.EOL,
		s.INDENT, s.Block.oneOrMore(), s.DEDENT
	)
	g.rule("ElseBlock", s.Indent, s.ELSE, s.COLON, s.EOL,
		s.INDENT, s.Block.oneOrMore(), s.DEDENT
	)
	g.rule("If", s.IfBlock, s.ElifBlock.optional(), s.ElseBlock.optional())

	g.group("Construct", s.If)
	s.Block.set(s.Construct, s.Statement)

	g.group("Program", s.Block.zeroOrMore())

	g.axiom = s.Program
	g.skip  = s.WHITESPACE

	return g

# -----------------------------------------------------------------------------
#
# EXAMPLES
#
# -----------------------------------------------------------------------------

EXAMPLE1 = """
do this
"""

EXAMPLE2 = """
if condition:
	do this
"""

EXAMPLE3 = """
if condition:
	do this
else:
	do that
"""

EXAMPLE3 = """
if condition:
	do this
	if other:
		lorem ipsum
	else:
		dolor sit amet
else:
	do that
"""

if __name__ == "__main__":
	g = grammar(False)
	r = g.parseString(EXAMPLE3)
	r.toJSON()


# EOF - vim: ts=4 sw=4 noet
