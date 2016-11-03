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

EXAMPLE1 = """
property=value
"""

EXAMPLE2 = """
block:
	property=value
"""

EXAMPLE2 = """
block:
	property=value
	block:
		property=value
"""


def check_indent(element, context):
	print "CONDITION:CHECK", element, "CONTEXT", context
	# o = context.offset
	# i = context.get("indent")
	# m = context.getText(o - i, o)
	#return m == ("\t" * i)
	return False

def indent(element, context):
	print "PROCEDURE:INDENT", element, "CONTEXT", context
	print context.set("pouet", "hello")
	print ("GET", context.get("pouet"))
	#context.set((context.get("indent") or 0) + 1)
	return False

def dedent(element, context):
	print "PROCEDURE:DEDENT", element, "CONTEXT", context
	print context.get("depth")
	#context.set(context.get("indent") - 1)
	return True

g = Grammar(isVerbose = False)
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
# Calling prepare will process the symbols
g.prepare()

r = g.parseString(EXAMPLE2)
print (r)


# EOF - vim: ts=4 sw=4 noet
