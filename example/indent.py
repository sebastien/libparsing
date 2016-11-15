#!/usr/bin/env python2.7
# encoding: utf8
import os, sys ; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/python")
from libparsing import *

__doc__ = """
Shows how to implement an indentation-based syntax using
Procedure and Condition parsing elements.

The grammar implemented in this example matches:

```
NAME:
	PROPERTY=VALUE
	NAME:
		PROPERTY=VALUE
	‥
```
"""

def check_indent(element, context):
	"""Checks that the last match has the same length as the current indent."""
	indent = context.get("indent") or 0
	o      = context.offset
	so     = max(o - indent, 0)
	eo     = o
	tabs   = 0
	for i in xrange(so, eo):
		if context[i] == "\t":
			tabs += 1
	return tabs == indent

def indent(element, context):
	"""Increases the required indentation"""
	context.set("indent", 1 + (context.get("indent") or 0))

def dedent(element, context):
	"""Decreases the required indentation"""
	indent = context.get("indent") or 0
	context.set("indent", indent - 1)

def grammarIndent( grammar ):
	"""Augments this grammar with indentation rules. This is extracted
	as a function to favor reuse."""
	g = grammar ; s= grammar.symbols
	if not s.TABS:
		g.token    ("TABS",        "\s*")
	g.procedure("INDENT",       indent)
	g.procedure("DEDENT",       dedent)
	g.condition("CHECK_INDENT", check_indent)
	g.rule("Indent", s.TABS, s.CHECK_INDENT)

def grammar(verbose=False):
	g = Grammar(isVerbose = verbose)
	s = g.symbols
	g.token    ("NAME",        "\w+")
	g.token    ("VALUE",       "[^\s\n]+")
	g.token    ("INDENT",      "\t*")
	g.token    ("WHITESPACE",  "\s+")
	g.token    ("TABS",        "\s*")
	g.word     ("EQUALS",      "=")
	g.word     ("COLON",       ":")
	g.word     ("EOL",         "\n")

	grammarIndent(g)

	g.rule("Value",  s.NAME,   s.EQUALS, s.VALUE)
	g.rule("Line",   s.Indent, s.Value, s.EOL)
	g.group("Content")
	g.rule("Block",  s.Indent, s.NAME, s.COLON, s.EOL,
		s.INDENT,
			g.agroup(s.Content).oneOrMore(),
		s.DEDENT
	)
	s.Content.set(s.Block, s.Line)
	g.axiom = s.Content
	g.skip  = s.WHITESPACE

	return g

# -----------------------------------------------------------------------------
#
# EXAMPLES
#
# -----------------------------------------------------------------------------

EXAMPLE1 = """
property=value
"""

EXAMPLE2 = """
block:
	property=value
"""

EXAMPLE3 = """
block:
	block:
		property=value
"""

FAILURE1 = """
block:
property=value
"""

if __name__ == "__main__":
	g = grammar(True)
	r = g.parseString(EXAMPLE2)
	#print (r.describe())
	#r.match.toJSON(1)


# EOF - vim: ts=4 sw=4 noet
