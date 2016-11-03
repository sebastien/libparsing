#!/usr/bin/env python2.7
# encoding: utf8
import os, sys ; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/src/python")
from libparsing import *

__doc__ = """
The idea is to test a simple Python-like language (indentation based).
We're going to have something very simple that matches:

NAME:
	PROPERTY=VALUE
	NAME:
		PROPERTY=VALUE
	‥
"""


def check_indent(element, context):
	"""Checks that the last match has the same length as the current indent."""
	i = context.get("indent") or 0
	m = (context.lastMatch and context.lastMatch.length) or 0
	return m == i

def indent(element, context):
	"""Increases the required indentation"""
	context.set("indent", 1 + (context.get("indent") or 0))

def dedent(element, context):
	"""Decreases the required indentation"""
	indent = context.get("indent") or 0
	context.set("indent", indent - 1)

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
	# FIXME: Procedure does not work
	g.procedure("INDENT",       indent)
	g.procedure("DEDENT",       dedent)
	# FIXME: Adding the condition yields a segfault
	g.condition("CHECK_INDENT", check_indent)

	g.rule("Indent", s.TABS,   s.CHECK_INDENT)
	g.rule("Value",  s.NAME,   s.EQUALS, s.VALUE)
	g.rule("Line",   s.Indent, s.Value, s.EOL)
	g.group("Content")
	g.rule("Block",  s.NAME, s.COLON, s.EOL,
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
	property=value
	block:
		property=value
"""

FAILURE1 = """
block:
property=value
"""

if __name__ == "__main__":
	g = grammar()
	r = g.parseString(EXAMPLE1)
	print r, r.match
	#r.match.toJSON(1)


# EOF - vim: ts=4 sw=4 noet
